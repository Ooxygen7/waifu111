"""角色内联查询处理器。

此模块实现了CharacterInlineQuery类，用于处理
角色相关的内联查询，允许用户通过内联查询搜索和查看
可用的角色。
"""

import logging
import os
from typing import List, Optional

from telegram import (
    InlineQueryResult,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.ext import ContextTypes

from utils.file_utils import list_all_characters, load_char

from .base import BaseInlineQuery, InlineMeta, InlineResultData
from .inline import ErrorResultFactory, InlineQueryError

# 设置日志
logger = logging.getLogger(__name__)


class CharacterInlineQuery(BaseInlineQuery):
    """
    角色搜索和显示的内联查询处理器。

    允许用户使用带有'char'触发关键词的内联查询
    搜索可用角色。提供角色信息显示，
    包括名称和描述。
    """

    meta = InlineMeta(
        name="character_query",
        query_type="char",
        trigger="char",
        description="查看可用角色列表",
        enabled=True,
        cache_time=600,  # 角色变化不频繁，缓存10分钟
    )

    def __init__(self):
        """初始化角色内联查询处理器。"""
        super().__init__()
        logger.debug("已初始化CharacterInlineQuery处理器")

    async def handle_inline_query(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> List[InlineQueryResult]:
        """
        处理角色内联查询。

        处理带有'char'触发器的内联查询以搜索和显示可用角色。支持按角色名称过滤。

        Args:
            update: 包含内联查询的Telegram更新
            context: 来自python-telegram-bot的回调上下文

        Returns:
            包含角色信息的InlineQueryResult对象列表
        """
        query = update.inline_query
        if not query:
            logger.warning("角色处理器收到空查询")
            return []

        # 从查询中提取搜索词
        query_text = query.query.strip()
        search_term = ""

        # 解析查询："char [搜索词]"
        parts = query_text.split(" ", 1)
        if len(parts) > 1:
            search_term = parts[1].strip().lower()

        user_id = query.from_user.id
        logger.info(f"处理来自用户{user_id}的角色查询，搜索词：'{search_term}'")

        try:
            # 加载可用角色并处理错误
            character_names = self._load_characters()

            if not character_names:
                logger.warning("查询无可用角色")
                no_chars_result = self.create_no_results_result("", "角色")
                return [self.create_result_from_data(no_chars_result)]

            logger.debug(f"已加载{len(character_names)}个角色用于过滤")

            # 根据搜索词过滤角色
            filtered_characters = self._filter_characters(character_names, search_term)

            if not filtered_characters:
                logger.debug(f"没有角色匹配搜索词：'{search_term}'")
                no_match_result = self.create_no_results_result(search_term, "角色")
                return [self.create_result_from_data(no_match_result)]

            logger.debug(f"找到{len(filtered_characters)}个匹配的角色")

            # 为过滤后的角色创建结果
            results_data = []
            failed_results = 0

            for char_name in filtered_characters[:50]:  # 限制为50个结果
                try:
                    char_result_data = await self._create_character_result_data(
                        char_name
                    )
                    if char_result_data:
                        results_data.append(char_result_data)
                    else:
                        failed_results += 1
                        logger.warning(f"为角色创建结果失败：{char_name}")
                except Exception as e:
                    failed_results += 1
                    logger.error(f"为角色{char_name}创建结果时出错：{e}", exc_info=True)

            if failed_results > 0:
                logger.warning(f"为{failed_results}个角色创建结果失败")

            # 转换为InlineQueryResult对象
            results = self.create_results_from_data(results_data)

            logger.info(f"为用户{user_id}返回{len(results)}个角色结果")
            return results

        except InlineQueryError as e:
            logger.error(f"用户{user_id}的角色查询错误：{e}", exc_info=True)
            raise  # 重新抛出以由主调度器处理
        except Exception as e:
            logger.error(f"用户{user_id}角色查询中的意外错误：{e}", exc_info=True)
            raise InlineQueryError(
                "角色查询处理失败", error_type="query_processing", user_friendly=True
            )

    def _load_characters(self) -> List[str]:
        """
        加载可用角色列表并进行全面的错误处理。

        Returns:
            List[str]: 角色名称列表（不含文件扩展名）

        Raises:
            InlineQueryError: 如果角色加载严重失败
        """
        try:
            logger.debug("尝试加载角色列表")
            character_names = list_all_characters()
            if character_names is None:
                raise InlineQueryError(
                    "角色数据加载失败", error_type="data_access", user_friendly=True
                )

            logger.debug(f"成功加载{len(character_names)}个角色")
            return character_names

        except FileNotFoundError as e:
            logger.error(f"角色目录未找到：{e}", exc_info=True)
            raise InlineQueryError(
                "角色文件目录不存在", error_type="data_access", user_friendly=True
            )
        except PermissionError as e:
            logger.error(f"访问角色文件权限被拒绝：{e}", exc_info=True)
            raise InlineQueryError(
                "无权限访问角色文件", error_type="data_access", user_friendly=True
            )
        except Exception as e:
            logger.error(f"加载角色时发生意外错误：{e}", exc_info=True)
            raise InlineQueryError(
                "角色数据加载异常", error_type="data_access", user_friendly=True
            )

    def _filter_characters(
        self, character_names: List[str], search_term: str
    ) -> List[str]:
        """
        根据搜索词过滤角色。

        Args:
            character_names: 所有角色名称的列表
            search_term: 用于过滤的搜索词（不区分大小写）

        Returns:
            过滤后的角色名称列表
        """
        if not search_term:
            return character_names

        # 按角色名称过滤（不区分大小写的部分匹配）
        filtered = [name for name in character_names if search_term in name.lower()]

        logger.debug(
            f"将{len(character_names)}个角色过滤为{len(filtered)}个匹配项，搜索词：'{search_term}'"
        )
        return filtered

    async def _create_character_result_data(
        self, char_name: str
    ) -> Optional[InlineResultData]:
        """
        为角色创建 InlineResultData 并进行全面的错误处理。

        参数:
            char_name: 角色名称（不含扩展名）

        返回:
            角色的 InlineResultData，如果创建失败则返回 None
        """
        try:
            logger.debug(f"为角色创建结果数据：{char_name}")

            # 加载角色数据并处理错误
            char_data = load_char(f"{char_name}.json")

            if not char_data:
                logger.warning(f"角色无返回数据：{char_name}")
                return None

            # 验证角色数据结构
            if not isinstance(char_data, dict):
                logger.error(
                    f"{char_name}的角色数据格式无效：期望dict，得到{type(char_data)}"
                )
                return None

            # 提取角色信息并设置后备值
            display_name = char_data.get("name", char_name)
            description = char_data.get("description", "无描述信息")
            avatar_url = char_data.get("avatar", None)  # 用于潜在的缩略图支持

            # 验证提取的数据
            if not display_name:
                display_name = char_name
                logger.warning(f"角色{char_name}名称为空，使用文件名")

            if not description:
                description = "无描述信息"

            # 创建格式更好的结构化内容
            content_lines = [
                f"**🎭 角色信息：{display_name}**",
                "",
                f"**📝 描述：**",
                description,
                "",
                f"**🔧 文件名：** `{char_name}.json`",
                "",
                "💡 *这是角色信息预览，如需切换角色请在私聊中使用相应命令。*",
            ]

            # 创建增强格式的结果数据
            result_data = InlineResultData(
                id=f"char_{char_name}",
                title=self.format_title_with_emoji(f"角色: {display_name}", "🎭"),
                description=self.truncate_text(description, 80),
                content="\n".join(content_lines),
                thumb_url=(
                    avatar_url if avatar_url and avatar_url.startswith("http") else None
                ),
                parse_mode="Markdown",
            )

            logger.debug(f"成功为角色创建结果数据：{char_name}")
            return result_data

        except FileNotFoundError as e:
            logger.warning(f"角色文件未找到：{char_name}.json - {e}")
            return None
        except PermissionError as e:
            logger.error(f"读取角色文件{char_name}权限被拒绝：{e}")
            return None
        except Exception as e:
            logger.error(
                f"为角色{char_name}创建结果数据时发生意外错误：{e}", exc_info=True
            )
            return None
