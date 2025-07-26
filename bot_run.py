import logging
import os
import subprocess
import sys
import threading
from telegram import BotCommand as TelegramBotCommand
from telegram import BotCommandScopeAllGroupChats, BotCommandScopeDefault, Update
from telegram.ext import (  # InlineQueryHandler,  # 注释掉内联相关
    Application,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import bot_core.message_handlers.group as group_handler
import bot_core.message_handlers.private as private_handler
from bot_core.callback_handlers.callback import create_callback_handler  # 修改导入路径
from bot_core.command_handlers.regist import CommandHandlers
# from bot_core.inline_handlers.inline import InlineQueryHandlers  # 注释掉内联相关
from bot_core.public_functions.config import BOT_TOKEN
from bot_core.public_functions.error import BotError
from utils.logging_utils import setup_logging
from bot_core.public_functions.error import error_handler
setup_logging()
logger = logging.getLogger(__name__)





def setup_handlers(app: Application) -> None:
    """
    设置命令处理器。

    Args:
        app (Application): Telegram Application 实例。
    """

    # 定义所有需要加载的命令模块

    # 获取所有命令处理器
    private_handlers = CommandHandlers.get_command_handlers(
        ["private"], tg_filters=filters.ChatType.PRIVATE
    )
    admin_handlers = CommandHandlers.get_command_handlers(
        ["admin"], tg_filters=filters.ChatType.PRIVATE
    )
    group_handlers = CommandHandlers.get_command_handlers(
        ["group"], tg_filters=filters.ChatType.GROUP | filters.ChatType.SUPERGROUP
    )
    command_handlers = private_handlers + admin_handlers + group_handlers

    # 消息处理器
    message_handlers = [
        MessageHandler(
            (filters.TEXT | filters.Document.ALL | filters.PHOTO | filters.Sticker.ALL)
            & ~filters.COMMAND
            & filters.ChatType.PRIVATE,
            private_handler.private_msg_handler,
        ),
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.Document.ALL)
            & ~filters.COMMAND
            & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            group_handler.group_msg_handler,
        ),
    ]

    # 注册所有命令处理器
    for handler in command_handlers:
        app.add_handler(handler)

    # 创建并添加回调处理器
    callback_handler = create_callback_handler(["bot_core.callback_handlers"])
    app.add_handler(CallbackQueryHandler(callback_handler.handle_callback_query))

    # 创建并添加内联查询处理器
    # try:
    #     inline_query_handler = InlineQueryHandler(InlineQueryHandlers.handle_inline_query)
    #     app.add_handler(inline_query_handler)
    #     logger.info("内联查询处理器已注册")
    # except Exception as e:
    #     logger.error(f"注册内联查询处理器失败: {e}", exc_info=True)
    #     # 不中断启动过程，只记录错误

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
        web_dir = os.path.join(current_dir, "web")
        app_py_path = os.path.join(web_dir, "app.py")

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
                command_menus = CommandHandlers.get_command_definitions(
                    ["private", "group", "admin"]
                )

                # 设置私聊命令菜单
                private_commands = [
                    TelegramBotCommand(cmd.command, cmd.description)
                    for cmd in command_menus["private"]
                ]  # 关键改动，使用TelegramBotCommand
                await app_instance.bot.set_my_commands(  # type: ignore
                    private_commands, scope=BotCommandScopeDefault()
                )
                logger.info("私聊命令菜单已设置完成")

                # 设置群组命令菜单
                group_commands = [
                    TelegramBotCommand(cmd.command, cmd.description)
                    for cmd in command_menus["group"]
                ]  # 关键改动，使用TelegramBotCommand
                await app_instance.bot.set_my_commands(  # type: ignore
                    group_commands, scope=BotCommandScopeAllGroupChats()
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
