"""
预设内联查询处理器。

此模块实现了PresetInlineQuery类，用于处理
预设相关的内联查询，允许用户通过内联查询搜索和查看
可用的预设。
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

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


class PresetInlineQuery(BaseInlineQuery):
    """
    预设搜索和显示的内联查询处理器。

    允许用户使用带有'preset'触发关键词的内联查询
    搜索可用预设。提供预设信息显示，
    包括名称和描述。
    """

    meta = InlineMeta(
        name="preset_query",
        query_type="preset",
        trigger="preset",
        description="查看可用预设列表",
        enabled=True,
        cache_time=300,  # 预设偶尔变化，缓存5分钟
    )

    def __init__(self):
        """初始化预设内联查询处理器。"""
        super().__init__()
        logger.debug("已初始化PresetInlineQuery处理器")

    async def handle_inline_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> List[InlineQueryResult]:
        """
        处理预设内联查询。

        该方法处理带有 'preset' 触发器的内联查询，用于搜索和显示可用预设。支持按预设名称进行过滤。

        参数:
            update: 包含内联查询的 Telegram 更新对象
            context: python-telegram-bot 的回调上下文

        返回:
            List[InlineQueryResult]: 包含预设信息的 InlineQueryResult 对象列表
        """
        query = update.inline_query
        if not query:
            return []
        # 从查询中提取搜索词
        query_text = query.query.strip()
        search_term = ""

        # 解析查询："preset [搜索词]"
        parts = query_text.split(" ", 1)
        if len(parts) > 1:
            search_term = parts[1].strip().lower()

        user_id = query.from_user.id
        logger.debug("处理来自用户%s的预设查询，搜索词：'%s'", user_id, search_term)

        try:
            # 加载可用预设
            presets = self._load_presets()

            if not presets:
                no_presets_result = self.create_no_results_result("", "预设")
                return [self.create_result_from_data(no_presets_result)]

            # 根据搜索词过滤预设
            filtered_presets = self._filter_presets(presets, search_term)

            if not filtered_presets:
                no_match_result = self.create_no_results_result(search_term, "预设")
                return [self.create_result_from_data(no_match_result)]

            # 为过滤后的预设创建结果
            results_data = []
            for preset in filtered_presets[:50]:  # 限制为50个结果
                preset_result_data = self._create_preset_result_data(preset)
                if preset_result_data:
                    results_data.append(preset_result_data)

            # 转换为InlineQueryResult对象
            results = self.create_results_from_data(results_data)

            logger.debug("为用户%s返回%d个预设结果", user_id, len(results))
            return results

        except InlineQueryError as e:
            logger.error("用户%s的预设查询错误：%s", user_id, e, exc_info=True)
            raise e  # Re-raise to be handled by main dispatcher
        except (OSError, IOError) as e:
            logger.error("用户%s的预设查询发生IO错误：%s", user_id, e, exc_info=True)
            raise InlineQueryError(
                "预设查询处理失败", error_type="query_processing", user_friendly=True
            ) from e

    def _load_presets(self) -> List[Dict[str, Any]]:
        """
        从prompts.json文件加载可用预设列表，包含全面的错误处理。

        Returns:
            包含名称、显示名和描述的预设字典列表

        Raises:
            InlineQueryError: 如果预设加载严重失败
        """
        try:
            prompts_file = os.path.join("prompts", "prompts.json")
            logger.debug("尝试从以下位置加载预设：%s", prompts_file)

            if not os.path.exists(prompts_file):
                logger.error("预设文件未找到：%s", prompts_file)
                raise InlineQueryError(
                    "预设配置文件不存在", error_type="data_access", user_friendly=True
                )

            try:
                with open(prompts_file, "r", encoding="utf-8") as f:
                    prompts_data = json.load(f)
            except PermissionError as e:
                logger.error("读取预设文件权限被拒绝：%s", e)
                raise InlineQueryError(
                    "无权限访问预设文件", error_type="data_access", user_friendly=True
                ) from e
            except json.JSONDecodeError as e:
                logger.error("预设文件中的JSON格式无效：%s", e)
                raise InlineQueryError(
                    "预设配置文件格式错误", error_type="data_access", user_friendly=True
                ) from e

            # Validate data structure
            if not isinstance(prompts_data, dict):
                logger.error("预设数据结构无效：期望dict，得到%s", type(prompts_data))
                raise InlineQueryError(
                    "预设配置文件结构错误", error_type="data_access", user_friendly=True
                )

            # Extract preset list from prompt_set_list
            preset_list = prompts_data.get("prompt_set_list", [])

            if not isinstance(preset_list, list):
                logger.error("预设列表结构无效：期望list，得到%s", type(preset_list))
                raise InlineQueryError(
                    "预设列表格式错误", error_type="data_access", user_friendly=True
                )

            logger.debug("成功从prompts.json加载%d个预设", len(preset_list))
            return preset_list

        # InlineQueryError will be re-raised automatically
        except (OSError, IOError) as e:
            logger.error("加载预设时发生IO错误：%s", e, exc_info=True)
            raise InlineQueryError(
                "预设数据加载异常", error_type="data_access", user_friendly=True
            ) from e

    def _filter_presets(
        self, presets: List[Dict[str, Any]], search_term: str
    ) -> List[Dict[str, Any]]:
        """
        根据搜索词过滤预设。

        Args:
            presets: 所有预设字典的列表
            search_term: 用于过滤的搜索词（不区分大小写）

        Returns:
            过滤后的预设字典列表
        """
        if not search_term:
            return presets

        # 按预设名称或显示名称过滤（不区分大小写的部分匹配）
        filtered = []
        for preset in presets:
            name = preset.get("name", "").lower()
            display = preset.get("display", "").lower()
            description = preset.get("description", "").lower()

            if (
                search_term in name
                or search_term in display
                or search_term in description
            ):
                filtered.append(preset)

        logger.debug(
            "将%d个预设过滤为%d个匹配项，搜索词：'%s'",
            len(presets),
            len(filtered),
            search_term,
        )
        return filtered

    def _create_preset_result_data(
        self, preset: Dict[str, Any]
    ) -> Optional[InlineResultData]:
        """
        为预设创建InlineResultData。

        Args:
            preset: 包含名称、显示名和描述的预设字典

        Returns:
            预设的InlineResultData，如果创建失败则返回None
        """
        try:
            # 提取预设信息
            name = preset.get("name", "")
            display_name = preset.get("display", name)
            description = preset.get("description", "无描述信息")

            if not name:
                logger.warning("预设缺少名称字段")
                return None

            # 创建格式化内容，结构更好
            content_lines = [
                f"**⚙️ 预设信息：{display_name}**",
                "",
                f"**📝 描述：**",
                description if description else "无描述信息",
                "",
                f"**🔧 预设名称：** `{name}`",
                "",
                "💡 *这是预设信息预览，如需切换预设请在私聊中使用相应命令。*",
            ]

            # 创建增强格式的结果数据
            result_data = InlineResultData(
                id=f"preset_{name}",
                title=self.format_title_with_emoji(f"预设: {display_name}", "⚙️"),
                description=self.truncate_text(
                    description if description else f"预设: {display_name}", 80
                ),
                content="\n".join(content_lines),
                parse_mode="Markdown",
            )

            return result_data

        except (KeyError, TypeError, ValueError) as e:
            logger.error("为预设%s创建结果数据时出错：%s", preset, e, exc_info=True)
            return None
