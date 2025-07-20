"""内联处理器模块的日志配置。

此模块为内联查询处理器提供专门的日志配置，
包括性能监控、错误跟踪和用户活动日志。
"""

import logging
import time
from functools import wraps
from typing import Callable, Any
from telegram import Update


class InlineQueryLogger:
    """内联查询操作的专用日志记录器。"""
    
    def __init__(self, name: str):
        """
        初始化内联查询日志记录器。
        
        Args:
            name: 日志记录器名称（通常是模块名称）
        """
        self.logger = logging.getLogger(name)
        self.performance_logger = logging.getLogger(f"{name}.performance")
        self.error_logger = logging.getLogger(f"{name}.errors")
        self.user_activity_logger = logging.getLogger(f"{name}.user_activity")
    
    def log_query_start(self, user_id: int, query_text: str, handler_name: str):
        """记录查询处理的开始。"""
        self.user_activity_logger.info(
            f"Query started - User: {user_id}, Handler: {handler_name}, Query: '{query_text}'"
        )
    
    def log_query_end(self, user_id: int, handler_name: str, result_count: int, duration: float):
        """记录查询处理的结束并包含性能指标。"""
        self.performance_logger.info(
            f"Query completed - User: {user_id}, Handler: {handler_name}, "
            f"Results: {result_count}, Duration: {duration:.3f}s"
        )
    
    def log_error(self, user_id: int, handler_name: str, error: Exception, error_type: str = "unknown"):
        """记录带有上下文信息的错误。"""
        self.error_logger.error(
            f"Error in {handler_name} for user {user_id} (type: {error_type}): {error}",
            exc_info=True,
            extra={
                'user_id': user_id,
                'handler_name': handler_name,
                'error_type': error_type,
                'error_message': str(error)
            }
        )
    
    def log_data_access(self, operation: str, resource: str, success: bool, duration: float = None):
        """记录数据访问操作。"""
        level = logging.DEBUG if success else logging.WARNING
        message = f"Data access - Operation: {operation}, Resource: {resource}, Success: {success}"
        if duration is not None:
            message += f", Duration: {duration:.3f}s"
        
        self.logger.log(level, message)
    
    def log_handler_loading(self, handler_name: str, success: bool, error: Exception = None):
        """记录处理器加载操作。"""
        if success:
            self.logger.info(f"Handler loaded successfully: {handler_name}")
        else:
            self.error_logger.error(
                f"Failed to load handler: {handler_name} - {error}",
                exc_info=True if error else False
            )


def log_performance(logger: InlineQueryLogger):
    """
    为处理器方法记录性能指标的装饰器。
    
    Args:
        logger: InlineQueryLogger实例
        
    Returns:
        带有性能日志的装饰函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            handler_name = args[0].__class__.__name__ if args else "Unknown"
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 如果可用，从更新中提取user_id
                user_id = None
                if len(args) > 1 and isinstance(args[1], Update):
                    update = args[1]
                    if update.inline_query and update.inline_query.from_user:
                        user_id = update.inline_query.from_user.id
                
                result_count = len(result) if isinstance(result, list) else 0
                logger.log_query_end(user_id or 0, handler_name, result_count, duration)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # 如果可用，从更新中提取user_id
                user_id = None
                if len(args) > 1 and isinstance(args[1], Update):
                    update = args[1]
                    if update.inline_query and update.inline_query.from_user:
                        user_id = update.inline_query.from_user.id
                
                logger.log_error(user_id or 0, handler_name, e, "performance_tracking")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            handler_name = args[0].__class__.__name__ if args else "Unknown"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log_data_access(func.__name__, handler_name, True, duration)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.log_data_access(func.__name__, handler_name, False, duration)
                logger.log_error(0, handler_name, e, "data_access")
                raise
        
        # 根据函数是否为异步返回适当的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def setup_inline_handlers_logging():
    """
    为内联处理器设置专门的日志配置。
    
    此函数为内联查询处理的不同方面配置
    具有适当级别和格式的日志记录器。
    """
    # 配置主要的内联处理器日志记录器
    inline_logger = logging.getLogger('bot_core.inline_handlers')
    inline_logger.setLevel(logging.DEBUG)
    
    # 配置性能日志记录器
    performance_logger = logging.getLogger('bot_core.inline_handlers.performance')
    performance_logger.setLevel(logging.INFO)
    
    # 配置错误日志记录器
    error_logger = logging.getLogger('bot_core.inline_handlers.errors')
    error_logger.setLevel(logging.ERROR)
    
    # 配置用户活动日志记录器
    user_activity_logger = logging.getLogger('bot_core.inline_handlers.user_activity')
    user_activity_logger.setLevel(logging.INFO)
    
    # 为内联处理器创建专门的格式化器
    inline_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
    )
    
    # 如果存在现有处理器，则应用格式化器
    for logger in [inline_logger, performance_logger, error_logger, user_activity_logger]:
        for handler in logger.handlers:
            handler.setFormatter(inline_formatter)
    
    logging.getLogger('bot_core.inline_handlers').info("Inline handlers logging configured")


# 创建模块级日志记录器实例以便于导入
inline_query_logger = InlineQueryLogger('bot_core.inline_handlers')
character_logger = InlineQueryLogger('bot_core.inline_handlers.character')
preset_logger = InlineQueryLogger('bot_core.inline_handlers.preset')
help_logger = InlineQueryLogger('bot_core.inline_handlers.help')
default_logger = InlineQueryLogger('bot_core.inline_handlers.default')