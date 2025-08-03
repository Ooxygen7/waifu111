import asyncio
import logging
from agent.llm_functions import generate_summary
from utils.db_utils import dialog_summary_add

logger = logging.getLogger(__name__)
import random
from typing import List, Dict, Any, Optional
from telegram.ext import ContextTypes
from bot_core.models import User, Conversation, Group
from bot_core.repository import ConversationRepository
from bot_core.public_functions.error import BotError
from utils.LLM_utils import PromptsBuilder
import utils.db_utils as db

class PromptService:
    """
    负责构建和管理与语言模型交互的提示。
    """

    def __init__(self, user: User, input_text: str, conversation: Optional[Conversation] = None, group: Optional[Group] = None, group_config: Optional[Any] = None):
        """
        初始化 PromptService。

        Args:
            user: 当前用户模型。
            input_text: 用户的原始输入文本。
            conversation: 当前私聊会话模型 (可选)。
            group: 当前群组模型 (可选)。
            group_config: 当前群组配置 (可选)。
        """
        self.user = user
        self.input_text = input_text
        self.conversation = conversation
        self.group = group
        self.group_config = group_config

        # 根据上下文确定 preset 和 character
        if group and self.group_config:
            preset = self.group_config.preset
            character = self.group_config.char
        else:
            preset = self.user.preset
            character = self.user.character

        # 确定用户昵称的备用逻辑
        user_display_name = self.user.nick or self.user.user_name or self.user.first_name

        self.prompt_builder = PromptsBuilder(
            prompts_set=preset,
            input_txt=self.input_text,
            character=character,
            user_nick=user_display_name
        )

    def build_private_chat_prompts(self) -> List[Dict[str, Any]]:
        """
        为私聊场景构建最终的 OpenAI 消息列表。
        """
        if not self.conversation:
            raise ValueError("私聊场景需要提供 conversation 对象。")

        # 1. 加载历史消息
        if self.conversation.id:
            # 注意：这里的 build_conv_messages 仍然依赖 db_utils，
            # 在未来的重构中，可以考虑将其逻辑也移入 Repository 或 Service。
            self.prompt_builder.build_conv_messages(self.conversation.id, "private")

        # 2. 插入会话摘要
        if self.conversation.summaries:
            summary_content = "\n".join([s['content'] for s in self.conversation.summaries])
            self.prompt_builder.insert_summary(summary_content)

        # 3. 构建最终消息
        self.prompt_builder.build_openai_messages()
        return self.prompt_builder.messages

    def build_group_chat_prompts(self, images: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        为群聊场景构建最终的 OpenAI 消息列表。

        Args:
            images: 附加的图片 file_id 列表 (可选)。
        """
        if not self.group or not self.conversation:
            raise ValueError("群聊场景需要提供 group 和 conversation 对象。")

        # 1. 加载群聊历史
        self.prompt_builder.build_conv_messages(self.conversation.id, "group")

        # 2. 加载并插入群聊上下文和用户画像
        group_dialog = self.prompt_builder.load_group_dialog(self.group.id)
        user_profiles = db.user_profile_get(self.user.id)
        
        profile_prompt = ""
        if user_profiles:
            current_group_profile = next((p['user_profile'] for p in user_profiles if p['group_id'] == self.group.id), None)
            if current_group_profile:
                profile_prompt = f"<用户信息>\r\n这是根据用户在群聊中的发言，为他总结的用户画像，请在回复时参考：\r\n{current_group_profile}\r\n</用户信息>\r\n"
            else:
                random_profile = random.choice(user_profiles)
                profile_prompt = f"<用户信息>\r\n这是根据用户在其他群聊中的发言，为他总结的用户画像，请在回复时参考：\r\n{random_profile['user_profile']}\r\n</用户信息>\r\n"

        # 3. 根据有无图片插入不同的提示
        if images:
            image_prompt = "<image_input>\r\n用户发送了图片，请仔细查看图片内容并根据图片内容回复。\r\n</image_input>\r\n"
            self.prompt_builder.insert_any({"location":"input_mark_start","mode":"before","content":f"{image_prompt}"})
        
        self.prompt_builder.insert_any({"location":"input_mark_start","mode":"before","content":f"<群聊模式>\r\n现在是群聊模式，你需要先看看群友在聊什么，再加入他们的对话\r\n{group_dialog}\r\n</群聊模式>"})
        self.prompt_builder.insert_any({"location":"input_mark_end","mode":"after","content":profile_prompt})

        # 4. 构建最终消息
        self.prompt_builder.build_openai_messages()
        return self.prompt_builder.messages


class ConversationService:
    """
    负责编排整个对话流程，包括与LLM的交互和响应处理。
    """

    def __init__(self, llm_client: Any, user: User, context: ContextTypes.DEFAULT_TYPE, conversation: Optional[Conversation] = None):
        """
        初始化 ConversationService。

        Args:
            llm_client: 配置好的 LLM 客户端实例。
            user: 当前用户模型。
            context: Telegram Bot 的上下文对象。
            conversation: 当前会话模型 (可选)。
        """
        self.llm_client = llm_client
        self.user = user
        self.context = context
        self.conversation = conversation
        self.conv_repo = ConversationRepository()

    async def get_llm_response(self, messages: List[Dict[str, Any]]):
        """
        设置消息并异步获取 LLM 的流式响应。

        Args:
            messages: 发送给 LLM 的消息列表。

        Yields:
            str: 从 LLM 返回的响应内容块。
        """
        self.llm_client.set_messages(messages)
        async for chunk in self.llm_client.response(self.user.stream):
            yield chunk

    async def undo_last_turn(self):
        """
        撤销私聊中的最后一轮对话。
        - 从数据库获取最新消息ID。
        - 从 Telegram 删除消息。
        - 从数据库删除消息记录。
        """
        if not self.conversation or not self.conversation.id:
            logger.warning("无法撤销，因为没有活动的会话ID。")
            return

        conv_id = self.conversation.id
        user_id = self.user.id

        # 1. 从数据库获取最新消息ID
        # 注意：旧的 db_utils 调用将被替换
        msg_ids = db.conversation_latest_message_id_get(conv_id)
        msg_ids = [msg_id for msg_id in msg_ids if msg_id is not None]

        if not msg_ids:
            logger.warning(f"在会话 {conv_id} 中找不到可供撤销的消息。")
            return

        # 2. 从 Telegram 删除消息
        try:
            await self.context.bot.delete_messages(user_id, msg_ids)
        except Exception as e:
            logger.warning(f"批量删除消息失败: {e}，将尝试逐个删除。")
            for msg_id in msg_ids:
                try:
                    await self.context.bot.delete_message(user_id, msg_id)
                except Exception as e2:
                    logger.error(f"删除消息 {msg_id} 失败: {e2}")

        # 3. 从数据库删除消息记录
        if len(msg_ids) >= 2:
            # 使用 Repository 删除
            self.conv_repo.delete_message(conv_id, msg_ids[0])
            self.conv_repo.delete_message(conv_id, msg_ids[1])
            logger.info(f"成功撤销了会话 {conv_id} 中的消息: {msg_ids}")
        elif len(msg_ids) == 1:
            self.conv_repo.delete_message(conv_id, msg_ids[0])
            logger.info(f"成功撤销了会话 {conv_id} 中的消息: {msg_ids}")
        else:
            logger.warning(f"消息ID列表长度不足 (len={len(msg_ids)})，无法从数据库中删除记录。")

    async def regenerate_response(self):
        """
        重新生成最后一轮的回复。
        - 获取最后一次用户输入。
        - 从 Telegram 删除最后一则 AI 回复。
        - 从数据库删除最后一轮对话（用户输入和 AI 回复）。
        - 基于之前的用户输入重新生成响应。
        """
        if not self.conversation or not self.conversation.id:
            logger.warning("无法重新生成，因为没有活动的会话ID。")
            return None, None

        conv_id = self.conversation.id
        user_id = self.user.id

        # 1. 获取最后的用户输入和消息ID
        last_input_text = db.dialog_last_input_get(conv_id)
        msg_ids = db.conversation_latest_message_id_get(conv_id)
        
        # 清理 None 值
        msg_ids = [msg_id for msg_id in msg_ids if msg_id is not None]

        if not last_input_text or not msg_ids:
            logger.warning(f"无法为会话 {conv_id} 重新生成，因为找不到足够的信息（输入或消息ID）。")
            return None, None

        # 2. 从 Telegram 删除最后一则 AI 回复
        try:
            # msg_ids[0] 是最新的消息，即 AI 的回复
            await self.context.bot.delete_message(user_id, msg_ids[0])
        except Exception as e:
            logger.error(f"为重新生成而删除消息 {msg_ids[0]} 失败: {e}")
            # 即使删除失败，也继续尝试从数据库中清理并重新生成

        # 3. 从数据库删除最后一轮对话（用户和AI）
        if len(msg_ids) >= 2:
            self.conv_repo.delete_message(conv_id, msg_ids[0]) # AI
            self.conv_repo.delete_message(conv_id, msg_ids[1]) # User
        elif len(msg_ids) == 1:
            self.conv_repo.delete_message(conv_id, msg_ids[0]) # AI

        # 4. 使用 PromptService 构建新的提示
        prompt_service = PromptService(
            user=self.user,
            conversation=self.conversation,
            input_text=last_input_text
        )
        messages = prompt_service.build_private_chat_prompts()

        # 5. 使用 get_llm_response 获取新响应
        response_chunks = []
        async for chunk in self.get_llm_response(messages):
            response_chunks.append(chunk)
        
        full_response = "".join(response_chunks)
        
        # 6. 返回响应文本和最后的用户输入
        return full_response, last_input_text

    def save_turn(self, input_message, output_message):
        """
        保存一轮完整的对话（用户输入和AI回复）到数据库。

        Args:
            input_message: 代表用户输入的 Message 对象。
            output_message: 代表AI输出的 Message 对象。
        """
        if not self.conversation or not self.conversation.id:
            logger.warning("无法保存对话回合：缺少会话或会话ID。")
            return

        if not input_message or not output_message:
            logger.warning("无法保存对话回合：缺少输入或输出消息。")
            return

        if output_message.text_raw.startswith('API调用失败'):
            logger.warning("API调用失败，跳过保存。")
            return
        
        # 获取最新的轮次，然后加1和2
        # 注意：这里我们依赖 Conversation 模型中的 turns 属性，
        # 该属性应在加载时由 Repository 正确填充。
        current_turn = self.conversation.turns
        
        self.conv_repo.add_message(
            self.conversation.id,
            'user',
            current_turn + 1,
            input_message.text_raw,
            input_message.text_processed,
            input_message.id
        )
        self.conv_repo.add_message(
            self.conversation.id,
            'assistant',
            current_turn + 2,
            output_message.text_raw,
            output_message.text_processed,
            output_message.id
        )
        
        # 更新模型中的轮次计数，以保持同步
        self.conversation.turns += 2
        
        logger.info(f"成功保存了会话 {self.conversation.id} 的第 {current_turn + 1} 和 {current_turn + 2} 轮。")
        # TODO: 在这里处理使用频率和余额的更新逻辑

    def create_group_conversation(self, group: Group) -> Optional[int]:
        """
        为指定用户在群组中创建一个新的一次性或持久性会话。

        Args:
            group: 当前群组模型。

        Returns:
            新的会话ID，如果创建失败则返回 None。
        """
        max_attempts = 5
        for _ in range(max_attempts):
            new_conv_id = random.randint(10000000, 99999999)
            if db.conversation_group_create(
                new_conv_id,
                self.user.id,
                self.user.user_name or '',
                group.id,
                group.name or ''
            ):
                logger.debug(f"为用户 {self.user.id} 在群组 {group.id} 中创建了新的会话ID: {new_conv_id}")
                return new_conv_id
        
        logger.error(f"为用户 {self.user.id} 在群组 {group.id} 中创建会话ID失败，已达最大尝试次数。")
        return None

    def save_group_turn(self, group: Group, conv_id: int, input_message, output_message, trigger: Optional[str]):
        """
        保存一轮完整的群组对话到数据库。

        Args:
            group: 当前群组模型。
            conv_id: 当前会话ID。
            input_message: 代表用户输入的 Message 对象。
            output_message: 代表AI输出的 Message 对象。
            trigger: 触发类型。
        """
        if not conv_id or not output_message:
            logger.warning("无法保存群聊记录：缺少 conv_id 或 output。")
            return

        turn = db.dialog_turn_get(conv_id, 'group')
        db.dialog_content_add(conv_id, 'user', turn + 1, input_message.text_raw, input_message.text_processed,
                              input_message.id, 'group')
        db.dialog_content_add(conv_id, 'assistant', turn + 2, output_message.text_raw, output_message.text_processed,
                              output_message.id, 'group')
        
        # 更新 group_dialogs 表
        db.group_dialog_update(input_message.id, 'trigger_type', trigger, group.id)
        db.group_dialog_update(input_message.id, 'raw_response', output_message.text_raw, group.id)
        db.group_dialog_update(input_message.id, 'processed_response', output_message.text_processed, group.id)
        
        logger.info(f"成功保存了群组 {group.id} 会话 {conv_id} 的一轮对话。")
        # TODO: 重构 update_user_usage

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
        logger.debug(f"开始检查对话 {self.conversation.id} 的摘要情况。")
        logger.debug(f"该对话当前轮次为 {self.conversation.turns} 轮。")
        if self.conversation.turns <= 60:
            logger.debug("轮次不足 (<= 60)，跳过摘要检查。")
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
            logger.debug(f"对话 {self.conversation.id} 的所有摘要区域均已存在。")
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








