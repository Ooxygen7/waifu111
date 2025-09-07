import os
import sys
import importlib
import inspect
import logging
from typing import Dict, List, Optional, Any, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass
from telegram import Update
from telegram.ext import ContextTypes

from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@dataclass
class PluginMeta:
    """插件元数据类"""
    name: str
    version: str
    description: str
    author: str
    trigger: str  # 触发命令
    command_type: str = "group"  # 命令类型: group, private, both
    menu_text: str = ""
    show_in_menu: bool = True
    menu_weight: int = 0
    dependencies: List[str] = None  # 依赖的其他插件
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self):
        self.meta: PluginMeta = None
        self._initialized = False
    
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理命令的抽象方法"""
        pass
    
    async def initialize(self) -> bool:
        """插件初始化方法，可以被子类重写"""
        self._initialized = True
        return True
    
    async def cleanup(self) -> None:
        """插件清理方法，可以被子类重写"""
        pass
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_commands: Dict[str, str] = {}  # trigger -> plugin_name
        self._loaded_modules = set()
    
    def get_plugins_path(self) -> str:
        """获取插件目录的绝对路径"""
        return os.path.abspath(self.plugins_dir)
    
    async def load_plugins(self) -> None:
        """加载所有插件"""
        plugins_path = self.get_plugins_path()
        
        if not os.path.exists(plugins_path):
            logger.warning(f"插件目录不存在: {plugins_path}")
            return
        
        # 将插件目录添加到Python路径
        if plugins_path not in sys.path:
            sys.path.insert(0, plugins_path)
        
        # 扫描插件文件
        for filename in os.listdir(plugins_path):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                await self._load_plugin_module(module_name)
    
    async def _load_plugin_module(self, module_name: str) -> None:
        """加载单个插件模块"""
        try:
            if module_name in self._loaded_modules:
                logger.debug(f"插件模块 {module_name} 已经加载")
                return
            
            # 导入模块
            module = importlib.import_module(module_name)
            
            # 查找插件类
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BasePlugin) and 
                    obj != BasePlugin):
                    plugin_classes.append(obj)
            
            if not plugin_classes:
                logger.warning(f"模块 {module_name} 中未找到插件类")
                return
            
            # 实例化并注册插件
            for plugin_class in plugin_classes:
                await self._register_plugin_class(plugin_class, module_name)
            
            self._loaded_modules.add(module_name)
            logger.info(f"成功加载插件模块: {module_name}")
            
        except Exception as e:
            logger.error(f"加载插件模块 {module_name} 失败: {e}", exc_info=True)
    
    async def _register_plugin_class(self, plugin_class: Type[BasePlugin], module_name: str) -> None:
        """注册插件类"""
        try:
            # 实例化插件
            plugin_instance = plugin_class()
            
            # 检查插件元数据
            if not hasattr(plugin_instance, 'meta') or plugin_instance.meta is None:
                logger.error(f"插件 {plugin_class.__name__} 缺少元数据")
                return
            
            meta = plugin_instance.meta
            
            # 检查依赖
            if not await self._check_dependencies(meta.dependencies):
                logger.error(f"插件 {meta.name} 的依赖检查失败")
                return
            
            # 初始化插件
            if not await plugin_instance.initialize():
                logger.error(f"插件 {meta.name} 初始化失败")
                return
            
            # 注册插件
            self.plugins[meta.name] = plugin_instance
            self.plugin_commands[meta.trigger] = meta.name
            
            logger.info(f"成功注册插件: {meta.name} (/{meta.trigger})")
            
        except Exception as e:
            logger.error(f"注册插件类 {plugin_class.__name__} 失败: {e}", exc_info=True)
    
    async def _check_dependencies(self, dependencies: List[str]) -> bool:
        """检查插件依赖"""
        for dep in dependencies:
            if dep not in self.plugins:
                logger.error(f"缺少依赖插件: {dep}")
                return False
        return True
    
    async def execute_command(self, trigger: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """执行插件命令"""
        if trigger not in self.plugin_commands:
            return False
        
        plugin_name = self.plugin_commands[trigger]
        plugin = self.plugins.get(plugin_name)
        
        if not plugin:
            logger.error(f"插件 {plugin_name} 未找到")
            return False
        
        if not plugin.is_initialized:
            logger.error(f"插件 {plugin_name} 未初始化")
            return False
        
        try:
            await plugin.handle(update, context)
            return True
        except Exception as e:
            logger.error(f"执行插件 {plugin_name} 命令失败: {e}", exc_info=True)
            return False
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginMeta]:
        """获取插件信息"""
        plugin = self.plugins.get(plugin_name)
        return plugin.meta if plugin else None
    
    def list_plugins(self) -> List[PluginMeta]:
        """列出所有插件"""
        return [plugin.meta for plugin in self.plugins.values()]
    
    def get_commands(self) -> Dict[str, str]:
        """获取所有命令映射"""
        return self.plugin_commands.copy()
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        try:
            # 清理旧插件
            if plugin_name in self.plugins:
                old_plugin = self.plugins[plugin_name]
                await old_plugin.cleanup()
                
                # 移除命令映射
                trigger_to_remove = None
                for trigger, name in self.plugin_commands.items():
                    if name == plugin_name:
                        trigger_to_remove = trigger
                        break
                
                if trigger_to_remove:
                    del self.plugin_commands[trigger_to_remove]
                
                del self.plugins[plugin_name]
            
            # 重新加载模块
            module_name = plugin_name.lower()
            if module_name in self._loaded_modules:
                self._loaded_modules.remove(module_name)
            
            # 重新导入模块
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            
            await self._load_plugin_module(module_name)
            
            logger.info(f"成功重新加载插件: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"重新加载插件 {plugin_name} 失败: {e}", exc_info=True)
            return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"插件 {plugin_name} 未加载")
                return False
            
            plugin = self.plugins[plugin_name]
            await plugin.cleanup()
            
            # 移除命令映射
            trigger_to_remove = None
            for trigger, name in self.plugin_commands.items():
                if name == plugin_name:
                    trigger_to_remove = trigger
                    break
            
            if trigger_to_remove:
                del self.plugin_commands[trigger_to_remove]
            
            del self.plugins[plugin_name]
            
            logger.info(f"成功卸载插件: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"卸载插件 {plugin_name} 失败: {e}", exc_info=True)
            return False


# 全局插件管理器实例
plugin_manager = PluginManager()


class PluginService:
    """插件服务类，提供插件管理的统一接口"""
    
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self._loaded_modules = set()
    
    def register_plugin(self, plugin: BasePlugin) -> None:
        """注册插件"""
        if not hasattr(plugin, 'meta') or plugin.meta is None:
            logger.error(f"插件 {plugin.__class__.__name__} 缺少元数据")
            return
        
        self.plugins[plugin.meta.name] = plugin
        logger.info(f"插件 {plugin.meta.name} 注册成功")
    
    def get_plugin(self, trigger: str) -> Optional[BasePlugin]:
        """根据触发词获取插件"""
        for plugin in self.plugins.values():
            if plugin.meta.trigger == trigger:
                return plugin
        return None
    
    def get_plugin_by_name(self, name: str) -> Optional[BasePlugin]:
        """根据名称获取插件"""
        return self.plugins.get(name)
    
    def get_all_plugins(self) -> List[BasePlugin]:
        """获取所有插件"""
        return list(self.plugins.values())
    
    async def initialize(self) -> None:
        """初始化插件系统"""
        await plugin_manager.load_plugins()
    
    async def execute_command(self, trigger: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """执行插件命令"""
        plugin = self.get_plugin(trigger)
        if plugin:
            try:
                await plugin.handle(update, context)
                return True
            except Exception as e:
                logger.error(f"执行插件命令 {trigger} 失败: {e}", exc_info=True)
                return False
        return False
    
    def get_plugin_commands(self) -> Dict[str, str]:
        """获取所有插件命令"""
        commands = {}
        for plugin in self.plugins.values():
            commands[plugin.meta.trigger] = plugin.meta.description
        return commands
    
    def list_plugins(self) -> List[PluginMeta]:
        """列出所有插件"""
        return [plugin.meta for plugin in self.plugins.values()]
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        return await plugin_manager.reload_plugin(plugin_name)
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            await plugin.cleanup()
            del self.plugins[plugin_name]
            logger.info(f"插件 {plugin_name} 已卸载")
            return True
        return False
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginMeta]:
        """获取插件信息"""
        plugin = self.plugins.get(plugin_name)
        return plugin.meta if plugin else None