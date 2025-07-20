
"""\nCyberWaifu Telegram Bot 内联查询处理器模块。\n\n此模块提供了一个统一的内联查询处理系统，通过\n类似于命令和回调处理器的基类架构实现。\n"""

from .base import InlineMeta, BaseInlineQuery
from .inline import InlineQueryHandlers, InlineQueryDispatcher, create_inline_query_handler
from .character import CharacterInlineQuery
from .preset import PresetInlineQuery
from .help import HelpInlineQuery
from .default import DefaultInlineQuery

__all__ = [
    'InlineMeta', 
    'BaseInlineQuery', 
    'InlineQueryHandlers', 
    'InlineQueryDispatcher', 
    'create_inline_query_handler',
    'CharacterInlineQuery',
    'PresetInlineQuery',
    'HelpInlineQuery',
    'DefaultInlineQuery'
]