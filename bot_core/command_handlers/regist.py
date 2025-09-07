import importlib
import inspect
import os
import sys

from bot_core.command_handlers.base import BaseCommand
from bot_core.command_handlers.base import BotCommandData
from bot_core.services.plugin_service import PluginService, BasePlugin
from utils.logging_utils import setup_logging
import logging
setup_logging()
logger = logging.getLogger(__name__)
from telegram.ext import CommandHandler
from typing import Callable

class CommandHandlers:
    """
    命令处理器管理类，负责动态加载和管理Telegram Bot的命令处理器。
    支持传统命令处理器和插件系统。
    """
    _command_maps: dict[str, dict[str, Callable]] | None = None
    _plugin_service: PluginService | None = None

    @classmethod
    def initialize(cls):
        """
        扫描所有命令模块并按聊天类型构建命令映射表。
        同时初始化插件系统并加载所有插件。
        这个方法应该在机器人启动时被明确调用一次。
        """
        if cls._command_maps is not None:
            logger.info("命令映射表已初始化，跳过。")
            return

        logger.info("正在初始化命令映射表...")
        cls._command_maps = {"private": {}, "group": {}}
        
        # 初始化插件服务
        cls._plugin_service = PluginService()
        
        # 加载传统命令处理器
        cls._load_traditional_commands()
        
        # 加载插件
        cls._load_plugins()
    
    @classmethod
    def _load_traditional_commands(cls):
        """加载传统的命令处理器"""
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
                            command_type = instance.meta.command_type
                            if command_type == "admin":
                                command_type = "private"  # 管理员命令视为私聊命令
                            
                            if command_type in cls._command_maps:
                                cls._command_maps[command_type][instance.meta.trigger] = instance.handler
                                logger.debug(f"已加载传统命令: /{instance.meta.trigger} 到 {command_type} 映射")
                    except Exception as e:
                        logger.error(f"为 {name} 创建命令处理器失败: {e}", exc_info=True)
    
    @classmethod
    def _load_plugins(cls):
        """加载插件系统中的所有插件"""
        plugins_dir = os.path.join(os.getcwd(), "plugins")
        if not os.path.exists(plugins_dir):
            logger.warning(f"插件目录不存在: {plugins_dir}")
            return
        
        # 将插件目录添加到Python路径
        if plugins_dir not in sys.path:
            sys.path.insert(0, plugins_dir)
        
        try:
            # 扫描插件目录
            for filename in os.listdir(plugins_dir):
                if filename.endswith("_plugin.py") and not filename.startswith("__"):
                    plugin_name = filename[:-3]  # 移除.py扩展名
                    try:
                        # 动态导入插件模块
                        plugin_module = importlib.import_module(plugin_name)
                        
                        # 查找插件类
                        for name, obj in inspect.getmembers(plugin_module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, BasePlugin) and 
                                obj != BasePlugin and
                                name.endswith("Plugin")):
                                
                                # 创建插件实例并注册
                                plugin_instance = obj()
                                cls._plugin_service.register_plugin(plugin_instance)
                                
                                # 将插件处理器添加到命令映射
                                command_type = plugin_instance.meta.command_type
                                if command_type == "admin":
                                    command_type = "private"
                                
                                if command_type in cls._command_maps:
                                    cls._command_maps[command_type][plugin_instance.meta.trigger] = plugin_instance.handle
                                    logger.info(f"已加载插件: /{plugin_instance.meta.trigger} ({plugin_instance.meta.name} v{plugin_instance.meta.version})")
                                break
                    except Exception as e:
                        logger.error(f"加载插件 {plugin_name} 失败: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"扫描插件目录失败: {e}", exc_info=True)

    @classmethod
    def get_command_handler(cls, command: str, chat_type: str) -> Callable | None:
        """
        根据命令触发词和聊天类型获取对应的处理器。
        假定 initialize() 已经在启动时被调用。

        Args:
            command (str): 命令触发词 (不带 /).
            chat_type (str): 聊天类型 ('private' 或 'group').

        Returns:
            Callable | None: 对应的命令处理器或 None。
        """
        if cls._command_maps is None:
            logger.error("命令映射表尚未初始化！请在机器人启动时调用 CommandHandlers.initialize()")
            return None
        
        if chat_type in cls._command_maps:
            return cls._command_maps[chat_type].get(command)
        
        return None
    
    @classmethod
    def get_plugin_service(cls) -> PluginService | None:
        """
        获取插件服务实例。
        
        Returns:
            PluginService | None: 插件服务实例或 None（如果未初始化）。
        """
        return cls._plugin_service

    @classmethod
    def get_command_definitions(
            cls,
            module_names: list[str],
    ) -> dict[str, list[BotCommandData]]:
        """
        动态扫描指定模块和插件，提取所有BaseCommand的子类和插件，并根据其meta属性，生成命令字典。
        Args:
            module_names (list): 模块名称列表.
        Returns:
            dict: 包含命令信息的字典，格式为 {'private': [BotCommand, ...], 'group': [BotCommand, ...]}
        """
        command_definitions: dict[str, list[BotCommandData]] = {
            "private": [],
            "group": [],
        }
        
        # 加载传统命令
        for module_name in module_names:
            try:
                module = importlib.import_module(
                    f"bot_core.command_handlers.{module_name}"
                )
            except ImportError as e:
                logger.error(
                    f"Error importing module {module_name}: {e}", exc_info=True
                )
                continue

            for name, obj in inspect.getmembers(module):
                if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseCommand)
                        and obj != BaseCommand
                ):
                    try:
                        instance = obj()
                        if hasattr(instance, "meta"):
                            if (
                                    instance.meta.enabled and instance.meta.show_in_menu
                            ):
                                command_type = instance.meta.command_type
                                if command_type == "admin":
                                    command_type = "private"
                                if command_type in command_definitions:
                                    command_definitions[command_type].append(
                                        BotCommandData(
                                            instance.meta.trigger,
                                            instance.meta.menu_text,
                                        )
                                    )
                                else:
                                    logger.warning(
                                        f"Unknown command type: {command_type} for command {instance.meta.trigger}"
                                    )
                    except Exception as e:
                        logger.error(
                            f"Error processing command {name}: {e}", exc_info=True
                        )
                        continue
        
        # 加载插件命令
        if cls._plugin_service:
            for plugin in cls._plugin_service.get_all_plugins():
                if plugin.meta.show_in_menu:
                    command_type = plugin.meta.command_type
                    if command_type == "admin":
                        command_type = "private"
                    if command_type in command_definitions:
                        command_definitions[command_type].append(
                            BotCommandData(
                                plugin.meta.trigger,
                                plugin.meta.menu_text,
                            )
                        )
        
        # 排序命令列表（按menu_weight排序）
        for command_type in command_definitions:
            command_definitions[command_type] = sorted(
                command_definitions[command_type],
                key=lambda cmd: cls._get_command_weight(cmd.command, command_type),
            )
        return command_definitions
    
    @classmethod
    def _get_command_weight(cls, trigger: str, command_type: str) -> int:
        """获取命令的权重，用于排序"""
        # 首先检查插件
        if cls._plugin_service:
            plugin = cls._plugin_service.get_plugin(trigger)
            if plugin:
                return plugin.meta.menu_weight
        
        # 然后检查传统命令
        try:
            module = importlib.import_module(f"bot_core.command_handlers.{command_type}")
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseCommand) and 
                    obj != BaseCommand):
                    try:
                        instance = obj()
                        if hasattr(instance, "meta") and instance.meta.trigger == trigger:
                            return instance.meta.menu_weight
                    except:
                        continue
        except:
            pass
        
        return 0  # 默认权重
