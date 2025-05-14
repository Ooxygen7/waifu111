from telegram import Update

from bot_core.public_functions.error import BotError, DatabaseError
from bot_core.public_functions.logging import logger
from utils import db_utils as db


def update_info_get(update: Update) -> dict:
    """从Telegram的Update对象中提取并整合有用的信息。
    Args:
        update (Update): Telegram的Update对象。
    Returns:
        dict: 包含用户、消息、群组等信息的字典。
    Raises:
        BotError: 解析Update信息时发生错误。
    """
    try:
        if update.message:
            return _process_message(update.message)
        elif update.callback_query:
            return _process_callback_query(update.callback_query)
    except Exception as e:
        logger.error(f"解析update信息错误: {str(e)}")
        raise BotError(f"解析update信息错误: {str(e)}")


def _process_message(message) -> dict:
    """处理Telegram消息对象，提取并整合信息。
    Args:
        message (Message): Telegram的消息对象。
    Returns:
        dict: 包含用户、消息、群组等信息的字典。
    """
    user_info = _extract_user_info(message.from_user)
    msg_info = _extract_message_info(message)
    group_info = _extract_group_info(message.chat)
    info = {**user_info, **msg_info, **group_info}

    if message.chat.type == 'private':
        config = _user_config_get(user_info['user_id'], info) or {}
        user_detail = db.user_info_get(user_info['user_id']) or {}
        return {**config, **user_detail, **info}
    else:  # group or supergroup
        config = db.group_config_get(group_info['group_id'])
        if config:
            config_dict = {'api': config[0], 'char': config[1], 'preset': config[2]}
            conv_id = {'conv_id': db.conversation_group_get(group_info['group_id'], user_info['user_id'])}
            if db.group_check_update(group_info['group_id']):
                return {'need_update': True, **user_info, **conv_id, **config_dict, **info}
            else:
                return {'need_update': False, **user_info, **conv_id, **config_dict, **info}
        else:
            return {'need_update': True, **info}


def _process_callback_query(callback_query) -> dict:
    """处理Telegram回调查询对象，提取并整合信息。
    Args:
        callback_query (CallbackQuery): Telegram的回调查询对象。
    Returns:
        dict: 包含用户、消息、群组等信息的字典。
    """

    user_info = _extract_user_info(callback_query.from_user)
    message = callback_query.message if callback_query.message else None
    msg_info = _extract_message_info(message) if message else {}

    if message and message.chat.type == 'private':
        info = {**user_info, **msg_info, 'user_name': f"{user_info['first_name']}{user_info['last_name']}"}
        config = _user_config_get(user_info['user_id']) or {}
        user_detail = db.user_info_get(user_info['user_id']) or {}
        return {**config, **user_detail, **info, **{'chat_type': callback_query.message.chat.type}}
    elif message and message.chat.type in ['group', 'supergroup']:
        group_info = _extract_group_info(message.chat)
        info = {**user_info, **msg_info, **group_info}
        config = db.group_config_get(group_info['group_id'])
        if config:
            config_dict = {'api': config[0], 'char': config[1], 'preset': config[2]}
            conv_id = {'conv_id': db.conversation_group_get(group_info['group_id'], user_info['user_id'])}
            return {**conv_id, **config_dict, **info, **{'chat_type': callback_query.message.chat.type}}
        else:
            return {'need_update': True, **info}
    else:
        # 无消息或其他聊天类型
        config = _user_config_get(user_info['user_id']) or {}
        user_detail = db.user_info_get(user_info['user_id']) or {}
        return {**user_detail, **config, **{'chat_type': callback_query.message.chat.type}}  # 可以根据需要添加 user_info


def _user_config_get(user_id: int, info=None) -> dict:
    if info is None:
        info = {}
    try:
        result = db.user_config_get(user_id)
        if not result:
            db.user_config_create(user_id)
            db.user_config_arg_update(user_id, 'nick', info['user_name'])
            result = db.user_config_get(user_id)
            logger.info(f"为新用户{user_id}创建默认配置")
        return result
    except Exception as e:
        logger.error(f"获取用户配置失败, user_id: {user_id}, 错误: {str(e)}")
        raise DatabaseError(f"获取用户配置失败: {str(e)}")


def _extract_user_info(user) -> dict:
    """从Telegram User对象中提取用户信息。

    Args:
        user: Telegram User对象。

    Returns:
        dict: 包含用户ID、名字、姓氏、用户名和完整用户名的字典。
    """
    return {
        'user_id': user.id,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'username': user.username or '',
        'user_name': (str(user.first_name or '') + str(user.last_name or '')).strip()
    }


def _extract_message_info(message) -> dict:
    """从Telegram Message对象中提取消息信息。

    Args:
        message: Telegram Message对象。

    Returns:
        dict: 包含消息ID和消息文本的字典。
    """
    return {
        'message_id': message.message_id or '',
        'message_text': message.text or ''
    }


def _extract_group_info(chat) -> dict:
    """从Telegram Chat对象中提取群组或私聊信息。

    Args:
        chat: Telegram Chat对象。

    Returns:
        dict: 包含聊天ID（群组ID或用户ID）、群组名称和聊天类型的字典。
    """
    return {
        'user_id' if chat.type == 'private' else 'group_id': chat.id or '',
        'group_name': chat.title or '',
        'chat_type': chat.type or ''
    }
