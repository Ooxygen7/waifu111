import logging
from typing import Optional

import telegram
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from agent.tools_registry import parse_and_invoke_tool
from utils.LLM_utils import LLM
from utils.logging_utils import setup_logging
from typing import AsyncGenerator, Dict, Any
from telegram import Update

setup_logging()
logger = logging.getLogger(__name__)

async def update_message(text:str, placeholder):
    try:
        # Telegram 单条消息最大长度限制4096字符，保险起见用4000
        max_len = 4000
        if len(text) > max_len:
            text = text[-max_len:]
        await placeholder.edit_text(text, parse_mode="markdown")
    except BadRequest as e:
        logger.warning(f"Markdown 解析错误: {str(e)}, 禁用 Markdown 重试")
        try:
            await placeholder.edit_text(text, parse_mode=None)
        except Exception as e2:
            logger.error(f"再次尝试发送消息失败: {e2}")
            placeholder.edit_text(f"Failed: {e2}")
    except TelegramError as e:
        if "Message is not modified" in str(e):
            logger.debug(f"消息内容未变化，跳过更新: {str(e)}")
            placeholder.edit_text(f"Failed: {e}")
        else:
            logger.error(f"更新消息时出错: {str(e)}")
            placeholder.edit_text(f"Failed: {e}")

async def finalize_message(sent_message, text: str, parse: str = "html", summary: Optional[str] = None) -> None:
    """
    最终更新消息内容，确保显示最终的处理后的响应。
    Args:
        sent_message: 已发送的消息对象。
        text (str): 处理后的最终响应内容。
        parse (str): 解析模式。
        summary (str, optional): 总结内容，如果存在则以引用文本块形式附加在消息末尾。
    """
    max_len = 4000

    # 预处理文本，转义HTML特殊字符
    def sanitize_text(input_text: str) -> str:
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;',
            '"': '&quot;',
            "'": '&#39;'
        }
        for old, new in replacements.items():
            input_text = input_text.replace(old, new)
        # 移除可能导致渲染问题的控制字符
        return ''.join(char for char in input_text if ord(char) >= 32 or char in '\n\r\t')

    # 处理主文本
    text = sanitize_text(text)
    
    # 如果有summary，使用HTML引用块格式
    if summary:
        sanitized_summary = sanitize_text(summary)
        # 使用blockquote标签创建引用块
        text = f"{text}\n\n<blockquote>{sanitized_summary}</blockquote>"

    try:
        # Telegram 单条消息最大长度限制4096字符，保险起见用4000
        if len(text) <= max_len:
            await sent_message.edit_text(text, parse_mode="html")
            logger.debug("使用了HTML渲染")
        else:
            # 超长时分两段发送，先发前半段，再发后半段
            await sent_message.edit_text(text[:max_len], parse_mode="html")
            await sent_message.reply_text(text[max_len:], parse_mode="html")
        logger.info(f"输出：\r\n{text}")
    except BadRequest as e:
        logger.warning(f"HTML解析错误: {str(e)}, 禁用HTML重试")
        try:
            # 完全移除所有HTML标签
            plain_text = text.replace('<blockquote>', '').replace('</blockquote>', '\n').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
            if len(plain_text) <= max_len:
                await sent_message.edit_text(plain_text, parse_mode=None)
            else:
                await sent_message.edit_text(plain_text[:max_len], parse_mode=None)
                await sent_message.reply_text(plain_text[max_len:], parse_mode=None)
            logger.info(f"输出：\r\n{plain_text}")
        except Exception as e2:
            logger.error(f"再次尝试发送消息失败: {e2}")
            await sent_message.edit_text(f"Failed: {e2}")
    except TelegramError as e:
        if "Message is not modified" in str(e):
            logger.debug(f"最终更新时消息内容未变化，跳过更新: {str(e)}")
            await sent_message.edit_text(f"Failed: {e}")
        else:
            logger.error(f"最终更新消息时出错: {str(e)}")
            await sent_message.edit_text(f"Failed: {e}")


async def send_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_content: str, parse: str = "markdown", photo=None) -> None:
    """
    直接发送一条消息到指定的用户或群组。
    Args:
        context: Telegram bot context对象。
        chat_id (int): 用户或群组的ID。
        message_content (str): 要发送的消息内容。
        parse (str): 解析模式，默认为"markdown"。
        photo: 可选的图片文件，如果提供则以图片标题形式发送消息。
    """
    max_len = 4000
    try:
        if photo:
            # 如果有图片，以图片标题形式发送
            if len(message_content) <= max_len:
                await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=message_content, parse_mode=parse)
            else:
                # 超长时先发图片和前半段标题，再发后半段文本
                await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=message_content[:max_len], parse_mode=parse)
                await context.bot.send_message(chat_id=chat_id, text=message_content[max_len:], parse_mode=parse)
        else:
            # 纯文本消息
            if len(message_content) <= max_len:
                await context.bot.send_message(chat_id=chat_id, text=message_content, parse_mode=parse)
            else:
                # 超长时分两段发送
                await context.bot.send_message(chat_id=chat_id, text=message_content[:max_len], parse_mode=parse)
                await context.bot.send_message(chat_id=chat_id, text=message_content[max_len:], parse_mode=parse)
        logger.info(f"发送消息到 {chat_id}：\r\n{message_content}")
    except BadRequest as e:
        logger.warning(f"{parse} 解析错误: {str(e)}, 禁用 {parse} 重试")
        try:
            if photo:
                if len(message_content) <= max_len:
                    await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=message_content, parse_mode=None)
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=message_content[:max_len], parse_mode=None)
                    await context.bot.send_message(chat_id=chat_id, text=message_content[max_len:], parse_mode=None)
            else:
                if len(message_content) <= max_len:
                    await context.bot.send_message(chat_id=chat_id, text=message_content, parse_mode=None)
                else:
                    await context.bot.send_message(chat_id=chat_id, text=message_content[:max_len], parse_mode=None)
                    await context.bot.send_message(chat_id=chat_id, text=message_content[max_len:], parse_mode=None)
            logger.info(f"发送消息到 {chat_id}：\r\n{message_content}")
        except Exception as e2:
            logger.error(f"再次尝试发送消息失败: {e2}")
    except TelegramError as e:
        logger.error(f"发送消息时出错: {str(e)}")


async def send_split_message(update, message_text: str, placeholder_message=None, iteration: int = 1) -> None:
    """
    发送可能需要分割的长消息，支持HTML格式和错误处理。
    Args:
        update: Telegram Update对象
        message_text: 要发送的消息内容
        placeholder_message: 可选的占位消息，如果提供则更新该消息，否则发送新消息
        iteration: 当前迭代轮次，用于日志记录
    """
    TELEGRAM_MESSAGE_LIMIT = 4000
    
    if len(message_text) > TELEGRAM_MESSAGE_LIMIT:
        # 分割消息
        parts = []
        current_part = ""
        lines = message_text.split('\n')
        
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
                if i == 0 and placeholder_message:
                    # 更新占位消息
                    await placeholder_message.edit_text(part, parse_mode="HTML")
                else:
                    # 发送新消息
                    await update.message.reply_text(part, parse_mode="HTML")
                logger.debug(f"已发送第{iteration}轮消息部分 {i+1}/{len(parts)}")
            except telegram.error.BadRequest as e:
                logger.warning(f"HTML解析失败，尝试文本模式: {e}")
                try:
                    if i == 0 and placeholder_message:
                        await placeholder_message.edit_text(part, parse_mode=None)
                    else:
                        await update.message.reply_text(part, parse_mode=None)
                except Exception as inner_e:
                    logger.error(f"文本模式发送也失败: {inner_e}", exc_info=True)
                    error_msg = f"第{iteration}轮第{i+1}部分消息发送失败"
                    if i == 0 and placeholder_message:
                        await placeholder_message.edit_text(error_msg)
                    else:
                        await update.message.reply_text(error_msg)
    else:
        # 消息长度正常，直接发送或更新
        try:
            if placeholder_message:
                await placeholder_message.edit_text(message_text, parse_mode="HTML")
                logger.debug(f"已更新第{iteration}轮占位消息，显示结果")
            else:
                await update.message.reply_text(message_text, parse_mode="HTML")
                logger.debug(f"已发送第{iteration}轮消息")
        except telegram.error.BadRequest as e:
            logger.warning(f"HTML解析失败，尝试文本模式: {e}")
            try:
                if placeholder_message:
                    await placeholder_message.edit_text(message_text, parse_mode=None)
                    logger.debug(f"已成功使用文本模式更新第{iteration}轮占位消息")
                else:
                    await update.message.reply_text(message_text, parse_mode=None)
                    logger.debug(f"已成功使用文本模式发送第{iteration}轮消息")
            except Exception as inner_e:
                logger.error(f"文本模式发送也失败: {inner_e}", exc_info=True)
                error_msg = f"第{iteration}轮处理完成，但内容显示失败"
                if placeholder_message:
                    await placeholder_message.edit_text(error_msg)
                else:
                    await update.message.reply_text(error_msg)


async def send_error_message(update, error_message: str, placeholder_message=None) -> None:
    """
    发送错误消息，支持HTML格式和容错处理。
    Args:
        update: Telegram Update对象
        error_message: 错误消息内容
        placeholder_message: 可选的占位消息，如果提供则更新该消息，否则发送新消息
    """
    try:
        if placeholder_message:
            await placeholder_message.edit_text(error_message, parse_mode="HTML")
        else:
            await update.message.reply_text(error_message, parse_mode="HTML")
    except Exception as inner_e:
        logger.warning(f"发送错误消息时HTML解析失败，尝试禁用HTML: {inner_e}")
        try:
            if placeholder_message:
                await placeholder_message.edit_text(error_message, parse_mode=None)
            else:
                await update.message.reply_text(error_message, parse_mode=None)
        except Exception as deepest_e:
            logger.error(f"禁用HTML后发送错误消息也失败: {deepest_e}")
            fallback_msg = "处理请求时发生未知错误，且无法格式化错误信息。"
            if placeholder_message:
                await placeholder_message.edit_text(fallback_msg)
            else:
                await update.message.reply_text(fallback_msg)






async def handle_agent_session(
    update: Update,
    agent_session: AsyncGenerator[Dict[str, Any], None],
    character_name: str = "cyberwaifu"
) -> None:
    """
    处理 Agent 会话的异步生成器，并向用户发送格式化的消息。
    采用“发送新占位符 -> 编辑为结果”的模式。

    Args:
        update: Telegram Update 对象。
        agent_session: 从 run_agent_session 返回的异步生成器。
        character_name: 用于在消息中显示的角色名称。
    """
    if not update.message:
        return

    current_placeholder = None

    try:
        async for state in agent_session:
            status = state.get("status")
            
            if status == "initializing":
                logger.debug(state.get("message"))
                # 初始化时不发送消息，等待第一个 thinking 状态

            elif status == "thinking":
                iteration = state.get("iteration", "?")
                # 为新一轮分析发送一个新的占位符
                current_placeholder = await update.message.reply_text(f"🔄 第 {iteration} 轮分析中...")

            elif status == "tool_call":
                iteration = state.get("iteration", "?")
                llm_text = state.get("llm_text", "")
                tool_results = state.get("tool_results", [])
                
                if not llm_text and not tool_results:
                    continue

                iteration_message_text = f"<b>🤖 第 {iteration} 轮分析结果</b>\n\n"
                if llm_text:
                    iteration_message_text += f"<b>{character_name}:</b> {llm_text.strip()}\n\n"
                
                if tool_results:
                    tool_results_html = []
                    for res in tool_results:
                        tool_name = res.get('tool_name', '未知工具')
                        tool_result = str(res.get('result', ''))
                        trimmed_result = (tool_result[:2000] + "...") if len(tool_result) > 2000 else tool_result
                        tool_html = f"<b>🔧 {tool_name} 执行结果:</b>\n<blockquote expandable>{trimmed_result}</blockquote>"
                        tool_results_html.append(tool_html)
                    iteration_message_text += "\n".join(tool_results_html)

                # 编辑当前轮次的占位符，显示结果
                await send_split_message(update, iteration_message_text, placeholder_message=current_placeholder, iteration=iteration)
                current_placeholder = None # 重置占位符，以便下一轮创建新的

            elif status == "final_response":
                final_content = state.get("content", "处理完成，但未生成最终回复。")
                final_message = f"<b>🤖 {character_name} 最终回复:</b>\n\n{final_content}"
                # 如果有占位符，编辑它；否则发送新消息
                await send_split_message(update, final_message, placeholder_message=current_placeholder)
                current_placeholder = None
                logger.info(f"最终回复: {final_content}")

            elif status == "max_iterations_reached":
                max_iter_msg = f"<b>⚠️ {character_name}提醒</b>\n\n老师，分析轮次已达上限，如需继续分析请重新发起请求哦！"
                await send_split_message(update, max_iter_msg, placeholder_message=current_placeholder)
                current_placeholder = None

            elif status == "error":
                error_message = state.get("message", "未知错误")
                await send_error_message(update, f"处理请求时发生错误: <code>{error_message}</code>", placeholder_message=current_placeholder)
                current_placeholder = None

    except Exception as e:
        logger.error(f"处理 Agent 会话消息时发生意外错误: {e}", exc_info=True)
        error_message = f"处理请求时发生意外错误: <code>{str(e)}</code>"
        # 尝试用最后的占位符显示错误，否则发送新消息
        await send_error_message(update, error_message, placeholder_message=current_placeholder)
