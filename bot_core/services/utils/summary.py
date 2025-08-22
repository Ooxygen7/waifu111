import asyncio
import logging
from agent.llm_functions import generate_summary
from utils.db_utils import dialog_summary_add
logger = logging.getLogger(__name__)
from bot_core.data_repository.conv_model import Conversation


class SummaryService:
    """
    负责处理对话摘要的生成和管理。
    """

    def __init__(self, conversation: Conversation):
        """
        初始化 SummaryService。

        Args:
            conversation: 当前会话模型。
        """
        self.conversation = conversation

    def check_and_generate_summaries_async(self):
        """
        检查当前会话是否需要总结，并异步启动一个后台任务来补全所有缺失的摘要。
        """
        if not self.conversation.id:
            return
        logger.info(f"开始检查对话 {self.conversation.id} 的摘要情况。")
        logger.info(f"该对话当前轮次为 {self.conversation.turns} 轮。")
        if self.conversation.turns <= 60:
            logger.info("轮次不足 (<= 60)，跳过摘要检查。")
            return

        # 计算需要检查的总结区域数量
        area_count = (self.conversation.turns - 1) // 30
        summaries = self.conversation.summaries

        # 构建已存在的总结区域集合
        exist_areas = {s.get('summary_area') for s in summaries if s.get('summary_area')}

        # 确定需要补全的区域列表
        missing_areas = []
        for i in range(1, area_count + 1):
            start = (i - 1) * 30 + 1
            end = i * 30
            area_str = f"{start}-{end}"
            if area_str not in exist_areas:
                missing_areas.append((start, end, area_str))

        if not missing_areas:
            logger.info(f"对话 {self.conversation.id} 的所有摘要区域均已存在。")
            return

        logger.info(f"对话 {self.conversation.id} 发现缺失的摘要区域: {[a[2] for a in missing_areas]}，将启动后台任务依次补全。")

        async def generate_all_summaries():
            for start, end, area_str in missing_areas:
                result = await self._generate_summary(start, end)
                if not result:
                    logger.warning(f"区域 {area_str} 总结生成失败，后续区域将不再尝试。")
                    break

        # 启动后台任务
        asyncio.create_task(generate_all_summaries())

    async def _generate_summary(self, start: int, end: int) -> bool:
        """
        为指定区域的内容生成并添加 summary。

        Args:
            start (int): 区域起始轮次。
            end (int): 区域结束轮次。

        Returns:
            bool: 添加总结是否成功。
        """
        if not self.conversation.id:
            logger.error("无法生成摘要，因为没有会话ID。")
            return False

        area_str = f"{start}-{end}"
        max_retry = 4
        for attempt in range(1, max_retry + 1):
            try:
                summary_text = await generate_summary(self.conversation.id, summary_type='zip', start=start, end=end)

                if not summary_text or len(summary_text) < 200:
                    logger.warning(f"第 {attempt}/{max_retry} 次尝试：区域 {area_str} 生成的总结过短（<200字符），将重试。")
                    await asyncio.sleep(5)
                    continue

                result = dialog_summary_add(self.conversation.id, area_str, summary_text)
                if result:
                    logger.info(f"成功为区域 {area_str} 添加总结。")
                    return True
                else:
                    logger.warning(f"第 {attempt}/{max_retry} 次尝试：为区域 {area_str} 添加总结到数据库失败，将重试。")

            except Exception as e:
                logger.error(f"第 {attempt}/{max_retry} 次尝试为区域 {area_str} 生成或添加总结时出错: {e}", exc_info=True)

            if attempt < max_retry:
                await asyncio.sleep(5)

        logger.error(f"区域 {area_str} 总结生成失败，已达最大重试次数 {max_retry}。")
        return False








