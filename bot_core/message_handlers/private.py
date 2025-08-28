import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot_core.services.conversation import PrivateConv
from bot_core.services.utils.decorators import Decorators
from bot_core.services.utils.tg_parse import parse_commands_with_and
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

    # 检查是否为命令
    if message_text.startswith('/'):
        # 解析包含&&的指令
        commands = parse_commands_with_and(message_text)

        if commands:
            # 按顺序执行每个指令
            for command, args in commands:
                # 处理@botname的情况
                command_parts_at = command.split('@')
                command_name = command_parts_at[0]

                # 如果命令中包含@，则检查是否是发给本机器人的
                if len(command_parts_at) > 1:
                    bot_username = command_parts_at[1]
                    logger.info(f"检测到@用户名: {bot_username}, 当前机器人用户名: {context.bot.username}")
                    if bot_username != context.bot.username:
                        logger.info(f"跳过不匹配的@命令: /{command_name}@{bot_username}, 当前机器人: {context.bot.username}")
                        continue  # 不是发给我的命令，跳过

                handler = CommandHandlers.get_command_handler(command_name, "private")
                if handler:
                    logger.info(f"私聊命令: /{command_name}, 用户ID: {user_id}")
                    # 将命令参数填充到 context.args
                    context.args = args
                    await handler(update, context)

            return
        else:
            # 回退到旧的解析方式（单指令）
            command_parts = message_text[1:].split()
            command_full = command_parts[0]
            command_parts_at = command_full.split('@')
            command = command_parts_at[0]

            # 如果命令中包含@，则检查是否是发给本机器人的
            if len(command_parts_at) > 1:
                bot_username = command_parts_at[1]
                logger.info(f"单命令检测到@用户名: {bot_username}, 当前机器人用户名: {context.bot.username}")
                if bot_username != context.bot.username:
                    logger.info(f"跳过不匹配的@命令: /{command}@{bot_username}, 当前机器人: {context.bot.username}")
                    return  # 不是发给我的命令，忽略

            handler = CommandHandlers.get_command_handler(command, "private")
            if handler:
                logger.info(f"私聊命令: /{command}, 用户ID: {user_id}")
                # 将命令参数填充到 context.args
                context.args = command_parts[1:]
                await handler(update, context)
                return

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
