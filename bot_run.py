import importlib
import inspect
import logging
import threading
import subprocess
import sys
import os

import telegram
from telegram import Update, BotCommand as TelegramBotCommand, BotCommandScopeDefault, BotCommandScopeAllGroupChats
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import bot_core.message_handlers.group as group_handler
import bot_core.message_handlers.private as private_handler
from bot_core.callback_handlers.callback import create_callback_handler  # 修改导入路径
from bot_core.command_handlers.base import BaseCommand, BotCommandData
from bot_core.public_functions.config import BOT_TOKEN
from bot_core.public_functions.error import BotError, ConfigError
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


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
            logger.error(f"Telegram API错误: {str(error)}，用户ID: {user_id}，聊天ID: {chat_id}", exc_info=True)
            error_message = "发送消息时发生错误，请稍后重试。"
        elif isinstance(error, BotError):
            logger.error(f"Bot运行错误: {str(error)}，用户ID: {user_id}，聊天ID: {chat_id}", exc_info=True)
            error_message = "Bot运行出现错误，请稍后重试。"
        elif isinstance(error, ConfigError):
            logger.error(f"配置错误: {str(error)}，用户ID: {user_id}，聊天ID: {chat_id}", exc_info=True)
            error_message = "Bot配置出现错误，请联系管理员。"
        else:
            logger.error(f"未处理的错误: {str(error)}，用户ID: {user_id}，聊天ID: {chat_id}", exc_info=True)
            error_message = "发生未知错误，请稍后重试。"

        # 仅在有效的消息上下文中发送错误提示
        if update and update.message and not context.user_data.get('error_notified'):
            await update.message.reply_text(error_message, parse_mode=None)
            context.user_data['error_notified'] = True  # 标记已发送错误消息
    except Exception as e:
        # 确保错误处理器本身的错误不会导致程序崩溃
        logger.critical(f"错误处理器发生错误: {str(e)}，原始错误: {str(error)}", exc_info=True)


class CommandHandlers:

    @staticmethod
    def get_command_handlers(module_names, tg_filters=None):
        """
        动态扫描指定模块，提取所有BaseCommand的子类，并生成对应的CommandHandler实例。

        Args:
            module_names (list): 模块名称列表.
            tg_filters: (telegram.ext.filters, optional): CommandHandler的过滤器。默认为None。

        Returns:
            list: CommandHandler实例列表。
        """
        command_handlers = []
        for module_name in module_names:
            try:
                module = importlib.import_module(f'bot_core.command_handlers.{module_name}')  # 动态导入模块
            except ImportError as e:
                logger.error(f"Error importing module {module_name}: {e}", exc_info=True)  # 打印导入错误，方便调试
                continue

            for name, obj in inspect.getmembers(module):  # 扫描模块中的所有成员
                if inspect.isclass(obj) and issubclass(obj, BaseCommand) and obj != BaseCommand:  # 检查是否是BaseCommand的子类
                    try:
                        instance = obj()  # 创建命令类实例
                        if hasattr(instance, 'meta') and hasattr(instance.meta, 'trigger'):  # 确保有meta和trigger属性
                            if instance.meta.enabled:  # 确保已激活
                                logger.debug(
                                    f"{name}命令已加载,启用:{instance.meta.enabled},展示在目录:{instance.meta.show_in_menu}")
                                handler = CommandHandler(instance.meta.trigger, instance.handler,
                                                         filters=tg_filters)  # 使用预处理过的handler
                                command_handlers.append(handler)
                    except Exception as e:
                        logger.error(f"Error creating CommandHandler for {name}: {e}",
                                     exc_info=True)  # 打印创建实例或CommandHandler错误，方便调试
                        continue

        return command_handlers

    @staticmethod
    def get_command_definitions(module_names: list[str]) -> dict[str, list[BotCommandData]]:  # 类型提示BotCommandData
        """
        动态扫描指定模块，提取所有BaseCommand的子类，并根据其meta属性，生成命令字典。
        Args:
            module_names (list): 模块名称列表.
        Returns:
            dict: 包含命令信息的字典，格式为 {'private': [BotCommand, ...], 'group': [BotCommand, ...]}
        """
        command_definitions: dict[str, list[BotCommandData]] = {  # 类型提示BotCommandData
            'private': [],
            'group': []
        }
        for module_name in module_names:
            try:
                module = importlib.import_module(f'bot_core.command_handlers.{module_name}')  # 动态导入模块
            except ImportError as e:
                logger.error(f"Error importing module {module_name}: {e}", exc_info=True)  # 打印导入错误，方便调试
                continue
            for name, obj in inspect.getmembers(module):  # 扫描模块中的所有成员

                if inspect.isclass(obj) and issubclass(obj, BaseCommand) and obj != BaseCommand:  # 检查是否是BaseCommand的子类
                    try:

                        instance = obj()  # 创建命令类实例
                        if hasattr(instance, 'meta'):  # 确保有meta属性
                            if instance.meta.enabled and instance.meta.show_in_menu:  # 确保已激活和显示在菜单中

                                command_type = instance.meta.command_type
                                if command_type == 'admin':
                                    command_type = 'private'  # 将admin命令归类到private
                                if command_type in command_definitions:
                                    command_definitions[command_type].append(
                                        BotCommandData(instance.meta.trigger, instance.meta.menu_text)
                                        # 使用BotCommandData
                                    )

                                else:
                                    print(f"Unknown command type: {command_type} for command {instance.meta.trigger}")
                    except Exception as e:
                        logger.error(f"Error processing command {name}: {e}",
                                     exc_info=True)  # 打印创建实例或CommandHandler错误，方便调试
                        continue
        # 排序命令列表
        for command_type in command_definitions:
            command_definitions[command_type] = sorted(
                command_definitions[command_type],
                key=lambda cmd: next((getattr(cls, 'meta').menu_weight for cmd_name, cls in inspect.getmembers(
                    importlib.import_module(f'bot_core.command_handlers.{command_type}')) if
                                      inspect.isclass(cls) and issubclass(cls,
                                                                          BaseCommand) and cls != BaseCommand and getattr(
                                          cls, 'meta').trigger == cmd.command), 0)
            )
        return command_definitions


def setup_handlers(app: Application) -> None:
    """
    设置命令处理器。

    Args:
        app (Application): Telegram Application 实例。
    """

    # 定义所有需要加载的命令模块

    # 获取所有命令处理器
    private_handlers = CommandHandlers.get_command_handlers(['private'], tg_filters=filters.ChatType.PRIVATE)
    admin_handlers = CommandHandlers.get_command_handlers(['admin'], tg_filters=filters.ChatType.PRIVATE)
    group_handlers = CommandHandlers.get_command_handlers(['group'],
                                                          tg_filters=filters.ChatType.GROUP | filters.ChatType.SUPERGROUP)
    command_handlers = private_handlers + admin_handlers + group_handlers

    # 消息处理器
    message_handlers = [
        MessageHandler(
            (filters.TEXT | filters.Document.ALL | filters.PHOTO | filters.Sticker.ALL) & ~filters.COMMAND & filters.ChatType.PRIVATE,
            private_handler.private_msg_handler
        ),
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND & (
                    filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            group_handler.group_msg_handler
        ),
    ]

    # 注册所有命令处理器
    for handler in command_handlers:
        app.add_handler(handler)

    # 创建并添加回调处理器
    callback_handler = create_callback_handler(['bot_core.callback_handlers'])
    app.add_handler(CallbackQueryHandler(callback_handler.handle_callback_query))

    # 添加消息处理器
    for handler in message_handlers:
        app.add_handler(handler)


def start_web_app():
    """
    启动Web管理界面
    """
    try:
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        web_dir = os.path.join(current_dir, 'web')
        app_py_path = os.path.join(web_dir, 'app.py')
        
        logger.info("正在启动Web管理界面...")
        
        # 启动web应用
        subprocess.run([sys.executable, app_py_path], cwd=web_dir)
    except Exception as e:
        logger.error(f"启动Web管理界面失败: {str(e)}", exc_info=True)

def main() -> None:
    """
    主函数，初始化并启动Telegram Bot和Web管理界面。

    Note:
        1. 初始化应用实例
        2. 设置命令菜单
        3. 注册消息处理器
        4. 启动Web管理界面（后台线程）
        5. 启动Bot轮询
        6. 确保资源正确释放
    """
    try:
        # 启动Web管理界面（在后台线程中运行）
        web_thread = threading.Thread(target=start_web_app, daemon=True)
        web_thread.start()
        logger.info("Web管理界面已在后台启动")
        
        # 创建 Application 实例
        app = Application.builder().token(BOT_TOKEN).build()

        async def setup_command_menu(app_instance: Application) -> None:
            """
            设置Bot的命令菜单。

            Args:
                app_instance (Application): Telegram Application 实例。

            Raises:
                BotRunError: 设置命令菜单失败时抛出。
            """
            try:
                command_menus = CommandHandlers.get_command_definitions(['private', 'group', 'admin'])

                # 设置私聊命令菜单
                private_commands = [TelegramBotCommand(cmd.command, cmd.description) for cmd in
                                    command_menus['private']]  # 关键改动，使用TelegramBotCommand
                await app_instance.bot.set_my_commands( # type: ignore
                    private_commands,
                    scope=BotCommandScopeDefault()
                )
                logger.info("私聊命令菜单已设置完成")

                # 设置群组命令菜单
                group_commands = [TelegramBotCommand(cmd.command, cmd.description) for cmd in
                                  command_menus['group']]  # 关键改动，使用TelegramBotCommand
                await app_instance.bot.set_my_commands( # type: ignore
                    group_commands,
                    scope=BotCommandScopeAllGroupChats()
                )
                logger.info("群组命令菜单已设置完成")
            except Exception as error:
                error_msg = f"设置命令菜单失败: {str(error)}"
                logger.error(error_msg, exc_info=True)
                raise BotError(error_msg)

        # 设置初始化函数
        app.post_init = setup_command_menu

        # 设置命令处理器
        setup_handlers(app)

        # 添加错误处理器
        app.add_error_handler(error_handler)
        logger.info("机器人初始化完成，准备启动...")

        # 启动机器人并确保资源正确释放
        try:
            logger.info("开始轮询更新...")
            app.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"轮询过程中发生错误: {str(e)}", exc_info=True)
            raise
        finally:
            logger.info("正在关闭数据库连接...")
            from utils.db_utils import close_all_connections
            close_all_connections()
            logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"机器人启动失败: {str(e)}", exc_info=True)
        raise BotError(f"机器人启动失败: {str(e)}")


if __name__ == "__main__":
    main()
