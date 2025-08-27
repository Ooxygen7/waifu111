import logging
import random
from typing import Union

from telegram import Update
from telegram.ext import ContextTypes

from bot_core.services.conversation import GroupConv
from bot_core.services.utils.decorators import Decorators
from bot_core.services.utils.error import BotError
from bot_core.services.utils.tg_parse import update_info_get, parse_commands_with_and
from utils import db_utils as db
from . import features

logger = logging.getLogger(__name__)


from bot_core.command_handlers.regist import CommandHandlers

@Decorators.ensure_group_info_updated
@Decorators.check_message_expiration
async def group_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理群聊消息，包括命令和普通对话。
    """
    if not update.message or not update.message.from_user:
        return

    user_id = update.message.from_user.id
    message_text = update.message.text or ""

    # 检查是否为命令
    if message_text.startswith('/'):
        info = update_info_get(update)
        _group_dialog_add(info)

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
                    if bot_username != context.bot.username:
                        continue  # 不是发给我的命令，跳过

                handler = CommandHandlers.get_command_handler(command_name, "group")
                if handler:
                    logger.info(f"群组命令: /{command_name}, 群组ID: {update.message.chat.id}, 用户ID: {user_id}")
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
                if bot_username != context.bot.username:
                    return  # 不是发给我的命令，忽略

            handler = CommandHandlers.get_command_handler(command, "group")
            if handler:
                logger.info(f"群组命令: /{command}, 群组ID: {update.message.chat.id}, 用户ID: {user_id}")
                # 将命令参数填充到 context.args
                context.args = command_parts[1:]
                await handler(update, context)
                return

    try:
        # 检查是否在关键词添加模式
        if context.user_data:
            keyword_action = context.user_data.get('keyword_action')
            # 兼容旧的字符串格式和新的字典格式
            is_adding = False
            if isinstance(keyword_action, dict):
                if keyword_action.get(user_id) == 'add':
                    is_adding = True
            elif isinstance(keyword_action, str) and keyword_action == 'add':
                 # 这是不规范的旧格式，但为了兼容而处理
                is_adding = True

            if is_adding:
                logger.info(f"用户 {user_id} 正在添加关键词，在群组 {update.message.chat.id}")
                await features.group_keyword_add(update, context)
                return

        # 处理普通群聊消息
        await group_reply(update, context)
    except Exception as e:
        logger.error(
            f"处理群聊消息时出错: {str(e)}，用户ID: {user_id}，群组ID: {update.message.chat.id}",
            exc_info=True
        )


async def group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理群组消息。

    Args:
        update (Update): Telegram 更新对象。
        context (ContextTypes.DEFAULT_TYPE): 上下文对象。
    """
    info = update_info_get(update)
    # 添加消息到群消息记录
    _group_dialog_add(info)
    
    # 检查话题权限
    if not _check_topic_permission(update, context):
        return
    
    # 检查是否需要回复
    needs_reply = _group_msg_need_reply(update, context)
    if not needs_reply:
        return
    else:
        conversation = GroupConv(update, context)
        conversation.set_trigger(needs_reply)
        await conversation.response()


def _group_dialog_add(info) -> bool:
    """
    将一条用户消息的初始记录添加到 group_dialogs 表中。
    """
    try:
        return db.group_dialog_initial_add(
            group_id=info['group_id'],
            msg_user_id=info['user_id'],
            msg_user_name=info['user_name'],
            msg_text=info['message_text'],
            msg_id=info['message_id'],
            group_name=info['group_name']
        )
    except Exception as e:
        logger.error(f"添加群聊初始对话记录失败, group_id: {info.get('group_id')}, msg_id: {info.get('message_id')}, 错误: {str(e)}", exc_info=True)
        # 在这里不重新抛出异常，因为记录失败不应中断整个消息处理流程
        return False


def _group_msg_need_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, bool]:
    """
    检查群聊消息是否需要回复。

    Args:
        update (Update): Telegram更新对象。
        context (ContextTypes.DEFAULT_TYPE): 上下文对象。

    Returns:
        Union[str, bool]: 触发类型或False。
    """
    if not update.message:
        return False
    message = update.message
    bot_username = context.bot.username
    info = update_info_get(update)
    if not info:
        return False
    message_text = message.text or message.caption or ""
    group_id = info['group_id']
    group_name = info['group_name']
    user_name = info['user_name']
    keyword_list = db.group_keyword_get(group_id)
    rate = db.group_rate_get(group_id) or 0.05
    try:
        if message.reply_to_message and message.reply_to_message.from_user:
            if message.reply_to_message.from_user.id == context.bot.id:
                logger.info(f"触发回复Bot, group_name: {group_name}, user_name: {user_name}")
                return 'reply'
        if message_text:
            if f"@{bot_username}" in message_text:
                logger.info(f"触发@Bot, group_name: {group_name}, user_name: {user_name}")
                return '@'
            if keyword_list and any(keyword in message_text for keyword in keyword_list):
                logger.info(
                    f"触发关键词, group_name: {group_name}, user_name: {user_name}"
                )
                return 'keyword'
            _rd = random.random()
            #logger.debug(f"roll:{_rd}&rate:{rate}")
            if _rd < rate:
                logger.info(f"触发随机回复, group_name: {group_name}, user_name: {user_name}")
                return 'random'

        # logger.info(f"未触发任何条件, group_name: {group_name}, user_name: {user_name}")
        return False
    except Exception as e:
        logger.error(f"检查群聊消息是否需要回复失败, group_id: {group_id}, 错误: {str(e)}")
        raise BotError(f"检查群聊消息是否需要回复失败: {str(e)}")


def _check_topic_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    检查Bot是否有权限在当前话题中发言。
    
    Args:
        update (Update): Telegram更新对象。
        context (ContextTypes.DEFAULT_TYPE): 上下文对象。
    
    Returns:
        bool: 是否允许发言。
    """
    if not update.message:
        return False
    try:
        message = update.message
        group_id = message.chat.id
        
        # 获取禁用的话题列表
        disabled_topics = db.group_disabled_topics_get(group_id)
        
        # 检查是否在话题中
        if hasattr(message, 'message_thread_id') and message.message_thread_id:
            topic_id = str(message.message_thread_id)
            # 如果当前话题在禁用列表中，则不允许发言
            return topic_id not in disabled_topics
        else:
            # 不在话题中的消息，检查主群聊是否被禁用
            return "main" not in disabled_topics
            
    except Exception as e:
        logger.error(f"检查话题权限失败: {str(e)}")
        return True  # 出错时默认允许
