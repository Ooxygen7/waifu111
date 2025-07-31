import logging
from typing import Optional, AsyncGenerator, Dict, Any, Union
import html
import telegram
from telegram import Update, Message
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4000

class MessageFactory:
    """
    一个用于发送和编辑Telegram消息的工厂类，封装了通用逻辑。
    - 自动处理长消息分割。
    - 统一处理Markdown/HTML解析错误和回退。
    - 简化消息发送和编辑的接口。
    """

    def __init__(self, update: Optional[Update] = None, context: Optional[ContextTypes.DEFAULT_TYPE] = None):
        if not update and not context:
            raise ValueError("必须提供 Update 或 ContextTypes.DEFAULT_TYPE 对象")
        self.update = update
        self.context = context
        self.bot = self.context.bot if self.context else self.update.get_bot()

    async def _send_or_edit_internal(
        self,
        text: str,
        chat_id: Optional[int] = None,
        placeholder: Optional[Message] = None,
        parse_mode: str = "HTML",
        photo: Optional[bytes] = None
    ) -> Optional[Message]:
        """
        内部核心方法，处理所有消息的发送和编辑。
        """
        chat_id = chat_id or (self.update.message.chat_id if self.update and self.update.message else None)
        if not chat_id:
            logger.error("无法确定 chat_id")
            return None

        # 1. 分割消息
        text_parts = self._split_text(text)

        # 2. 发送或编辑
        sent_message = None
        for i, part in enumerate(text_parts):
            is_first_part = (i == 0)
            target_message = placeholder if is_first_part and placeholder else None
            
            try:
                # 尝试使用指定解析模式发送
                sent_message = await self._try_send_part(
                    chat_id=chat_id,
                    text_part=part,
                    placeholder=target_message,
                    parse_mode=parse_mode,
                    photo=photo if is_first_part else None # 只有第一部分带图片
                )
            except BadRequest:
                logger.warning(f"{parse_mode} 解析失败，回退到纯文本模式。")
                try:
                    # 回退到纯文本模式
                    sent_message = await self._try_send_part(
                        chat_id=chat_id,
                        text_part=part,
                        placeholder=target_message,
                        parse_mode=None,
                        photo=photo if is_first_part else None
                    )
                except Exception as e:
                    logger.error(f"纯文本模式发送也失败: {e}", exc_info=True)
                    error_msg = f"消息部分 {i+1} 发送失败。"
                    if target_message:
                        await target_message.edit_text(error_msg)
                    else:
                        await self.bot.send_message(chat_id=chat_id, text=error_msg)
            except TelegramError as e:
                if "Message is not modified" in str(e):
                    logger.debug("消息未修改，跳过。")
                else:
                    logger.error(f"发送消息时发生 Telegram 错误: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"发送消息时发生未知错误: {e}", exc_info=True)

            # 更新 placeholder 以便下一部分回复
            if sent_message and not placeholder:
                placeholder = sent_message

        return placeholder or sent_message


    async def _try_send_part(
        self,
        chat_id: int,
        text_part: str,
        placeholder: Optional[Message],
        parse_mode: Optional[str],
        photo: Optional[bytes]
    ) -> Message:
        """尝试发送或编辑单个消息部分。"""
        if placeholder:
            # 如果有图片，不能编辑，只能发送新消息
            if photo:
                await placeholder.delete() # 删除占位符
                return await self.bot.send_photo(chat_id=chat_id, photo=photo, caption=text_part, parse_mode=parse_mode)
            return await placeholder.edit_text(text=text_part, parse_mode=parse_mode)
        
        if photo:
            return await self.bot.send_photo(chat_id=chat_id, photo=photo, caption=text_part, parse_mode=parse_mode)
        
        # 如果是回复，使用 reply_text
        if self.update and self.update.message:
             return await self.update.message.reply_text(text=text_part, parse_mode=parse_mode)
        # 否则直接发送
        return await self.bot.send_message(chat_id=chat_id, text=text_part, parse_mode=parse_mode)


    def _split_text(self, text: str) -> list[str]:
        """将长文本分割成多个部分。"""
        if len(text) <= TELEGRAM_MESSAGE_LIMIT:
            return [text]
        
        parts = []
        current_part = ""
        for line in text.split('\n'):
            if len(current_part) + len(line) + 1 > TELEGRAM_MESSAGE_LIMIT:
                if current_part:
                    parts.append(current_part.strip())
                # 如果单行超长，强制截断
                while len(line) > TELEGRAM_MESSAGE_LIMIT:
                    parts.append(line[:TELEGRAM_MESSAGE_LIMIT])
                    line = line[TELEGRAM_MESSAGE_LIMIT:]
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        
        if current_part.strip():
            parts.append(current_part.strip())
            
        return parts

    async def send(self, text: str, chat_id: Optional[int] = None, parse_mode: str = "HTML", photo: Optional[bytes] = None) -> Optional[Message]:
        """发送一条新消息。"""
        return await self._send_or_edit_internal(text=text, chat_id=chat_id, parse_mode=parse_mode, photo=photo)

    async def edit(self, placeholder: Message, text: str, parse_mode: str = "HTML", summary: Optional[str] = None) -> Optional[Message]:
        """编辑一条已存在的消息。"""
        if summary:
            # 使用 blockquote 标签创建引用块
            text = f"{text}\n\n<blockquote>{html.escape(summary)}</blockquote>"
        
        return await self._send_or_edit_internal(text=text, placeholder=placeholder, parse_mode=parse_mode)


# --- 向后兼容的函数 ---

async def update_message(text: str, placeholder: Message):
    """
    兼容旧版：更新一条消息。
    """
    try:
        await placeholder.edit_text(text, parse_mode="markdown")
    except BadRequest:
        logger.warning("Markdown 解析失败，回退到纯文本模式。")
        try:
            await placeholder.edit_text(text)
        except Exception as e:
            logger.error(f"纯文本模式更新消息失败: {e}", exc_info=True)
    except TelegramError as e:
        if "Message is not modified" not in str(e):
            logger.error(f"更新消息时发生 Telegram 错误: {e}", exc_info=True)


async def finalize_message(sent_message: Message, text: str, parse: str = "html", summary: Optional[str] = None) -> None:
    """
    兼容旧版：最终确定一条消息。
    """
    if summary:
        text = f"{text}\n\n<blockquote>{html.escape(summary)}</blockquote>"
    
    try:
        await sent_message.edit_text(text, parse_mode=parse)
    except BadRequest:
        logger.warning(f"{parse} 解析失败，回退到纯文本模式。")
        try:
            await sent_message.edit_text(text)
        except Exception as e:
            logger.error(f"纯文本模式最终确定消息失败: {e}", exc_info=True)
    except TelegramError as e:
        if "Message is not modified" not in str(e):
            logger.error(f"最终确定消息时发生 Telegram 错误: {e}", exc_info=True)


async def send_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_content: str, parse: str = "markdown", photo=None) -> None:
    """
    兼容旧版：发送一条消息。
    建议使用: `MessageFactory(context=context).send(text, chat_id)`
    """
    factory = MessageFactory(context=context)
    await factory.send(text=message_content, chat_id=chat_id, parse_mode=parse, photo=photo)


# --- 重构后的 Agent 会话处理器 ---

async def handle_agent_session(
    update: Update,
    agent_session: AsyncGenerator[Dict[str, Any], None],
    character_name: str = "cyberwaifu"
) -> None:
    """
    处理 Agent 会话的异步生成器，并向用户发送格式化的消息。
    使用 MessageFactory 来管理消息的创建和更新。
    """
    if not update.message:
        return

    factory = MessageFactory(update=update)
    current_placeholder: Optional[Message] = None

    try:
        async for state in agent_session:
            status = state.get("status")
            
            if status == "initializing":
                logger.debug(state.get("message"))
                continue

            elif status == "thinking":
                iteration = state.get("iteration", "?")
                current_placeholder = await update.message.reply_text(f"🔄 第 {iteration} 轮分析中...")

            elif status == "tool_call":
                iteration = state.get("iteration", "?")
                llm_text = state.get("llm_text", "")
                tool_results = state.get("tool_results", [])
                
                if not llm_text and not tool_results:
                    continue

                iteration_message_text = f"<b>🤖 第 {iteration} 轮分析结果</b>\n\n"
                if llm_text:
                    iteration_message_text += f"<b>{character_name}:</b> {html.escape(llm_text.strip())}\n\n"
                
                if tool_results:
                    tool_results_html = []
                    for res in tool_results:
                        tool_name = res.get('tool_name', '未知工具')
                        tool_result = str(res.get('result', ''))
                        trimmed_result = (tool_result[:2000] + "...") if len(tool_result) > 2000 else tool_result
                        tool_html = f"<b>🔧 {tool_name} 执行结果:</b>\n<blockquote expandable>{html.escape(trimmed_result)}</blockquote>"
                        tool_results_html.append(tool_html)
                    iteration_message_text += "\n".join(tool_results_html)

                if current_placeholder:
                    await factory.edit(current_placeholder, iteration_message_text)
                else:
                    current_placeholder = await factory.send(iteration_message_text)
                current_placeholder = None # 重置占位符

            elif status == "final_response":
                final_content = state.get("content", "处理完成，但未生成最终回复。")
                final_message = f"<b>🤖 {character_name} 最终回复:</b>\n\n{html.escape(final_content)}"
                if current_placeholder:
                    await factory.edit(current_placeholder, final_message)
                else:
                    await factory.send(final_message)
                current_placeholder = None
                logger.info(f"最终回复: {final_content}")

            elif status == "max_iterations_reached":
                max_iter_msg = f"<b>⚠️ {character_name}提醒</b>\n\n老师，分析轮次已达上限，如需继续分析请重新发起请求哦！"
                if current_placeholder:
                    await factory.edit(current_placeholder, max_iter_msg)
                else:
                    await factory.send(max_iter_msg)
                current_placeholder = None

            elif status == "error":
                error_message = state.get("message", "未知错误")
                error_text = f"处理请求时发生错误: <code>{html.escape(error_message)}</code>"
                if current_placeholder:
                    await factory.edit(current_placeholder, error_text)
                else:
                    await factory.send(error_text)
                current_placeholder = None

    except Exception as e:
        logger.error(f"处理 Agent 会话消息时发生意外错误: {e}", exc_info=True)
        error_message = f"处理请求时发生意外错误: <code>{html.escape(str(e))}</code>"
        if current_placeholder:
            await factory.edit(current_placeholder, error_message)
        else:
            # 尝试回复原始消息
            if update.message:
                await factory.send(error_message)
