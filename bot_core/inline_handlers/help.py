"""
帮助内联查询处理器。

此模块实现了HelpInlineQuery类，用于处理
帮助相关的内联查询，为用户提供使用说明
和可用查询类型的信息。
"""

import logging
from typing import List

from telegram import (
    InlineQueryResult,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.ext import ContextTypes

from .base import BaseInlineQuery, InlineMeta, InlineResultData
from .inline import ErrorResultFactory, InlineQueryError

# 设置日志
logger = logging.getLogger(__name__)


class HelpInlineQuery(BaseInlineQuery):
    """
    帮助和使用信息的内联查询处理器。

    当用户使用'help'触发关键词时，为用户提供使用说明
    和可用内联查询类型的信息。
    """

    meta = InlineMeta(
        name="help_query",
        query_type="help",
        trigger="help",
        description="获取使用帮助",
        enabled=True,
        cache_time=3600,  # 帮助内容很少变化，缓存1小时
    )

    def __init__(self):
        """初始化帮助内联查询处理器。"""
        super().__init__()
        logger.debug("已初始化HelpInlineQuery处理器")

    async def handle_inline_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> List[InlineQueryResult]:
        """
        处理帮助内联查询。

        处理带有'help'触发器的内联查询，提供使用说明
        和可用查询类型的信息。

        Args:
            update: 包含内联查询的Telegram更新
            context: 来自python-telegram-bot的回调上下文

        Returns:
            包含帮助信息的InlineQueryResult对象列表
        """
        query = update.inline_query
        if not query:
            return []
        user_id = query.from_user.id
        logger.debug(f"处理来自用户{user_id}的帮助查询")

        try:
            # 创建帮助结果数据
            results_data = self._create_help_results_data()

            # 转换为InlineQueryResult对象
            results = self.create_results_from_data(results_data)

            logger.debug(f"为用户{user_id}返回{len(results)}个帮助结果")
            return results

        except Exception as e:
            logger.error(f"用户{user_id}的帮助查询发生意外错误：{e}", exc_info=True)
            raise InlineQueryError(
                "帮助信息获取失败", error_type="query_processing", user_friendly=True
            )

    def _create_help_results_data(self) -> List[InlineResultData]:
        """
        创建包含使用说明和可用查询类型的帮助结果数据。

        Returns:
            List[InlineResultData]: 包含帮助信息的InlineResultData对象列表
        """
        results_data = []
        # 通用使用帮助
        results_data.append(
            InlineResultData(
                id="help_general",
                title=self.format_title_with_emoji("内联查询使用帮助", "📖"),
                description="了解如何使用机器人的内联查询功能",
                content=self._get_general_help_text(),
                parse_mode="Markdown",
            )
        )

        # 角色查询帮助
        results_data.append(
            InlineResultData(
                id="help_char",
                title=self.format_title_with_emoji("角色查询帮助", "👤"),
                description="了解如何查询可用角色",
                content=self._get_character_help_text(),
                parse_mode="Markdown",
            )
        )

        # 预设查询帮助
        results_data.append(
            InlineResultData(
                id="help_preset",
                title=self.format_title_with_emoji("预设查询帮助", "⚙️"),
                description="了解如何查询可用预设",
                content=self._get_preset_help_text(),
                parse_mode="Markdown",
            )
        )

        # 快速参考
        results_data.append(
            InlineResultData(
                id="help_quick",
                title=self.format_title_with_emoji("快速参考", "⚡"),
                description="所有可用查询类型的快速参考",
                content=self._get_quick_reference_text(),
                parse_mode="Markdown",
            )
        )

        return results_data

    def _get_general_help_text(self) -> str:
        """
        获取解释内联查询使用方法的通用帮助文本。

        Returns:
            格式化的帮助文本字符串
        """
        return """📖 **内联查询使用帮助**

内联查询允许您在任何聊天中快速访问机器人功能，无需切换到机器人私聊。

**基本用法：**
在任何聊天中输入 `@botname` 后跟查询类型和搜索词。

**可用查询类型：**
• `char` - 查询可用角色
• `preset` - 查询可用预设
• `help` - 获取帮助信息

**示例：**
• `@botname char` - 显示所有角色
• `@botname char 脆脆` - 搜索包含"脆脆"的角色
• `@botname preset` - 显示所有预设
• `@botname help` - 显示帮助信息

💡 **提示：** 选择结果后会显示详细信息，但不会执行切换操作。"""

    def _get_character_help_text(self) -> str:
        """
        获取角色查询帮助文本。

        Returns:
            格式化的角色帮助文本字符串
        """
        return """👤 **角色查询帮助**

使用角色查询功能可以快速浏览和了解可用的角色。

**用法：**
• `@botname char` - 显示所有可用角色
• `@botname char [搜索词]` - 搜索特定角色

**示例：**
• `@botname char` - 显示所有角色列表
• `@botname char 脆脆` - 搜索名称包含"脆脆"的角色
• `@botname char miku` - 搜索名称包含"miku"的角色

**功能特点：**
• 支持模糊搜索角色名称
• 显示角色的基本信息和描述
• 仅用于查看，不会切换当前角色

💡 **提示：** 如需切换角色，请使用私聊中的相应命令。"""

    def _get_preset_help_text(self) -> str:
        """
        获取预设查询帮助文本。

        Returns:
            格式化的预设帮助文本字符串
        """
        return """⚙️ **预设查询帮助**

使用预设查询功能可以快速浏览和了解可用的对话预设。

**用法：**
• `@botname preset` - 显示所有可用预设
• `@botname preset [搜索词]` - 搜索特定预设

**示例：**
• `@botname preset` - 显示所有预设列表
• `@botname preset 一般` - 搜索包含"一般"的预设
• `@botname preset nsfw` - 搜索包含"nsfw"的预设

**功能特点：**
• 支持按名称、显示名或描述搜索
• 显示预设的详细信息和说明
• 仅用于查看，不会切换当前预设

💡 **提示：** 如需切换预设，请使用私聊中的相应命令。"""

    def _get_quick_reference_text(self) -> str:
        """
        获取包含所有可用查询类型的快速参考文本。

        Returns:
            格式化的快速参考文本字符串
        """
        return """⚡ **快速参考**

**所有可用的内联查询类型：**

🔍 **查询格式：** `@botname [类型] [搜索词]`

**可用类型：**
• `char` - 角色查询
  - 查看和搜索可用角色
  - 显示角色信息和描述

• `preset` - 预设查询
  - 查看和搜索对话预设
  - 显示预设功能说明

• `help` - 帮助信息
  - 获取使用说明和帮助
  - 了解各种功能用法

**快速示例：**
• `@botname char 脆脆` 🔍 搜索角色
• `@botname preset 一般` 🔍 搜索预设
• `@botname help` 📖 获取帮助

💡 **记住：** 内联查询仅用于查看信息，实际操作请在私聊中进行。"""
