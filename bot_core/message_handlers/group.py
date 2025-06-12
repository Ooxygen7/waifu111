import datetime
import logging
import random
from typing import Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot_core.public_functions.conversation import GroupConv
from bot_core.public_functions.decorators import Decorators
from bot_core.public_functions.error import DatabaseError, BotError
from bot_core.public_functions.update_parse import update_info_get
from utils import db_utils as db
from utils.logging_utils import setup_logging
from . import features

setup_logging()
logger = logging.getLogger(__name__)


@Decorators.ensure_group_info_updated
@Decorators.check_message_expiration
async def group_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理群聊文本消息。

    Args:
        update (Update): Telegram 更新对象。
        context (ContextTypes.DEFAULT_TYPE): 上下文对象。

    Note:
        此函数已使用 @check_message_and_user 装饰器进行用户和消息有效性检查。
        如果消息过期或用户无效，装饰器会自动处理并返回。
    """
    try:
        # 检查是否在关键词添加模式
        keyword_action = context.user_data.get('keyword_action')
        if keyword_action == 'add':
            user_id = update.effective_user.id
            logger.info(f"用户正在添加关键词，用户ID: {user_id}，群组ID: {update.message.chat.id}")
            await features.group_keyword_add(update, context)
            return
            

        # 处理普通群聊消息
        await group_reply(update, context)
    except Exception as e:
        logger.error(
            f"处理群聊消息时出错: {str(e)}，用户ID: {update.effective_user.id}，群组ID: {update.message.chat.id}",
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
    message_id = info['message_id']
    message_text = info['message_text']
    group_name = info['group_name']
    user_id = info['user_id']
    user_name = info['user_name']

    current_time = str(datetime.datetime.now())
    try:
        if db.group_dialog_add(message_id, info['group_id']):
            field_list = ['group_id', 'group_name', 'create_at', 'msg_user', 'msg_user_name', 'msg_text']
            value_list = [info['group_id'], group_name, current_time, user_id, user_name, message_text]
            for field, value in zip(field_list, value_list):
                db.group_dialog_update(message_id, field, value, info['group_id'])
            return True
        return False
    except Exception as e:
        logger.error(f"添加群聊对话记录失败, group_id: {info['group_id']}, 错误: {str(e)}")
        raise DatabaseError(f"添加群聊对话记录失败: {str(e)}")


def _group_msg_need_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[str, bool]:
    """
    检查群聊消息是否需要回复。

    Args:
        update (Update): Telegram更新对象。
        context (ContextTypes.DEFAULT_TYPE): 上下文对象。

    Returns:
        Union[str, bool]: 触发类型或False。
    """
    message = update.message
    bot_username = context.bot.username
    info = update_info_get(update)
    message_text = update.message.text or update.message.caption or ""
    group_id = info['group_id']
    group_name = info['group_name']
    user_name = info['user_name']
    keyword_list = db.group_keyword_get(group_id)
    rate = db.group_rate_get(group_id) or 0.05
    try:
        if message.reply_to_message:
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
            logger.debug(f"roll:{_rd}&rate:{rate}")
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
