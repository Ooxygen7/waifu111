from telegram.error import BadRequest, TelegramError

from bot_core.public_functions.logging import logger


async def finalize_message(sent_message, cleared_response: str) -> None:
    """
    最终更新消息内容，确保显示最终的处理后的响应。
    Args:
        sent_message: 已发送的消息对象。
        cleared_response (str): 处理后的最终响应内容。
    """
    max_len = 4000
    try:
        # Telegram 单条消息最大长度限制4096字符，保险起见用4000
        if len(cleared_response) <= max_len:
            await sent_message.edit_text(cleared_response, parse_mode="markdown")
        else:
            # 超长时分两段发送，先发前半段，再发后半段
            await sent_message.edit_text(cleared_response[:max_len], parse_mode="markdown")
            await sent_message.reply_text(cleared_response[max_len:], parse_mode="markdown")
    except BadRequest as e:
        logger.warning(f"Markdown 解析错误: {str(e)}, 禁用 Markdown 重试")
        try:
            if len(cleared_response) <= max_len:
                await sent_message.edit_text(cleared_response, parse_mode=None)
            else:
                await sent_message.edit_text(cleared_response[:max_len], parse_mode=None)
                await sent_message.reply_text(cleared_response[max_len:], parse_mode=None)
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
