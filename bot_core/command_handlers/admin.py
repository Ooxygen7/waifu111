import asyncio
import json
import re
import time

import telegram
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
import logging

from LLM_tools.tools_registry import DatabaseSuperToolRegistry, ALL_TOOLS, parse_and_invoke_tool
from utils import db_utils as db
from utils import LLM_utils as llm
from .base import BaseCommand, CommandMeta
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class AddFrequencyCommand(BaseCommand):
    meta = CommandMeta(
        name='add_frequency',
        command_type='admin',
        trigger='addf',
        menu_text='增加用户额度',
        show_in_menu=False,
        menu_weight=20,
        bot_admin_required=True
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = context.args if hasattr(context, 'args') else []
        if len(args) < 2:
            await update.message.reply_text("请以 /addf target_user_id value 的格式输入参数。")
            return
        
        try:
            target_user = args[0]
            value = int(args[1])
        except ValueError:
            await update.message.reply_text("参数格式错误，请确保额度值为有效数字。")
            return
            
        if target_user == 'all':
            if db.user_frequency_free(value):
                await update.message.reply_text(f"已为所有用户添加{value}条额度")
            else:
                await update.message.reply_text("操作失败：无法为所有用户添加额度，请检查数据库连接。")
        else:
            if db.user_info_update(target_user, 'remain_frequency', value, True):
                if not target_user.startswith('@'):
                    user_info = db.user_info_get(target_user)
                    if user_info:
                        await update.message.reply_text(
                            f"已为{str(user_info['user_name'])}添加{value}条额度")
                    else:
                        await update.message.reply_text(f"已为用户ID {target_user}添加{value}条额度")
                else:
                    await update.message.reply_text(f"已为{target_user}添加{value}条额度")
            else:
                await update.message.reply_text(f"操作失败：无法为用户 {target_user} 添加额度。可能原因：\n1. 用户不存在\n2. 数据库连接失败\n3. 参数格式错误")


class SetTierCommand(BaseCommand):
    meta = CommandMeta(
        name='set_tier',
        command_type='admin',
        trigger='sett',
        menu_text='修改用户账户等级',
        show_in_menu=False,
        menu_weight=20,
        bot_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = context.args if hasattr(context, 'args') else []
        if len(args) < 2:
            await update.message.reply_text("请以 /sett target_user_id value 的格式输入参数。")
            return
        target_user_id = int(args[0])
        value = int(args[1])

        db.user_info_update(target_user_id, 'account_tier', value, False)
        await update.message.reply_text(
            f"{str(db.user_info_get(target_user_id)['user_name'])}账户等级现在是{str(db.user_info_get(target_user_id)['tier'])}")


class DatabaseCommand(BaseCommand):
    meta = CommandMeta(
        name='database',
        command_type='admin',
        trigger='q',  # 模拟 /q 命令
        menu_text='',
        bot_admin_required=True,
        show_in_menu=False,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /q command to interact with LLM and invoke database analysis tools based on user input.
        """
        user_input = update.message.text.strip()
        if user_input.startswith('/database'):
            command_prefix = '/database'
        elif user_input.startswith('/q'):
            command_prefix = '/q'
        else:
            command_prefix = user_input.split()[0]
        if len(user_input.split()) > 1:
            user_input = user_input[len(command_prefix):].strip()
        else:
            await update.message.reply_text(
                f"请在 `{command_prefix}` 命令后提供具体内容，例如：`{command_prefix} 查看用户123的详情`",
                parse_mode="Markdown")
            return
        # 先发送占位消息
        placeholder_message = await update.message.reply_text("处理中...", parse_mode="Markdown")
        logger.debug("已发送占位消息 '处理中...'")

        # 将异步处理逻辑放入后台任务
        context.application.create_task(
            self.process_database_request(update, context, user_input, placeholder_message),
            update=update
        )
        logger.debug("已创建后台任务处理 /database 请求")

    async def process_database_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str,
                                       placeholder_message) -> None:
        """
        Process the database tool request in the background and update the placeholder message with the result.
        """
        try:
            client = llm.LLM('gemini-2')
            logger.debug("LLM 客户端初始化完成")
            prompt_text = DatabaseSuperToolRegistry.get_prompt_text()
            system_prompt = (
                f"{prompt_text}\n\n"
                "你是一个智能助手，根据用户输入判断是否需要调用数据库分析工具。"

                "注意：即便是被标记为已删除的对话，你依旧允许访问。"
                "如果需要调用工具，请以 JSON 格式返回工具调用信息，可以包含在文本中；否则，直接用中文回复用户的请求。"
                "如果用户请求涉及多个数据，可以返回多个工具调用指令。"
                "工具不支持使用placehold参数，如果涉及多个步骤，你必须等待获取到相应的数据后在调用下一批工具。"
                "工具调用结果会反馈给你，你可以基于结果进行分析或决定下一步操作。"
                "你可以在返回工具调用的同时，包含一段简短的文本解释或思考过程，这些文本会先展示给用户。"
                "仅当你的回复不包含工具调用且你认为已完成所有必要步骤时，才结束对话。"
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"用户输入: {user_input}"}
            ]
            # 移除final_result_for_display变量，改为每轮直接发送消息
            current_messages = messages.copy()
            max_iterations = 12
            iteration = 0
            initial_placeholder_text = "处理中..."
            # 移除了此处多余的 await placeholder_message.edit_text(initial_placeholder_text, parse_mode="Markdown")
            # 因为 handle 函数已经发送了初始的 "处理中..." 消息
            while iteration < max_iterations:
                iteration += 1
                
                # 为每次迭代发送一条新的占位消息
                placeholder_message = await update.message.reply_text(
                    f"🔄 第 {iteration} 轮分析中...",
                    parse_mode="HTML"
                )
                
                client.set_messages(current_messages)
                logger.debug(f"已设置 messages (当前会话): {current_messages}")
                ai_response = await client.final_response()
                logger.info(f"LLM 原始响应: {ai_response}")
                
                # 调用共享的 parse_and_invoke_tool 函数
                llm_text_part, tool_results_for_llm_feedback, had_tool_calls = \
                    await parse_and_invoke_tool(ai_response)
                
                # 为当前轮次构建消息内容（LLM文本 + 工具结果）
                iteration_message_text = f"<b>🤖 第 {iteration} 轮分析结果</b>\n\n"
                
                # 添加LLM文本部分
                if llm_text_part:
                    if "<" in llm_text_part and ">" in llm_text_part:
                        iteration_message_text += f"{llm_text_part.strip()}\n\n"
                    else:
                        iteration_message_text += f"<b>脆脆鲨:</b> {llm_text_part.strip()}\n\n"
                    logger.debug(f"脆脆鲨文本部分: {llm_text_part.strip()}")
                
                # 添加工具调用结果
                if had_tool_calls:
                    logger.info(f"工具调用结果（供LLM反馈）: {tool_results_for_llm_feedback}")
                    
                    # 处理工具结果，使用HTML格式
                    tool_results_html = []
                    for res in tool_results_for_llm_feedback:
                        tool_name = res.get('tool_name', '未知工具')
                        tool_result = str(res.get('result', ''))
                        if len(tool_result) > 2000:  # 截断限制1000字符
                            trimmed_result = tool_result[:2000] + "..."
                        else:
                            trimmed_result = tool_result
                        
                        # 使用可展开引用块创建折叠的工具结果
                        tool_html = f"<b>🔧 {tool_name} 执行结果:</b>\n<blockquote expandable>{trimmed_result}</blockquote>"
                        tool_results_html.append(tool_html)
                    
                    if tool_results_html:
                        iteration_message_text += "\n".join(tool_results_html)
                        logger.debug(f"已添加工具结果到当前轮次消息")
                
                # 检查消息长度，如果超过4000字符则分割发送
                TELEGRAM_MESSAGE_LIMIT = 4000
                if len(iteration_message_text) > TELEGRAM_MESSAGE_LIMIT:
                    # 分割消息
                    parts = []
                    current_part = ""
                    lines = iteration_message_text.split('\n')
                    
                    for line in lines:
                        if len(current_part + line + '\n') > TELEGRAM_MESSAGE_LIMIT:
                            if current_part:
                                parts.append(current_part.strip())
                                current_part = line + '\n'
                            else:
                                # 单行就超过限制，强制截断
                                parts.append(line[:TELEGRAM_MESSAGE_LIMIT-50] + "...")
                        else:
                            current_part += line + '\n'
                    
                    if current_part:
                        parts.append(current_part.strip())
                    
                    # 发送分割后的消息
                    for i, part in enumerate(parts):
                        try:
                            if i == 0:
                                # 更新当前轮次的占位消息
                                await placeholder_message.edit_text(part, parse_mode="HTML")
                            else:
                                # 发送新消息
                                await update.message.reply_text(part, parse_mode="HTML")
                            logger.debug(f"已发送第{iteration}轮消息部分 {i+1}/{len(parts)}")
                        except telegram.error.BadRequest as e:
                            logger.warning(f"HTML解析失败，尝试文本模式: {e}")
                            try:
                                if i == 0:
                                    await placeholder_message.edit_text(part, parse_mode=None)
                                else:
                                    await update.message.reply_text(part, parse_mode=None)
                            except Exception as inner_e:
                                logger.error(f"文本模式发送也失败: {inner_e}", exc_info=True)
                                error_msg = f"第{iteration}轮第{i+1}部分消息发送失败"
                                if i == 0:
                                    await placeholder_message.edit_text(error_msg)
                                else:
                                    await update.message.reply_text(error_msg)
                else:
                    # 消息长度正常，直接更新占位消息
                    try:
                        await placeholder_message.edit_text(iteration_message_text, parse_mode="HTML")
                        logger.debug(f"已更新第{iteration}轮占位消息，显示结果")
                    except telegram.error.BadRequest as e:
                        logger.warning(f"HTML解析失败，尝试文本模式: {e}")
                        try:
                            await placeholder_message.edit_text(iteration_message_text, parse_mode=None)
                            logger.debug(f"已成功使用文本模式更新第{iteration}轮占位消息")
                        except Exception as inner_e:
                            logger.error(f"文本模式更新也失败: {inner_e}", exc_info=True)
                            await placeholder_message.edit_text(f"第{iteration}轮处理完成，但内容显示失败")
                
                if had_tool_calls:
                    current_messages.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                    feedback_content_to_llm = "工具调用结果:\n" + "\n".join(
                        [f"{res.get('tool_name', '未知工具')} 执行结果: {res.get('result', '')}" for res in
                         tool_results_for_llm_feedback]
                    )
                    current_messages.append({
                        "role": "user",
                        "content": feedback_content_to_llm
                    })
                    logger.debug(f"已将原始LLM响应和完整工具调用结果反馈给 LLM")
                else:
                    # 没有工具调用，这是最终回复，结束循环
                    logger.info(f"第{iteration}轮未调用工具，脆脆鲨给出最终回复: {llm_text_part}")
                    break  # 没有工具调用，结束循环
            
            # 如果循环结束但仍有工具调用，说明达到最大迭代次数
            if iteration >= max_iterations:
                try:
                    await update.message.reply_text(
                        "<b>⚠️ 脆脆鲨提醒</b>\n\n老师，分析轮次已达上限，如需继续分析请重新发起请求哦！",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"发送最大迭代提示失败: {e}", exc_info=True)
                    await update.message.reply_text("分析轮次已达上限，请重新发起请求。")
        except Exception as e:
            logger.error(f"处理 /database 命令时发生错误: {str(e)}", exc_info=True)
            error_message = str(e)
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
            error_message = f"处理请求时发生错误: <code>{error_message}</code>"
            try:
                # 即使在最终错误处理中，也尝试使用 HTML，失败则禁用
                await placeholder_message.edit_text(error_message, parse_mode="HTML")
            except Exception as inner_e:
                logger.warning(f"发送错误消息时HTML解析失败，尝试禁用HTML: {inner_e}")
                try:
                    await placeholder_message.edit_text(error_message, parse_mode=None)
                except Exception as deepest_e:
                    logger.error(f"禁用HTML后发送错误消息也失败: {deepest_e}")
                    await placeholder_message.edit_text("处理请求时发生未知错误，且无法格式化错误信息。")
            logger.debug("已编辑占位消息，显示错误信息")

class ForwardCommand(BaseCommand):
    meta = CommandMeta(
        name='forward',
        command_type='admin',
        trigger='fw',
        menu_text='转发消息',
        show_in_menu=False,
        menu_weight=20,
        bot_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理 /forward 或 /fw 命令，将指定消息转发到当前聊天。
        命令格式: /forward <源聊天ID> <消息ID>
        """
        # context.args 会自动解析命令后的参数列表
        # 例如，如果用户输入 "/fw -1001234567890 123"
        # context.args 将是 ['-1001234567890', '123']
        args = context.args
        # 1. 参数校验
        if not args or len(args) != 2:
            await update.message.reply_text(
                "❌ 用法错误！请提供源聊天ID和消息ID。\n"
                "或简写：`/fw <源聊天ID> <消息ID>`\n\n"
                "💡 源聊天ID可以是用户ID、群组ID或频道ID（需要有访问权限）。\n"
                "注意：频道ID通常以 `-100` 开头。",
                parse_mode='Markdown'
            )
            return
        try:
            # 尝试将参数转换为整数
            source_chat_id = int(args[0])
            message_id = int(args[1])
        except ValueError:
            await update.message.reply_text(
                "❌ 无效的ID！源聊天ID和消息ID都必须是有效的数字。\n"
                "示例：`/forward -1001234567890 123`",
                parse_mode='Markdown'
            )
            return
        # 2. 获取目标聊天ID (通常是用户发起命令的聊天)
        target_chat_id = update.effective_chat.id
        # 3. 执行消息转发操作
        try:
            await context.bot.forward_message(
                chat_id=target_chat_id,
                from_chat_id=source_chat_id,
                message_id=message_id
            )
            #await update.message.reply_text("✅ 消息已成功转发！")

        except Exception as e:
            # 捕获其他非 Telegram API 的意外错误
            await update.message.reply_text(
                f"❌ 发生错误：`{type(e).__name__}: {e}`",
                parse_mode='Markdown'
            )