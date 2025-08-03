import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot_core.public_functions.conversation import PrivateConv
from bot_core.public_functions.decorators import Decorators
from . import features
from utils.logging_utils import setup_logging
setup_logging()
logger = logging.getLogger(__name__)


from bot_core.command_handlers.regist import CommandHandlers

@Decorators.ensure_user_info_updated
async def private_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理私聊消息，包括命令和普通对话。
    """
    if not update.message or not update.message.from_user:
        return

    user_id = update.message.from_user.id
    message_text = update.message.text or ""

    try:
        if message_text.startswith('/'):
            command_parts = message_text[1:].split()
            command_with_bot_name = command_parts[0]
            command = command_with_bot_name.split('@')[0]
            args = command_parts[1:]
            
            # 将参数列表附加到 context
            context.args = args

            handler = CommandHandlers.get_command_handler(command, "private")
            if handler:
                logger.info(f"用户 {user_id} 执行命令: {message_text}")
                await handler(update, context)
            else:
                await update.message.reply_text("未知命令。")
            return

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
