import datetime
import functools

from telegram import Update
from telegram.ext import ContextTypes

from bot_core.public_functions.config import DEFAULT_CHAR, DEFAULT_PRESET, DEFAULT_API, ADMIN
from bot_core.public_functions.error import BotError, DatabaseError
from bot_core.public_functions.update_parse import update_info_get
from utils import db_utils as db

import logging
from utils.logging_utils import setup_logging
setup_logging()
logger = logging.getLogger(__name__)


class Decorators:
    @staticmethod
    def handle_command_errors(func):
        """Decorator to handle common errors in command handlers."""

        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            command_name = func.__name__
            try:
                return await func(update, context, *args, **kwargs)
            except Exception as e:
                logger.error(f"处理 {command_name} 命令时出错: {str(e)}", exc_info=True)
                # Optionally, send a generic error message to the user here
                # await update.message.reply_text("处理命令时发生错误，请稍后重试。")
                # Re-raising BotRunError might be handled by a global error handler
                raise BotError(f"处理 {command_name} 命令失败: {str(e)}")

        return wrapper

    @staticmethod
    def group_admin_required(func):
        """Decorator: Only allow group admins to execute the command, otherwise reply with a prompt."""

        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            info = update_info_get(update)
            admin_list = db.group_admin_list_get(info['group_id'])

            if not ((info['user_id'] in admin_list) or (info['user_id'] in ADMIN)):
                # Check if it's a message or a callback query
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text("仅管理员可操作此命令。")
                elif hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.answer("仅管理员可操作。", show_alert=True)
                return
            return await func(update, context, *args, **kwargs)

        return wrapper

    @staticmethod
    def user_admin_required(func):
        """Decorator: Only allow users who are admins (via public.user_admin_check) to execute the command."""

        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            info = update_info_get(update)  # 获取用户信息，假设这个函数可用
            if not info['user_id'] in ADMIN:
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text("无权限操作，仅管理员可用。")
                # 如果是其他类型（如回调查询），可以扩展逻辑
                return  # 停止执行
            return await func(update, context, *args, **kwargs)

        return wrapper

    @staticmethod
    def ensure_group_info_updated(func):
        """Decorator to ensure group info is updated or created before executing the function."""

        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            group_id = update.message.chat.id  # 假设更新来自消息
            group_name = update.message.chat.title
            current_time = str(datetime.datetime.now())

            try:
                if db.group_check_update(group_id):
                    logger.info(f"更新群组信息, group_name: {group_name}, time: {current_time}")
                    admins = await context.bot.get_chat_administrators(group_id)
                    admin_list = [admin.user.id for admin in admins]
                    config = db.group_config_get(group_id)
                    if config:
                        api, char, preset = config[0], config[1], config[2]
                    else:
                        db.group_info_create(group_id)
                        api, char, preset = DEFAULT_API, DEFAULT_CHAR, DEFAULT_PRESET  # 假设这些常量已定义
                    field_list = ['group_name', 'update_time', 'members_list', 'api', 'char', 'preset']
                    value_list = [group_name, current_time, str(admin_list), api, char, preset]
                    for field, value in zip(field_list, value_list):
                        db.group_info_update(group_id, field, value)
                    # 更新成功，继续执行原函数
                await func(update, context, *args, **kwargs)
            except Exception as e:
                logger.error(f"更新或创建群组信息失败, group_id: {group_id}, 错误: {str(e)}")
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text(f"群组信息更新失败: {str(e)}")
                raise DatabaseError(f"更新或创建群组信息失败: {str(e)}")

        return wrapper

    @staticmethod
    def check_message_expiration(func):
        """
        装饰器，用于检查消息是否过期。
        如果消息超过 30 秒，则记录日志并停止处理。
        参数:
        func (Callable): 要装饰的函数，通常是处理更新的函数。
        返回:
        Callable: 一个包装函数，如果消息不过期则调用原函数，否则返回 None。
        """

        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            # 确保 update.message 和 update.message.text 存在
            command_name = '消息'
            if update.message and update.message.text and update.message.text.startswith('/'):
                command_name = update.message.text.split()[0]
            if datetime.datetime.now(update.message.date.tzinfo) - update.message.date > datetime.timedelta(seconds=30):
                logger.warning(f"忽略过期的{command_name}，消息ID: {update.message.message_id}")
                return None  # 停止处理如果消息过期
            # 如果不过期，继续调用原函数
            return await func(update, context, *args, **kwargs)

        return wrapper

    @staticmethod
    def ensure_user_info_updated(func):
        """
        装饰器，用于确保用户信息的更新，同时在内部调用 check_message_expiration 装饰器。
        该装饰器首先检查消息是否过期（通过调用 check_message_expiration 的逻辑），
        如果不过期，则更新用户的信息并继续处理命令。
        参数:
        func (Callable): 要装饰的函数，通常是命令处理函数。
        返回:
        Callable: 一个包装函数，结合了消息过期检查和用户更新逻辑。
        """

        # 这里我们创建一个内部函数，并使用 check_message_expiration 装饰它
        # 这实现了在 ensure_user_info_updated 中"调用" check_message_expiration
        @Decorators.check_message_expiration  # 先应用 check_message_expiration 装饰器
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if update.message.chat.type == 'private':
                info = update_info_get(update)  # 假设这是获取用户信息的函数
                if db.user_config_check(info['user_id']):
                    db.user_info_update(info['user_id'], 'first_name', info['first_name'])
                    db.user_info_update(info['user_id'], 'last_name', info['last_name'])
                    db.user_info_update(info['user_id'], 'user_name', info['username'])
                    current_time = str(datetime.datetime.now())
                    db.user_info_update(info['user_id'], 'update_at', current_time)
                else:
                    db.user_info_create(info['user_id'], info['first_name'], info['last_name'], info['username'])
                # 记录命令处理开始，确保 text 属性存在
                command_name = '消息'
                if update.message and update.message.text and update.message.text.startswith('/'):
                    command_name = update.message.text.split()[0]
                logger.info(f"处理 {command_name} ，用户名称: {info['user_name']}")
            # 继续调用原始函数
            return await func(update, context, *args, **kwargs)

        return wrapper  # 返回最终的包装函数