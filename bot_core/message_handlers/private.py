import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot_core.public_functions.conversation import PrivateConv
from bot_core.public_functions.decorators import Decorators
from . import features
from utils.logging_utils import setup_logging
setup_logging()
logger = logging.getLogger(__name__)


@Decorators.ensure_user_info_updated
async def private_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理私聊消息。

    Args:
        update (Update): Telegram 更新对象。
        context (ContextTypes.DEFAULT_TYPE): 上下文对象。

    Note:
        此函数已使用 @check_message_and_user 装饰器进行用户和消息有效性检查。
        如果消息无效或用户未注册，装饰器会自动处理并返回。
    """
    if not update.message:
        return
    if not update.message.from_user:
        return
    user_id = update.message.from_user.id
    try:
        # 检查是否在新建角色状态
        newchar_state = context.bot_data.get('newchar_state', {}).get(user_id)
        if newchar_state:
            logger.info(f"用户处于新建角色状态，用户ID: {user_id}")
            await features.private_newchar(update, newchar_state, user_id)
            return
        
        # 检查用户是否发送了图片、贴纸或GIF
        if update.message.photo or update.message.sticker or update.message.animation:
            logger.info(f"用户发送了图片、贴纸或GIF，调用处理函数，用户ID: {user_id}")
            await features.f_or_not(update, context)
            return
        
        userconv = PrivateConv(update, context)
        await userconv.response()

    except Exception as e:
        logger.error(f"处理私聊消息时出错: {str(e)}，用户ID: {user_id}", exc_info=True)
