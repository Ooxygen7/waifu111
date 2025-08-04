"""
内联查询管理和路由系统。

此模块提供InlineQueryHandlers类，用于动态处理器加载
和统一的内联查询分发，遵循与命令和回调处理器
相同的架构模式。
"""

import importlib
import inspect
import logging
import traceback
from typing import List, Dict, Tuple, Optional
from telegram import Update, InlineQueryResult, InlineQueryResultArticle, InputTextMessageContent
from telegram.helpers import escape_markdown
from telegram.ext import ContextTypes

from .base import BaseInlineQuery, InlineResultData

# 设置日志
logger = logging.getLogger(__name__)

# 导入内联处理器的增强日志功能
try:
    from .logging_config import inline_query_logger, setup_inline_handlers_logging
    setup_inline_handlers_logging()
except ImportError:
    # 如果logging_config不可用则使用后备方案
    inline_query_logger = None


class InlineQueryError(Exception):
    """内联查询处理错误的自定义异常。"""
    
    def __init__(self, message: str, error_type: str = "general", user_friendly: bool = True):
        """
        初始化内联查询错误。
        
        Args:
            message: 错误消息
            error_type: 错误类型 (handler_loading, data_access, query_processing, 等)
            user_friendly: 消息是否可以安全地显示给用户
        """
        super().__init__(message)
        self.error_type = error_type
        self.user_friendly = user_friendly


class ErrorResultFactory:
    """创建标准化错误结果的工厂类。"""
    
    @staticmethod
    def create_error_result(error_msg: str, error_id: str = "error", 
                          title: str = "查询出错") -> List[InlineQueryResult]:
        """
        为查询处理失败创建标准化错误结果。
        
        Args:
            error_msg: 要显示的错误消息
            error_id: 错误结果的唯一ID
            title: 错误结果的标题
            
        Returns:
            包含单个错误结果的列表
        """
        try:
            error_data = InlineResultData(
                id=error_id,
                title=f"❌ {title}",
                description=f"处理查询时发生错误: {error_msg}",
                content=f"**❌ 查询失败：{escape_markdown(error_msg, version=1)}**\n\n请稍后重试或联系管理员。",
                parse_mode="Markdown"
            )
            return [error_data.to_article_result()]
        except Exception as e:
            logger.error(f"Failed to create error result: {e}", exc_info=True)
            # 回退到最小错误结果
            return [
                InlineQueryResultArticle(
                    id="fallback_error",
                    title="❌ 系统错误",
                    description="无法处理查询请求",
                    input_message_content=InputTextMessageContent(
                        message_text="系统发生错误，请稍后重试。"
                    )
                )
            ]
    
    @staticmethod
    def create_data_access_error_result(resource_type: str) -> List[InlineQueryResult]:
        """
        为数据访问失败创建具有优雅降级的错误结果。
        
        Args:
            resource_type: 加载失败的资源类型 (characters, presets, 等)
            
        Returns:
            包含有用信息的错误结果列表
        """
        error_data = InlineResultData(
            id=f"data_error_{resource_type}",
            title=f"⚠️ 无法加载{resource_type}",
            description=f"数据访问失败，请稍后重试",
            content=f"**⚠️ 无法加载{resource_type}数据**\n\n"
                    f"**可能的原因：**\n"
                    f"• 数据文件不存在或损坏\n"
                    f"• 系统暂时不可用\n"
                    f"• 权限不足\n\n"
                    f"请稍后重试或联系管理员。",
            parse_mode="Markdown"
        )
        return [error_data.to_article_result()]
    
    @staticmethod
    def create_handler_loading_error_result() -> List[InlineQueryResult]:
        """
        为处理器加载失败创建错误结果。
        
        Returns:
            包含处理器加载问题错误结果的列表
        """
        error_data = InlineResultData(
            id="handler_loading_error",
            title="🔧 功能暂时不可用",
            description="查询处理器加载失败",
            content="**🔧 查询功能暂时不可用**\n\n"
                    "系统正在维护中，请稍后重试。\n"
                    "如果问题持续存在，请联系管理员。",
            parse_mode="Markdown"
        )
        return [error_data.to_article_result()]


class InlineQueryHandlers:
    """
    管理内联查询处理器的静态类。
    
    提供动态处理器加载和统一查询分发的方法，
    遵循与CommandHandlers和CallbackHandlers相同的模式。
    """
    
    @staticmethod
    def get_inline_handlers(module_names: List[str]) -> List[BaseInlineQuery]:
        """
        动态扫描指定模块并提取所有BaseInlineQuery子类。
        
        Args:
            module_names: 要扫描内联查询处理器的模块名称列表
            
        Returns:
            已启用的BaseInlineQuery实例列表
        """
        inline_handlers = []
        failed_modules = []
        failed_handlers = []
        
        logger.info(f"Starting to load inline handlers from modules: {module_names}")
        
        for module_name in module_names:
            try:
                logger.debug(f"Attempting to import module: {module_name}")
                # 动态模块导入
                module = importlib.import_module(f"bot_core.inline_handlers.{module_name}")
                logger.debug(f"Successfully imported module: {module_name}")
                
            except ImportError as e:
                error_msg = f"Failed to import module {module_name}: {e}"
                logger.error(error_msg, exc_info=True)
                failed_modules.append((module_name, str(e)))
                continue
            except Exception as e:
                error_msg = f"Unexpected error importing module {module_name}: {e}"
                logger.error(error_msg, exc_info=True)
                failed_modules.append((module_name, str(e)))
                continue
            
            # 扫描模块中的所有成员
            module_handlers_count = 0
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BaseInlineQuery)
                    and obj != BaseInlineQuery
                ):
                    try:
                        logger.debug(f"Found handler class: {name} in module {module_name}")
                        # 创建处理器实例
                        instance = obj()
                        
                        # 验证处理器实例
                        if not hasattr(instance, 'meta'):
                            raise InlineQueryError(
                                f"Handler {name} missing meta attribute",
                                error_type="handler_loading",
                                user_friendly=False
                            )
                        
                        # 检查处理器是否已启用
                        if instance.meta.enabled:
                            inline_handlers.append(instance)
                            module_handlers_count += 1
                            logger.info(
                                f"Successfully loaded inline handler: {name} "
                                f"(query_type: {instance.meta.query_type}, "
                                f"trigger: '{instance.meta.trigger}', "
                                f"cache_time: {instance.meta.cache_time}s)"
                            )
                        else:
                            logger.info(f"Skipping disabled inline handler: {name}")
                            
                    except InlineQueryError as e:
                        error_msg = f"Handler validation failed for {name}: {e}"
                        logger.error(error_msg, exc_info=True)
                        failed_handlers.append((name, str(e)))
                        continue
                    except Exception as e:
                        error_msg = f"Unexpected error creating handler instance for {name}: {e}"
                        logger.error(error_msg, exc_info=True)
                        failed_handlers.append((name, str(e)))
                        continue
            
            logger.debug(f"Loaded {module_handlers_count} handlers from module {module_name}")
        
        # 记录摘要
        total_handlers = len(inline_handlers)
        logger.info(f"Handler loading complete: {total_handlers} handlers loaded successfully")
        
        if failed_modules:
            logger.warning(f"Failed to load {len(failed_modules)} modules: {[name for name, _ in failed_modules]}")
        
        if failed_handlers:
            logger.warning(f"Failed to load {len(failed_handlers)} handlers: {[name for name, _ in failed_handlers]}")
        
        # 确保至少加载了一些处理器
        if total_handlers == 0:
            logger.error("No inline handlers were loaded successfully! Inline query functionality will be limited.")
        
        return inline_handlers
    
    @staticmethod
    def parse_inline_query(query: str) -> Tuple[str, str]:
        """
        解析内联查询字符串以提取查询类型和搜索词。
        
        Args:
            query: 来自用户输入的内联查询字符串
            
        Returns:
            (query_type, search_term)的元组
            - query_type: 查询的第一个词（触发关键字）
            - search_term: 第一个词之后查询的剩余部分
        """
        if not query or not query.strip():
            return '', ''
        
        parts = query.strip().split(' ', 1)
        if len(parts) == 1:
            return parts[0], ''
        return parts[0], parts[1].strip()
    
    @staticmethod
    async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        统一的内联查询分发器，将查询路由到适当的处理器。
        
        此方法解析传入的内联查询，根据触发关键字找到匹配的处理器，
        并分发查询进行处理。
        
        Args:
            update: 包含内联查询的Telegram更新
            context: 来自python-telegram-bot的回调上下文
        """
        query = update.inline_query
        if not query:
            logger.warning("Received update without inline query")
            return
        
        query_text = query.query
        user_id = query.from_user.id
        username = getattr(query.from_user, 'username', 'unknown')
        
        # 记录查询开始
        logger.info(f"Processing inline query from user {user_id} (@{username}): '{query_text}'")
        
        try:
            # 解析查询以提取类型和搜索词
            query_type, search_term = InlineQueryHandlers.parse_inline_query(query_text)
            
            logger.debug(f"Parsed query - type: '{query_type}', search_term: '{search_term}'")
            
            # 获取所有可用的处理器并进行错误处理
            try:
                handlers = InlineQueryHandlers.get_inline_handlers([
                    'character', 'preset', 'help', 'default'
                ])
                
                if not handlers:
                    raise InlineQueryError(
                        "No handlers available",
                        error_type="handler_loading",
                        user_friendly=True
                    )
                    
            except Exception as e:
                logger.error(f"Failed to load handlers: {e}", exc_info=True)
                await InlineQueryHandlers._send_error_response(
                    query, 
                    "系统暂时不可用，请稍后重试",
                    error_type="handler_loading"
                )
                return
            
            # 查找匹配的处理器
            matching_handler = None
            default_handler = None
            
            for handler in handlers:
                if handler.meta.trigger == query_type:
                    matching_handler = handler
                    break
                elif handler.meta.trigger == '':  # 默认处理器
                    default_handler = handler
            
            # 使用匹配的处理器或回退到默认处理器
            selected_handler = matching_handler or default_handler
            
            if selected_handler:
                handler_name = selected_handler.__class__.__name__
                logger.debug(f"Using handler: {handler_name} for query_type: '{query_type}'")
                
                try:
                    # 使用选定的处理器处理查询
                    results = await selected_handler.handle_inline_query(update, context)
                    
                    if not results:
                        logger.warning(f"Handler {handler_name} returned empty results")
                        results = ErrorResultFactory.create_error_result(
                            "没有找到相关结果",
                            error_id="no_results",
                            title="无结果"
                        )
                    
                    # 用结果回答内联查询
                    await query.answer(
                        results=results,
                        cache_time=selected_handler.meta.cache_time,
                        is_personal=True
                    )
                    
                    logger.info(f"Successfully processed query for user {user_id}, "
                              f"returned {len(results)} results using {handler_name}")
                    
                except InlineQueryError as e:
                    logger.error(f"Handler {handler_name} error: {e}", exc_info=True)
                    await InlineQueryHandlers._send_error_response(
                        query, 
                        str(e) if e.user_friendly else "处理查询时发生错误",
                        error_type=e.error_type
                    )
                except Exception as e:
                    logger.error(f"Unexpected error in handler {handler_name}: {e}", exc_info=True)
                    await InlineQueryHandlers._send_error_response(
                        query, 
                        "查询处理失败，请稍后重试",
                        error_type="query_processing"
                    )
                
            else:
                logger.warning(f"No handler found for query_type: '{query_type}', available handlers: "
                             f"{[h.meta.trigger for h in handlers]}")
                # 提供后备响应
                await InlineQueryHandlers._send_no_handler_response(query)
                
        except InlineQueryError as e:
            logger.error(f"Inline query error for user {user_id}: {e}", exc_info=True)
            await InlineQueryHandlers._send_error_response(
                query, 
                str(e) if e.user_friendly else "查询处理失败",
                error_type=e.error_type
            )
        except Exception as e:
            logger.error(f"Unexpected error processing inline query from user {user_id}: {e}", exc_info=True)
            await InlineQueryHandlers._send_error_response(
                query, 
                "系统发生错误，请稍后重试",
                error_type="general"
            )
    
    @staticmethod
    async def _send_error_response(query, error_msg: str, error_type: str = "general") -> None:
        """
        为失败的查询处理发送具有优雅降级的错误响应。
        
        Args:
            query: 内联查询对象
            error_msg: 要显示的错误消息
            error_type: 用于日志记录和分类的错误类型
        """
        try:
            # 根据错误类型创建适当的错误结果
            if error_type == "handler_loading":
                error_results = ErrorResultFactory.create_handler_loading_error_result()
            elif error_type == "data_access":
                error_results = ErrorResultFactory.create_data_access_error_result("数据")
            else:
                error_results = ErrorResultFactory.create_error_result(error_msg)
            
            await query.answer(results=error_results, cache_time=60)
            logger.debug(f"Sent error response for error_type: {error_type}")
            
        except Exception as e:
            logger.error(f"Failed to send error response: {e}", exc_info=True)
            # 最后手段：尝试发送最小响应
            try:
                minimal_error = [
                    InlineQueryResultArticle(
                        id="critical_error",
                        title="系统错误",
                        description="无法处理请求",
                        input_message_content=InputTextMessageContent(
                            message_text="系统发生严重错误，请联系管理员。"
                        )
                    )
                ]
                await query.answer(results=minimal_error, cache_time=30)
            except Exception as critical_e:
                logger.critical(f"Critical failure: Cannot send any error response: {critical_e}")
    
    @staticmethod
    async def _send_no_handler_response(query) -> None:
        """
        当没有找到查询处理器时发送具有优雅降级的响应。
        
        Args:
            query: 内联查询对象
        """
        try:
            no_handler_data = InlineResultData(
                id="no_handler",
                title="❓ 未知查询类型",
                description="请使用 help 查看可用的查询类型",
                content="**❓ 未知的查询类型**\n\n"
                        "请使用 `@botname help` 查看帮助信息。\n\n"
                        "**可用的查询类型：**\n"
                        "• `char` - 查询角色\n"
                        "• `preset` - 查询预设\n"
                        "• `help` - 获取帮助",
                parse_mode="Markdown"
            )
            no_handler_results = [no_handler_data.to_article_result()]
            await query.answer(results=no_handler_results, cache_time=300)
            logger.debug("Sent no handler response")
            
        except Exception as e:
            logger.error(f"Failed to send no handler response: {e}", exc_info=True)
            # 回退到错误响应
            await InlineQueryHandlers._send_error_response(
                query, 
                "无法找到合适的处理器",
                error_type="handler_loading"
            )


def create_inline_query_handler(module_names: List[str]) -> 'InlineQueryDispatcher':
    """
创建一个加载了处理器的InlineQueryDispatcher实例。

Args:
    module_names: 要扫描处理器的模块名称列表
    
Returns:
    准备使用的InlineQueryDispatcher实例
"""
    handlers = InlineQueryHandlers.get_inline_handlers(module_names)
    return InlineQueryDispatcher(handlers)


class InlineQueryDispatcher:
    """
    将内联查询路由到适当处理器的分发器类。
    
    此类维护处理器的映射，并提供处理内联查询的主要
    分发方法。
    """
    
    def __init__(self, handlers: List[BaseInlineQuery]):
        """
        使用处理器列表初始化分发器。
        
        Args:
            handlers: BaseInlineQuery实例列表
        """
        self.handlers = handlers
        self._handler_map = self._build_handler_map(handlers)
        
        logger.info(f"Initialized InlineQueryDispatcher with {len(handlers)} handlers")
        for handler in handlers:
            logger.debug(f"  - {handler.__class__.__name__}: trigger='{handler.meta.trigger}'")
    
    def _build_handler_map(self, handlers: List[BaseInlineQuery]) -> Dict[str, BaseInlineQuery]:
        """
        构建从触发关键字到处理器的映射。
        
        Args:
            handlers: 处理器实例列表
            
        Returns:
            将触发关键字映射到处理器实例的字典
        """
        handler_map = {}
        default_handler = None
        
        for handler in handlers:
            trigger = handler.meta.trigger
            if trigger == '':
                default_handler = handler
            else:
                handler_map[trigger] = handler
        
        # 使用特殊键添加默认处理器
        if default_handler:
            handler_map['__default__'] = default_handler
        
        return handler_map
    
    async def dispatch_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理内联查询的主要分发方法。
        
        Args:
            update: 包含内联查询的Telegram更新
            context: 来自python-telegram-bot的回调上下文
        """
        await InlineQueryHandlers.handle_inline_query(update, context)