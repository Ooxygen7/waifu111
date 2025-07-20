"""默认内联查询处理器。

此模块实现了DefaultInlineQuery类，用于处理
空查询和不匹配的查询类型，为用户提供
基本使用提示和可用查询类型信息。
"""

import logging
from typing import List
from telegram import Update, InlineQueryResult, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes

from .base import BaseInlineQuery, InlineMeta, InlineResultData
from .inline import InlineQueryError, ErrorResultFactory

# 设置日志
logger = logging.getLogger(__name__)


class DefaultInlineQuery(BaseInlineQuery):
    """
    用于回退场景的默认内联查询处理器。
    
    通过提供基本使用提示和可用查询类型信息
    来处理空查询和不匹配的查询类型。
    此处理器使用空触发器作为回退处理。
    """
    
    meta = InlineMeta(
        name='default_query',
        query_type='default',
        trigger='',  # 空触发器用于回退处理
        description='默认查询处理',
        enabled=True,
        cache_time=60  # 短缓存时间，因为这是基本信息
    )
    
    def __init__(self):
        """初始化默认内联查询处理器。"""
        super().__init__()
        logger.debug("已初始化DefaultInlineQuery处理器")
    
    async def handle_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> List[InlineQueryResult]:
        """处理空查询或不匹配查询的默认内联查询。
        
        处理不匹配任何特定处理器或为空的内联查询，
        提供基本使用提示和可用查询类型。
        
        Args:
            update: 包含内联查询的Telegram更新
            context: 来自python-telegram-bot的回调上下文
            
        Returns:
            包含使用提示的InlineQueryResult对象列表
        """
        query = update.inline_query
        if not query:
            return []
        user_id = query.from_user.id
        query_text = query.query.strip()
        
        logger.debug(f"处理来自用户{user_id}的默认查询：'{query_text}'")
        
        try:
            # 创建包含使用提示的默认结果数据
            results_data = self._create_default_results_data(query_text)
            
            # 转换为InlineQueryResult对象
            results = self.create_results_from_data(results_data)
            
            logger.debug(f"为用户{user_id}返回{len(results)}个默认结果")
            return results
            
        except Exception as e:
            logger.error(f"用户{user_id}的默认查询发生意外错误：{e}", exc_info=True)
            raise InlineQueryError(
                "默认查询处理失败",
                error_type="query_processing",
                user_friendly=True
            )
    def _create_default_results_data(self, query_text: str) -> List[InlineResultData]:
        """创建包含使用提示和可用查询类型的默认结果数据。
        
        Args:
            query_text: 来自用户的原始查询文本
            
        Returns:
            包含使用信息的InlineResultData对象列表
        """
        results_data = []
        
        # 基本使用提示 - 总是首先显示
        results_data.append(
            InlineResultData(
                id="default_usage",
                title=self.format_title_with_emoji("如何使用内联查询", "💡"),
                description="了解内联查询的基本用法",
                content=self._get_basic_usage_text(),
                parse_mode="Markdown"
            )
        )
        
        # 可用查询类型
        results_data.append(
            InlineResultData(
                id="default_types",
                title=self.format_title_with_emoji("可用查询类型", "🔍"),
                description="查看所有支持的查询类型",
                content=self._get_available_types_text(),
                parse_mode="Markdown"
            )
        )
        
        # 如果有不匹配的查询文本，提供特定帮助
        if query_text:
            results_data.append(
                InlineResultData(
                    id="default_nomatch",
                    title=self.format_title_with_emoji("查询未匹配", "❓"),
                    description=f"'{query_text}' 不是有效的查询类型",
                    content=self._get_no_match_text(query_text),
                    parse_mode="Markdown"
                )
            )
        
        # 快速示例
        results_data.append(
            InlineResultData(
                id="default_examples",
                title=self.format_title_with_emoji("使用示例", "📝"),
                description="查看常用查询示例",
                content=self._get_examples_text(),
                parse_mode="Markdown"
            )
        )
        
        return results_data
    
    def _get_basic_usage_text(self) -> str:
        """
        获取内联查询的基本使用提示文本。
        
        Returns:
            格式化的基本使用文本字符串
        """
        return """💡 **内联查询基本用法**

内联查询让您可以在任何聊天中快速访问机器人功能！

**基本格式：**
`@botname [查询类型] [搜索词]`

**开始使用：**
1. 在任何聊天中输入 `@botname`
2. 添加空格后输入查询类型
3. 可选择性地添加搜索词进行筛选

**提示：**
• 不确定怎么用？试试输入 `@botname help`
• 想看角色？试试 `@botname char`
• 想看预设？试试 `@botname preset`

🚀 **立即开始使用内联查询吧！**"""
    
    def _get_available_types_text(self) -> str:
        """
        获取可用查询类型文本。
        
        Returns:
            格式化的可用类型文本字符串
        """
        return """🔍 **可用查询类型**

以下是所有支持的内联查询类型：

**📚 查询类型列表：**

• **`char`** - 角色查询
  查看和搜索可用的角色列表
  示例：`@botname char` 或 `@botname char 脆脆`

• **`preset`** - 预设查询
  查看和搜索可用的对话预设
  示例：`@botname preset` 或 `@botname preset 一般`

• **`help`** - 帮助信息
  获取详细的使用帮助和说明
  示例：`@botname help`

**💡 使用技巧：**
• 所有查询都支持搜索词筛选
• 查询结果仅用于查看，不会执行操作
• 实际切换角色或预设请在私聊中进行

选择任意类型开始探索！"""
    
    def _get_no_match_text(self, query_text: str) -> str:
        """
        获取不匹配查询的文本。
        
        Args:
            query_text: 不匹配的查询文本
            
        Returns:
            格式化的无匹配文本字符串
        """
        return f"""❓ **查询未匹配**

您输入的查询 `{query_text}` 不是有效的查询类型。

**有效的查询类型：**
• `char` - 查询角色
• `preset` - 查询预设  
• `help` - 获取帮助

**建议：**
• 检查拼写是否正确
• 使用上述有效的查询类型之一
• 输入 `@botname help` 获取详细帮助

**示例：**
• `@botname char` - 查看所有角色
• `@botname preset` - 查看所有预设
• `@botname help` - 获取使用帮助

🔄 **请重新尝试使用正确的查询类型！**"""
    
    def _get_examples_text(self) -> str:
        """
        获取包含常用使用模式的示例文本。
        
        Returns:
            格式化的示例文本字符串
        """
        return """📝 **使用示例**

以下是一些常用的内联查询示例：

**🎭 角色查询示例：**
• `@botname char` - 显示所有可用角色
• `@botname char 脆脆` - 搜索包含"脆脆"的角色
• `@botname char miku` - 搜索包含"miku"的角色

**⚙️ 预设查询示例：**
• `@botname preset` - 显示所有可用预设
• `@botname preset 一般` - 搜索包含"一般"的预设
• `@botname preset nsfw` - 搜索特定类型的预设

**📖 帮助查询示例：**
• `@botname help` - 获取完整帮助信息
• `@botname help` - 查看使用说明

**💡 实用技巧：**
• 搜索词不区分大小写
• 支持部分匹配搜索
• 结果按相关性排序

现在就试试这些示例吧！"""