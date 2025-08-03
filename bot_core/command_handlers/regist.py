import importlib
import inspect

from bot_core.command_handlers.base import BaseCommand
from bot_core.command_handlers.base import BotCommandData
from utils.logging_utils import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__)
from telegram.ext import CommandHandler
from typing import Callable

class CommandHandlers:
    """
    命令处理器管理类，负责动态加载和管理Telegram Bot的命令处理器。
    """
    _command_map: dict[str, Callable] | None = None

    @classmethod
    def _initialize(cls):
        """
        扫描所有命令模块并构建命令映射表。
        """
        if cls._command_map is not None:
            return

        cls._command_map = {}
        module_names = ["private", "group", "admin"]
        for module_name in module_names:
            try:
                module = importlib.import_module(f"bot_core.command_handlers.{module_name}")
            except ImportError as e:
                logger.error(f"导入模块 {module_name} 失败: {e}", exc_info=True)
                continue

            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseCommand) and obj != BaseCommand:
                    try:
                        instance = obj()
                        if hasattr(instance, "meta") and instance.meta.enabled:
                            if cls._command_map is not None:
                                cls._command_map[instance.meta.trigger] = instance.handler
                                logger.debug(f"已加载命令: /{instance.meta.trigger}")
                    except Exception as e:
                        logger.error(f"为 {name} 创建命令处理器失败: {e}", exc_info=True)

    @classmethod
    def get_command_handler(cls, command: str) -> Callable | None:
        """
        根据命令触发词获取对应的处理器。

        Args:
            command (str): 命令触发词 (不带 /).

        Returns:
            Callable | None: 对应的命令处理器或 None。
        """
        if cls._command_map is None:
            cls._initialize()
        if cls._command_map is not None:
            return cls._command_map.get(command)
        return None

    @staticmethod
    def get_command_definitions(
            module_names: list[str],
    ) -> dict[str, list[BotCommandData]]:  # 类型提示BotCommandData
        """
        动态扫描指定模块，提取所有BaseCommand的子类，并根据其meta属性，生成命令字典。
        Args:
            module_names (list): 模块名称列表.
        Returns:
            dict: 包含命令信息的字典，格式为 {'private': [BotCommand, ...], 'group': [BotCommand, ...]}
        """
        command_definitions: dict[str, list[BotCommandData]] = {
            "private": [],
            "group": [],
        }  # 类型提示BotCommandData
        for module_name in module_names:
            try:
                module = importlib.import_module(
                    f"bot_core.command_handlers.{module_name}"
                )  # 动态导入模块
            except ImportError as e:
                logger.error(
                    f"Error importing module {module_name}: {e}", exc_info=True
                )  # 打印导入错误，方便调试
                continue

            for name, obj in inspect.getmembers(module):  # 扫描模块中的所有成员

                if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseCommand)
                        and obj != BaseCommand
                ):  # 检查是否是BaseCommand的子类
                    try:

                        instance = obj()  # 创建命令类实例
                        if hasattr(instance, "meta"):  # 确保有meta属性
                            if (
                                    instance.meta.enabled and instance.meta.show_in_menu
                            ):  # 确保已激活和显示在菜单中

                                command_type = instance.meta.command_type
                                if command_type == "admin":
                                    command_type = "private"  # 将admin命令归类到private
                                if command_type in command_definitions:
                                    command_definitions[command_type].append(
                                        BotCommandData(
                                            instance.meta.trigger,
                                            instance.meta.menu_text,
                                        )
                                        # 使用BotCommandData
                                    )

                                else:
                                    print(
                                        f"Unknown command type: {command_type} for command {instance.meta.trigger}"
                                    )
                    except Exception as e:
                        logger.error(
                            f"Error processing command {name}: {e}", exc_info=True
                        )  # 打印创建实例或CommandHandler错误，方便调试
                        continue
        # 排序命令列表
        for command_type in command_definitions:
            command_definitions[command_type] = sorted(
                command_definitions[command_type],
                key=lambda cmd: next(
                    (
                        getattr(cls, "meta").menu_weight
                        for cmd_name, cls in inspect.getmembers(
                        importlib.import_module(
                            f"bot_core.command_handlers.{command_type}"
                        )
                    )
                        if inspect.isclass(cls)
                           and issubclass(cls, BaseCommand)
                           and cls != BaseCommand
                           and getattr(cls, "meta").trigger == cmd.command
                    ),
                    0,
                ),
            )
        return command_definitions
