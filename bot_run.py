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
    MessageHandler,
    filters,
)

import bot_core.message_handlers.group as group_handler
import bot_core.message_handlers.private as private_handler
from bot_core.callback_handlers.callback import create_callback_handler  # 修改导入路径
from bot_core.command_handlers.regist import CommandHandlers
from utils.config_utils import BOT_TOKEN
from bot_core.services.utils.error import BotError
from utils.logging_utils import setup_logging
from bot_core.services.utils.error import error_handler
from bot_core.services.trading.monitor_service import monitor_service

setup_logging()
logger = logging.getLogger(__name__)





def setup_handlers(app: Application) -> None:
    """
    设置命令处理器。

    Args:
        app (Application): Telegram Application 实例。
    """

    # 定义所有需要加载的命令模块

    # 消息处理器
    message_handlers = [
        MessageHandler(
            (filters.TEXT | filters.Document.ALL | filters.PHOTO | filters.Sticker.ALL)
            & filters.ChatType.PRIVATE,
            private_handler.private_msg_handler,
        ),
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.Document.ALL)
            & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            group_handler.group_msg_handler,
        ),
    ]


    # 创建并添加回调处理器
    callback_handler = create_callback_handler(["bot_core.callback_handlers"])
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

        # --- 关键优化：在启动时预加载所有命令处理器 ---
        CommandHandlers.initialize()
        logger.info("所有命令处理器已预加载。")

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
                    ["private", "group", "admin", "trading"]
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
        

        
        # 启动交易监控服务
        async def start_trading_monitor(app_instance: Application) -> None:
            """启动交易监控服务"""
            try:
                await monitor_service.start_monitoring()
                logger.info("交易监控服务已启动")
            except Exception as e:
                logger.error(f"启动交易监控服务失败: {e}")
        
        # 添加交易监控启动到post_init
        original_post_init = app.post_init
        async def combined_post_init(app_instance: Application) -> None:
            if original_post_init:
                await original_post_init(app_instance)
            await start_trading_monitor(app_instance)
        
        app.post_init = combined_post_init
        
        logger.info("机器人初始化完成，准备启动...")

        # 启动机器人并确保资源正确释放
        try:
            logger.info("开始轮询更新...")
            app.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"轮询过程中发生错误: {str(e)}", exc_info=True)
            raise
        finally:
            logger.info("正在关闭服务...")
            
            # 停止交易监控服务
            try:
                import asyncio
                asyncio.create_task(monitor_service.stop_monitoring())
                logger.info("交易监控服务已停止")
            except Exception as e:
                logger.error(f"停止交易监控服务失败: {e}")
            
            # 关闭数据库连接
            from utils.db_utils import close_all_connections
            close_all_connections()
            logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"机器人启动失败: {str(e)}", exc_info=True)
        raise BotError(f"机器人启动失败: {str(e)}")


if __name__ == "__main__":
    main()
