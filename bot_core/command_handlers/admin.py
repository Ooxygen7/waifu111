import asyncio
import json
import re
import time

import telegram
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
import logging

from LLM_tools.tools_registry import DatabaseToolRegistry, ALL_TOOLS, parse_and_invoke_tool
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
        target_user = args[0]
        value = int(args[1])
        if target_user == 'all':
            if db.user_frequency_free(value):
                await update.message.reply_text(f"已为所有用户添加{value}条额度")
        else:
            if db.user_info_update(target_user, 'remain_frequency', value, True):
                if not target_user.startswith('@'):
                    await update.message.reply_text(
                        f"已为{str(db.user_info_get(target_user)['user_name'])}添加{value}条额度")
                else:
                    await update.message.reply_text(f"已为{target_user}添加{value}条额度")


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
            client = llm.LLM('gemini-2.5')
            logger.debug("LLM 客户端初始化完成")
            prompt_text = DatabaseToolRegistry.get_prompt_text()
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
            final_result_for_display = ""
            current_messages = messages.copy()
            max_iterations = 8
            iteration = 0
            initial_placeholder_text = "处理中..."
            # 移除了此处多余的 await placeholder_message.edit_text(initial_placeholder_text, parse_mode="Markdown")
            # 因为 handle 函数已经发送了初始的 "处理中..." 消息
            while iteration < max_iterations:
                iteration += 1
                client.set_messages(current_messages)
                logger.debug(f"已设置 messages (当前会话): {current_messages}")
                ai_response = await client.final_response()
                logger.info(f"LLM 原始响应: {ai_response}")
                llm_text_part, tool_results_for_llm_feedback, had_tool_calls = \
                    await parse_and_invoke_tool(ai_response)
                if llm_text_part:
                    if "```" in llm_text_part:
                        final_result_for_display += f"{llm_text_part.strip()}\n"
                    else:
                        final_result_for_display += f"脆脆鲨: {llm_text_part.strip()}\n"
                    logger.debug(f"LLM文本部分已添加: {llm_text_part.strip()}")
                if had_tool_calls:
                    logger.info(f"工具调用结果（供LLM反馈）: {tool_results_for_llm_feedback}")

                    trimmed_results_for_display = []
                    for res in tool_results_for_llm_feedback:
                        tool_name = res.get('tool_name', '未知工具')
                        tool_result = str(res.get('result', ''))
                        if len(tool_result) > 80:
                            trimmed_result = tool_result[:80] + "..."
                        else:
                            trimmed_result = tool_result
                        trimmed_results_for_display.append(f"{tool_name} 执行结果: {trimmed_result}")
                    if trimmed_results_for_display:
                        final_result_for_display += "```\n" + "\n".join(trimmed_results_for_display) + "\n```\n"
                        logger.debug(f"已添加修剪后的工具结果到显示: {trimmed_results_for_display}")
                    display_content = final_result_for_display.strip()
                    # 确保每次更新都有"处理中..."前缀
                    current_display_text = f"{initial_placeholder_text}\n{display_content}" if display_content else initial_placeholder_text

                    # --- 中间结果更新的错误处理 ---
                    try:
                        await placeholder_message.edit_text(
                            f"{current_display_text}\n更新时间: {time.time()}",  # 添加时间戳确保内容变化
                            parse_mode="Markdown"
                        )
                        logger.debug("已更新占位消息，显示中间结果")
                    except telegram.ext.error.BadRequest as e:
                        # 捕获 Telegram 的 BadRequest 错误，通常是 Markdown 解析问题
                        logger.warning(f"更新占位消息时Markdown解析失败，尝试禁用Markdown: {e}")
                        try:
                            # 尝试禁用 Markdown 再次发送
                            await placeholder_message.edit_text(
                                f"{current_display_text}\n更新时间: {time.time()}",
                                parse_mode=None  # 禁用 Markdown
                            )
                            logger.debug("已成功禁用Markdown更新占位消息")
                        except Exception as inner_e:
                            # 如果禁用 Markdown 后仍然失败，记录更深层的错误并发送通用错误消息
                            logger.error(f"禁用Markdown后再次发送消息失败: {inner_e}", exc_info=True)
                            await placeholder_message.edit_text("处理中... (内容包含无法解析的格式，已禁用格式显示)")
                    except Exception as e:
                        # 捕获其他非 Telegram BadRequest 的异常
                        logger.error(f"更新占位消息时发生未知错误: {e}", exc_info=True)
                        # 尝试禁用 Markdown 再次发送，作为通用降级方案
                        try:
                            await placeholder_message.edit_text(
                                f"{current_display_text}\n更新时间: {time.time()}",
                                parse_mode=None
                            )
                            logger.debug("发生未知错误后尝试禁用Markdown更新占位消息")
                        except Exception as inner_e:
                            logger.error(f"未知错误且禁用Markdown后发送消息失败: {inner_e}", exc_info=True)
                            await placeholder_message.edit_text("处理中... (更新失败，请稍后再试)")
                    # --- 结束中间结果更新的错误处理 ---
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
                    logger.info(f"未调用工具，LLM直接回复。最终文本: {llm_text_part}")
                    break  # 结束循环
            TELEGRAM_MESSAGE_LIMIT = 4096
            final_output_to_user = final_result_for_display.strip()
            if len(final_output_to_user) > TELEGRAM_MESSAGE_LIMIT:
                final_output_to_user = final_output_to_user[
                                       :TELEGRAM_MESSAGE_LIMIT - 60].strip() + "...\n\n**注意：结果过长，已被截断。**"

            if not final_output_to_user:
                final_output_to_user = "LLM未返回有效内容。"
            # --- 最终结果更新的错误处理 ---
            try:
                await placeholder_message.edit_text(final_output_to_user, parse_mode="Markdown")
                logger.debug("已编辑占位消息，显示最终结果")
            except telegram.error.BadRequest as e:
                # 捕获 Telegram 的 BadRequest 错误，通常是 Markdown 解析问题
                logger.warning(f"最终结果Markdown解析失败，尝试禁用Markdown: {e}")
                try:
                    # 尝试禁用 Markdown 再次发送
                    await placeholder_message.edit_text(final_output_to_user, parse_mode=None)  # 禁用 Markdown
                    logger.debug("已成功禁用Markdown发送最终结果")
                except Exception as inner_e:
                    # 如果禁用 Markdown 后仍然失败，记录更深层的错误并发送通用错误消息
                    logger.error(f"禁用Markdown后发送最终结果失败: {inner_e}", exc_info=True)
                    await placeholder_message.edit_text("处理完成。但内容包含无法解析的格式，已禁用格式显示。")
            except Exception as e:
                # 捕获其他非 Telegram BadRequest 的异常
                logger.error(f"发送最终结果时发生未知错误: {e}", exc_info=True)
                # 尝试禁用 Markdown 再次发送，作为通用降级方案
                try:
                    await placeholder_message.edit_text(final_output_to_user, parse_mode=None)
                    logger.debug("发送最终结果时发生未知错误后尝试禁用Markdown")
                except Exception as inner_e:
                    logger.error(f"未知错误且禁用Markdown后发送最终结果失败: {inner_e}", exc_info=True)
                    await placeholder_message.edit_text("处理完成。但由于未知错误，内容可能显示不完整。")
            # --- 结束最终结果更新的错误处理 ---
        except Exception as e:
            logger.error(f"处理 /database 命令时发生错误: {str(e)}", exc_info=True)
            error_message = str(e)
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
            error_message = f"处理请求时发生错误: `{error_message}`"
            try:
                # 即使在最终错误处理中，也尝试使用 Markdown，失败则禁用
                await placeholder_message.edit_text(error_message, parse_mode="Markdown")
            except Exception as inner_e:
                logger.warning(f"发送错误消息时Markdown解析失败，尝试禁用Markdown: {inner_e}")
                try:
                    await placeholder_message.edit_text(error_message, parse_mode=None)
                except Exception as deepest_e:
                    logger.error(f"禁用Markdown后发送错误消息也失败: {deepest_e}")
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
                "示例：`/forward <源聊天ID> <消息ID>`\n"
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
            await update.message.reply_text("✅ 消息已成功转发！")
        except TelegramError as e:
            # 捕获 Telegram API 相关的错误，并给出更友好的提示
            error_message = f"❌ 转发失败！Telegram API 错误：`{e}`\n"

            # 常见错误类型提示
            error_str = str(e).lower()
            if "message not found" in error_str:
                error_message += "⚠️ 可能是消息ID不正确，或者该消息已不存在。"
            elif "chat not found" in error_str or "user not found" in error_str:
                error_message += "⚠️ 可能是源聊天ID不正确，或者Bot无法访问该聊天。"
            elif "not enough rights to forward message" in error_str:
                error_message += "⚠️ Bot 没有足够的权限从源聊天转发消息。"
            elif "bot was blocked by the user" in error_str:
                error_message += "⚠️ Bot 被目标用户（或源聊天拥有者）屏蔽了。"
            elif "forbidden: bot was blocked by the user" in error_str:
                error_message += "⚠️ Bot 被目标聊天用户（或源聊天拥有者）屏蔽了。"
            elif "peer_id_invalid" in error_str:
                error_message += "⚠️ 源聊天ID格式无效或不存在。"
            else:
                error_message += "请检查源聊天ID、消息ID是否正确，并确保Bot有相应权限。"
            await update.message.reply_text(error_message, parse_mode='Markdown')
        except Exception as e:
            # 捕获其他非 Telegram API 的意外错误
            await update.message.reply_text(
                f"❌ 发生未知错误：`{type(e).__name__}: {e}`",
                parse_mode='Markdown'
            )