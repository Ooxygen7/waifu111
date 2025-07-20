"""
内联查询处理器的基础类。

此模块定义了内联查询处理的核心架构，
包括元数据定义和处理器的抽象基类。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from telegram import Update, InlineQueryResult
from telegram.ext import ContextTypes


@dataclass
class InlineResultData:
    """
    内联查询结果结构的数据类。
    
    提供了一种标准化的方式来创建内联查询结果，
    具有适当的格式化、视觉反馈和可选的缩略图支持。
    """
    id: str
    title: str
    description: str
    content: str = ""
    thumb_url: Optional[str] = None
    parse_mode: Optional[str] = None
    
    def __post_init__(self):
        """初始化后验证和格式化结果数据。"""
        # 确保ID不为空
        if not self.id:
            raise ValueError("结果ID不能为空")
        
        # 确保标题不为空
        if not self.title:
            raise ValueError("结果标题不能为空")
        
        # 如果内容为空，使用标题作为内容
        if not self.content:
            self.content = self.title
        
        # 如果描述过长，截断以便显示
        if len(self.description) > 100:
            self.description = self.description[:97] + "..."
    
    def to_article_result(self) -> 'InlineQueryResultArticle':
        """
        转换为Telegram InlineQueryResultArticle。
        
        Returns:
            准备使用的InlineQueryResultArticle对象
        """
        from telegram import InlineQueryResultArticle, InputTextMessageContent
        
        # 使用正确的参数名称创建文章结果
        kwargs = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'input_message_content': InputTextMessageContent(
                message_text=self.content,
                parse_mode=self.parse_mode
            )
        }
        
        # 如果提供了缩略图URL，则添加
        if self.thumb_url:
            kwargs['thumbnail_url'] = self.thumb_url
        
        return InlineQueryResultArticle(**kwargs)


class InlineMeta:
    """
    内联查询处理器的元数据类。
    
    定义内联查询处理器的行为和属性，
    包括查询类型、触发关键词和缓存配置。
    """
    
    def __init__(self,
                 name: str,
                 query_type: str,
                 trigger: str = '',
                 description: str = '',
                 enabled: bool = True,
                 cache_time: int = 300):
        """
        初始化内联查询元数据。
        
        Args:
            name: 处理器的唯一名称标识符
            query_type: 查询类型分类（例如：'char'、'preset'、'help'）
            trigger: 查询的触发关键词（默认处理器使用空字符串）
            description: 处理器功能的人类可读描述
            enabled: 处理器是否启用并应该被注册
            cache_time: 查询结果的缓存时间（秒）
        """
        self.name = name
        self.query_type = query_type
        self.trigger = trigger
        self.description = description
        self.enabled = enabled
        self.cache_time = cache_time
    
    def __repr__(self):
        return (f"InlineMeta(name='{self.name}', query_type='{self.query_type}', "
                f"trigger='{self.trigger}', enabled={self.enabled})")

class BaseInlineQuery(ABC):
    """内联查询处理器的抽象基类。
    
    所有内联查询处理器都必须继承此类并实现
    handle_inline_query方法。该类强制要求存在
    用于处理器配置的meta属性。
    """
    
    meta: InlineMeta
    
    def __init__(self):
        """初始化内联查询处理器。
        
        验证处理器是否定义了必需的meta属性。
        
        Raises:
            NotImplementedError: 如果未定义meta属性
        """
        if not hasattr(self, 'meta') or not isinstance(self.meta, InlineMeta):
            raise NotImplementedError(
                f'{self.__class__.__name__} 必须定义一个InlineMeta类型的meta属性'
            )
    
    @abstractmethod
    async def handle_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> List[InlineQueryResult]:
        """处理内联查询并返回结果。
        
        此方法必须由所有具体的内联查询处理器实现。
        它应该处理内联查询并返回要显示给用户的结果列表。    
        
        Args:
            update: 包含内联查询的Telegram更新
            context: 来自python-telegram-bot的回调上下文
            
        Returns:
            要显示给用户的InlineQueryResult对象列表
            
        Raises:
            NotImplementedError: 如果子类未实现
        """
        pass
    
    def create_result_from_data(self, result_data: InlineResultData) -> InlineQueryResult:
        """
        从InlineResultData创建InlineQueryResult。
        
        Args:
            result_data: 结构化的结果数据
            
        Returns:
            准备使用的InlineQueryResult对象
        """
        return result_data.to_article_result()
    
    def create_results_from_data(self, results_data: List[InlineResultData]) -> List[InlineQueryResult]:
        """
        从InlineResultData列表创建多个InlineQueryResult。
        
        Args:
            results_data: 结构化结果数据列表
            
        Returns:
            准备使用的InlineQueryResult对象列表
        """
        return [self.create_result_from_data(data) for data in results_data]
    
    def format_title_with_emoji(self, title: str, emoji: str = "") -> str:
        """
        使用表情符号格式化标题以获得更好的视觉反馈。
        
        Args:
            title: 基础标题文本
            emoji: 可选的前置表情符号
            
        Returns:
            带有表情符号的格式化标题
        """
        if emoji:
            return f"{emoji} {title}"
        return title
    
    def truncate_text(self, text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        将文本截断到指定的最大长度并添加后缀。
        
        Args:
            text: 要截断的文本
            max_length: 允许的最大长度
            suffix: 截断时添加的后缀
            
        Returns:
            如需要则带有后缀的截断文本
        """
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    def create_info_result(self, result_id: str, title: str, description: str, 
                          content: str, emoji: str = "ℹ️") -> InlineResultData:
        """
        创建具有一致格式的标准化信息结果。
        
        Args:
            result_id: 结果的唯一标识符
            title: 结果的标题
            description: 用于显示的简短描述
            content: 选择时发送的完整内容
            emoji: 用于视觉反馈的表情符号
            
        Returns:
            具有一致格式的InlineResultData对象
        """
        return InlineResultData(
            id=result_id,
            title=self.format_title_with_emoji(title, emoji),
            description=self.truncate_text(description),
            content=content,
            parse_mode="Markdown"
        )
    
    def create_error_result(self, error_id: str, error_msg: str, 
                           title: str = "查询出错") -> InlineResultData:
        """
        创建具有一致格式的标准化错误结果。
        
        Args:
            error_id: 错误结果的唯一标识符
            error_msg: 要显示的错误消息
            title: 错误结果的标题
            
        Returns:
            用于错误显示的InlineResultData对象
        """
        return InlineResultData(
            id=error_id,
            title=self.format_title_with_emoji(title, "❌"),
            description=f"处理查询时发生错误: {error_msg}",
            content=f"查询失败：{error_msg}\n\n请稍后重试或联系管理员。"
        )
    
    def create_no_results_result(self, search_term: str = "", 
                                result_type: str = "结果") -> InlineResultData:
        """
        创建标准化的无结果找到结果。
        
        Args:
            search_term: 没有产生结果的搜索词
            result_type: 正在搜索的结果类型
            
        Returns:
            用于无结果显示的InlineResultData对象
        """
        if search_term:
            title = f"无匹配{result_type}"
            description = f"没有找到包含 '{search_term}' 的{result_type}"
            content = f"没有找到包含 '{search_term}' 的{result_type}。\n\n请尝试其他搜索词或查看所有可用选项。"
        else:
            title = f"无可用{result_type}"
            description = f"当前系统中没有可用的{result_type}"
            content = f"当前系统中没有可用的{result_type}。\n\n请联系管理员添加相关内容。"
        
        return InlineResultData(
            id=f"no_{result_type.lower()}",
            title=self.format_title_with_emoji(title, "🔍"),
            description=description,
            content=content
        )
    
    def __repr__(self):
        return f"{self.__class__.__name__}(meta={self.meta})"