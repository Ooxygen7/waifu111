import asyncio
import json
import re

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
        trigger='q',
        menu_text='',
        bot_admin_required=True,
        show_in_menu=False,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /q command to interact with LLM and invoke database analysis tools based on user input.
        Args:
            update: The Telegram Update object containing the user input.
            context: The Telegram ContextTypes object for bot interaction.
        """
        # 获取用户输入（去掉命令部分）
        user_input = update.message.text.strip()
        if len(user_input.split()) > 1:
            user_input = " ".join(user_input.split()[1:])  # 去掉 /database 命令本身
        else:
            await update.message.reply_text("请在 /database 命令后提供具体内容，例如：/database 查看用户123的详情",
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
        Args:
            update: The Telegram Update object containing the user input.
            context: The Telegram ContextTypes object for bot interaction.
            user_input: The processed user input text.
            placeholder_message: The placeholder message to be edited with the final result.
        """
        try:
            # 初始化 LLM 客户端
            client = llm.LLM('deepseek-v3')
            logger.debug("LLM 客户端初始化完成")
            # 构建与 LLM 交互的 messages，包含系统提示和用户输入
            prompt_text = DatabaseToolRegistry.get_prompt_text()
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"{prompt_text}\n\n"
                        "你是一个智能助手，根据用户输入判断是否需要调用数据库分析工具。"
                        "如果需要调用工具，请以 JSON 格式返回工具调用信息；否则，直接用中文回复用户的请求。"
                        "如果用户请求涉及多个步骤，可以返回多个工具调用指令，格式为 {'tool_calls': [...]}。"
                        "工具调用结果会反馈给你，你可以基于结果进行分析或决定下一步操作。"
                    )
                },
                {
                    "role": "user",
                    "content": f"用户输入: {user_input}"
                }
            ]
            final_result = ""
            current_messages = messages.copy()
            max_iterations = 8  # 防止无限循环
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                # 直接设置 messages
                client.set_messages(current_messages)
                logger.debug(f"已设置 messages: {current_messages}")
                # 获取 LLM 响应
                ai_response = await client.final_response()
                logger.info(f"LLM 响应: {ai_response}")
                # 解析 LLM 响应并调用工具
                result, intermediate_results = await parse_and_invoke_tool(ai_response, update, context)
                if intermediate_results:  # 如果有工具调用
                    logger.info(f"工具调用结果: {result}")
                    # 记录完整结果用于日志和 LLM 反馈
                    logger.debug(f"完整工具调用结果: {intermediate_results}")
                    # 修剪工具调用结果用于 Telegram 消息展示，每个工具结果最多 80 个字符
                    trimmed_results = []
                    for res in intermediate_results:
                        tool_name = res['tool_name']
                        tool_result = str(res['result'])
                        if len(tool_result) > 80:
                            trimmed_result = tool_result[:80] + "..."
                        else:
                            trimmed_result = tool_result
                        trimmed_results.append(f"{tool_name} 执行结果: {trimmed_result}")
                    # 使用 Markdown 代码块包裹修剪后的工具调用结果，确保每个工具都展示
                    formatted_result = "```\n" + "\n".join(trimmed_results) + "\n```"
                    final_result += formatted_result + "\n"
                    # 添加时间戳以确保内容变化
                    import time
                    await placeholder_message.edit_text(
                        f"处理中...\n当前结果:\n{formatted_result}\n更新时间: {time.time()}",
                        parse_mode="Markdown"
                    )
                    # 完整结果反馈给 LLM，不修剪
                    feedback_content = "工具调用结果:\n" + "\n".join(
                        [f"{res['tool_name']} 执行结果: {res['result']}" for res in intermediate_results]
                    )
                    current_messages.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                    current_messages.append({
                        "role": "user",
                        "content": feedback_content
                    })
                    logger.debug(f"已将完整工具调用结果反馈给 LLM: {feedback_content}")
                else:
                    logger.info(f"未调用工具，直接回复用户: {result}")
                    final_result += result
                    break  # 没有工具调用，结束循环
            # 检查最终结果长度是否超过 Telegram 限制（4096 字符）
            TELEGRAM_MESSAGE_LIMIT = 4096
            if len(final_result) > TELEGRAM_MESSAGE_LIMIT:
                final_result = final_result[:TELEGRAM_MESSAGE_LIMIT - 30] + "..."
                final_result += "\n\n注意：结果过长，已被截断。"
            # 编辑占位消息以显示最终结果，使用 Markdown 格式
            try:
                await placeholder_message.edit_text(final_result.strip(), parse_mode="Markdown")
            except Exception as error:
                logger.warning(f"发送消息失败，尝试禁用md: {error}")
                await placeholder_message.edit_text(final_result.strip())
            logger.debug("已编辑占位消息，显示最终结果")
        except Exception as e:
            logger.error(f"处理 /database 命令时发生错误: {str(e)}")
            # 编辑占位消息以显示错误信息，使用 Markdown 格式，并限制错误信息长度
            error_message = str(e)
            if len(error_message) > 100:
                error_message = error_message[:100] + "..."
            error_message = f"处理请求时发生错误: `{error_message}`"
            await placeholder_message.edit_text(error_message, parse_mode="Markdown")
            logger.debug("已编辑占位消息，显示错误信息")

async def parse_and_invoke_tool(ai_response: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[
    str, list]:
    """
    Parse the AI response and invoke tools if necessary. Returns the final response and intermediate results.
    This function extracts JSON content from the response (ignoring surrounding text) and processes tool calls.
    Args:
        ai_response: The raw response from the LLM.
        update: The Telegram Update object.
        context: The Telegram ContextTypes object.
    Returns:
        tuple: (final_response, intermediate_results)
        - final_response: The response to send to the user.
        - intermediate_results: List of results from tool calls for feedback to LLM.
    """
    try:
        # 尝试提取可能的 JSON 内容（包括 Markdown 代码块和纯文本中的 JSON）
        json_candidate = None
        # 匹配 Markdown 代码块中的内容
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', ai_response)
        if code_block_match:
            json_candidate = code_block_match.group(1).strip()
            logger.debug(f"从 Markdown 代码块中提取内容: {json_candidate}")
        else:
            # 如果没有代码块，尝试直接提取纯文本中的 JSON 格式
            json_match = re.search(r'\{(?:[^\{\}]|\{(?:[^\{\}]|\{[^ \{\}]*\})*\})*\}', ai_response)
            if json_match:
                json_candidate = json_match.group(0).strip()
                logger.debug(f"从纯文本中提取 JSON 内容: {json_candidate}")
            else:
                logger.debug("未找到 JSON 内容，直接返回原始文本")
                return ai_response, []
        # 尝试解析提取的 JSON 内容
        response_data = json.loads(json_candidate)
        tool_calls = []
        # 检查是否为多工具调用格式 {"tool_calls": [...]}
        if "tool_calls" in response_data and isinstance(response_data["tool_calls"], list):
            tool_calls = response_data["tool_calls"]
        # 检查是否为单工具调用格式 {"tool_name": "..."}
        elif "tool_name" in response_data:
            parameters = response_data.get("parameters", {})
            tool_calls = [{"tool_name": response_data["tool_name"], "parameters": parameters}]
        if tool_calls:
            results = []
            intermediate_results = []
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                logger.info(f"调用工具 {i + 1}/{len(tool_calls)}: {tool_name}，参数: {parameters}")
                # 直接从统一工具池 ALL_TOOLS 获取工具
                tool_func = ALL_TOOLS.get(tool_name)
                if tool_func:
                    try:
                        # 只传递 parameters 中的参数，不传递 update 和 context 作为位置参数
                        result = await tool_func(**parameters) if asyncio.iscoroutinefunction(tool_func) else tool_func(
                            **parameters)
                        results.append(f"工具 {tool_name} 执行结果: {result}")
                        intermediate_results.append({
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "result": result
                        })
                        logger.info(f"工具 {tool_name} 执行成功: {result}")
                    except Exception as e:
                        error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
                        results.append(error_msg)
                        intermediate_results.append({
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "result": error_msg
                        })
                        logger.error(error_msg)
                else:
                    error_msg = f"未找到工具: {tool_name}"
                    results.append(error_msg)
                    intermediate_results.append({
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "result": error_msg
                    })
                    logger.warning(error_msg)
            # 汇总所有工具调用的结果
            return "\n".join(results), intermediate_results
    except json.JSONDecodeError as jde:
        # 如果无法解析为 JSON，说明提取的内容不是有效 JSON，直接返回原始响应
        logger.debug(f"提取的内容不是有效 JSON 格式，直接返回原始文本: {str(jde)}")
        return ai_response, []
    except Exception as e:
        logger.error(f"解析或调用工具时发生错误: {str(e)}")
        return f"处理工具调用时发生错误: {str(e)}", []
    # 如果没有工具调用，直接返回原始响应
    return ai_response, []
