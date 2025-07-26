import telegram
from telegram import Update
from telegram.ext import ContextTypes
from utils.logging_utils import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__)

class BotError(Exception):
    """自定义Bot异常基类"""
    pass


class ConfigError(Exception):
    """自定义Bot运行异常基类"""
    pass


class DatabaseError(Exception):
    """自定义Bot运行异常基类"""
    pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    全局错误处理器，捕获并处理所有未捕获的异常。

    Args:
        update (Update): Telegram 更新对象。
        context (ContextTypes.DEFAULT_TYPE): 上下文对象。

    Note:
        错误处理的优先级：
        1. Telegram API相关错误
        2. Bot运行时错误
        3. 配置错误
        4. 其他未捕获的异常
    """
    error = context.error
    chat_id = update.effective_chat.id if update and update.effective_chat else "未知"
    user_id = update.effective_user.id if update and update.effective_user else "未知"

    try:
        if isinstance(error, telegram.error.BadRequest):
            logger.error(
                f"Telegram API错误: {str(error)}，用户ID: {user_id}，聊天ID: {chat_id}",
                exc_info=True,
            )
            error_message = f"发送消息时发生错误，请稍后重试。\n\n<details><summary>详细错误信息</summary>\n\n{str(error)[:3000]}\n</details>"
        elif isinstance(error, BotError):
            logger.error(
                f"Bot运行错误: {str(error)}，用户ID: {user_id}，聊天ID: {chat_id}",
                exc_info=True,
            )
            error_message = f"Bot运行出现错误，请稍后重试。\n\n<details><summary>详细错误信息</summary>\n\n{str(error)[:3000]}\n</details>"
        elif isinstance(error, ConfigError):
            logger.error(
                f"配置错误: {str(error)}，用户ID: {user_id}，聊天ID: {chat_id}",
                exc_info=True,
            )
            error_message = f"Bot配置出现错误，请联系管理员。\n\n<details><summary>详细错误信息</summary>\n\n{str(error)[:3000]}\n</details>"
        else:
            logger.error(
                f"未处理的错误: {str(error)}，用户ID: {user_id}，聊天ID: {chat_id}",
                exc_info=True,
            )
            error_message = f"发生未知错误，请稍后重试。\n\n<details><summary>详细错误信息</summary>\n\n{str(error)[:3000]}\n</details>"
        # 仅在有效的消息上下文中发送错误提示
        if (
            update
            and update.message
            and context.user_data
            and not context.user_data.get("error_notified")
        ):
            try:
                await update.message.reply_text(error_message, parse_mode="HTML")
            except telegram.error.BadRequest:
                await update.message.reply_text(error_message, parse_mode=None)
            context.user_data["error_notified"] = True  # 标记已发送错误消息
        # elif update and update.inline_query and not context.user_data.get("error_notified"):
        #     # 处理内联查询错误
        #     try:
        #         from telegram import InlineQueryResultArticle, InputTextMessageContent
        #         error_results = [
        #             InlineQueryResultArticle(
        #                 id="error",
        #                 title="查询出错",
        #                 description="处理查询时发生错误",
        #                 input_message_content=InputTextMessageContent(
        #                     message_text=f"查询失败：{str(error)[:500]}"
        #                 )
        #             )
        #         ]
        #         await update.inline_query.answer(results=error_results, cache_time=60)
        #         context.user_data["error_notified"] = True
        #     except Exception as inline_error:
        #         logger.error(f"发送内联查询错误响应失败: {inline_error}", exc_info=True)
    except Exception as e:
        # 确保错误处理器本身的错误不会导致程序崩溃
        logger.critical(
            f"错误处理器发生错误: {str(e)}，原始错误: {str(error)}", exc_info=True
        )
