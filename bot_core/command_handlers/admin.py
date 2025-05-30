import asyncio
import json
import re
import time

import telegram
from telegram import Update
from telegram.ext import ContextTypes
import logging

from LLM_tools.tools_registry import DatabaseToolRegistry, ALL_TOOLS
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
                    await parse_and_invoke_tool(ai_response, update, context)
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

async def parse_and_invoke_tool(ai_response: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[
    str, list, bool]:
    """
    Parse the AI response and invoke tools if necessary. Returns the LLM's text output,
    list of full tool results for LLM feedback, and a boolean indicating if tools were called.
    This function extracts JSON content from the response (ignoring surrounding text) and processes tool calls.
    Args:
        ai_response: The raw response from the LLM.
        update: The Telegram Update object.
        context: The Telegram ContextTypes object.
    Returns:
        tuple: (llm_text_output, tool_results_for_llm_feedback, had_tool_calls)
        - llm_text_output: The textual part of the LLM's response.
        - tool_results_for_llm_feedback: List of detailed results from tool calls for feedback to LLM.
        - had_tool_calls: Boolean, True if any tool calls were successfully parsed and invoked.
    """
    llm_text_output = ai_response.strip()  # 默认整个响应都是文本
    tool_results_for_llm_feedback = []
    had_tool_calls = False
    response_data = None
    json_content_extracted = ""
    # 尝试提取 Markdown 代码块中的 JSON
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', ai_response)
    if code_block_match:
        json_content_extracted = code_block_match.group(1).strip()
        # 从原始响应中移除 JSON 代码块，得到 LLM 的文本部分
        llm_text_output = ai_response.replace(code_block_match.group(0), "").strip()
        logger.debug(f"从 Markdown 代码块中提取 JSON，剩余文本: '{llm_text_output}'")
    else:
        # 如果没有代码块，尝试将整个响应解析为 JSON (仅当它是纯JSON时)
        try:
            parsed_full_response = json.loads(ai_response)
            # 如果整个响应是有效 JSON，则文本部分为空
            response_data = parsed_full_response
            json_content_extracted = ai_response
            llm_text_output = ""  # 整个响应都是 JSON
            logger.debug("整个响应是纯 JSON 格式")
        except json.JSONDecodeError:
            # 如果整个响应不是纯 JSON，则尝试在文本中查找独立的 JSON 对象 (通常不是 LLM 返回的首选格式)
            # 这个正则比较通用，但对于复杂的嵌套或多JSON对象可能不完美
            json_match = re.search(r'\{(?:[^\{\}]|\{(?:[^\{\}]|\{[^ \{\}]*\})*\})*\}', ai_response)
            if json_match:
                json_content_extracted = json_match.group(0).strip()
                llm_text_output = ai_response.replace(json_match.group(0), "").strip()
                logger.debug(f"从纯文本中提取 JSON，剩余文本: '{llm_text_output}'")
            else:
                logger.debug("未找到 JSON 内容，整个响应作为文本返回")
                return llm_text_output, [], False  # 没有工具调用，直接返回文本
    if json_content_extracted and not response_data:  # 如果通过正则提取了JSON但还没解析
        try:
            response_data = json.loads(json_content_extracted)
        except json.JSONDecodeError as jde:
            logger.warning(f"无法解析提取的 JSON 内容: '{json_content_extracted}'. 错误: {jde}. 将其视为文本。")
            # 如果提取的 JSON 无效，则将其内容追加回文本输出
            llm_text_output = (llm_text_output + "\n" + json_content_extracted).strip()
            return llm_text_output, [], False
    if response_data:
        tool_calls = []
        # 检查是否为多工具调用格式 {"tool_calls": [...]}
        if "tool_calls" in response_data and isinstance(response_data["tool_calls"], list):
            tool_calls = response_data["tool_calls"]
        # 检查是否为单工具调用格式 {"tool_name": "..."}
        elif "tool_name" in response_data:
            parameters = response_data.get("parameters", {})
            tool_calls = [{"tool_name": response_data["tool_name"], "parameters": parameters}]
        if tool_calls:
            had_tool_calls = True
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                logger.info(f"解析到工具调用 {i + 1}/{len(tool_calls)}: {tool_name}，参数: {parameters}")
                tool_func = ALL_TOOLS.get(tool_name)
                if tool_func:
                    try:
                        # 确保只传递工具函数实际需要的参数
                        # 这是一个更健壮的参数传递方式，特别是当LLM可能生成多余参数时
                        import inspect
                        sig = inspect.signature(tool_func)
                        filtered_params = {k: v for k, v in parameters.items() if k in sig.parameters}
                        result = await tool_func(**filtered_params) if asyncio.iscoroutinefunction(
                            tool_func) else tool_func(**filtered_params)
                        tool_results_for_llm_feedback.append({
                            "tool_name": tool_name,
                            "parameters": parameters,  # 保持原始参数以便LLM理解
                            "result": result
                        })
                        logger.info(f"工具 {tool_name} 执行成功: {result}")
                    except Exception as e:
                        error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
                        tool_results_for_llm_feedback.append({
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "result": error_msg
                        })
                        logger.error(error_msg, exc_info=True)
                else:
                    error_msg = f"未找到工具: {tool_name}"
                    tool_results_for_llm_feedback.append({
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "result": error_msg
                    })
                    logger.warning(error_msg)

    return llm_text_output, tool_results_for_llm_feedback, had_tool_calls