import datetime
import logging
import json
import random
from typing import List, Dict, Any, Optional
from bot_core.data_repository.conv_model import User, Conversation, Group
from utils.LLM_utils import PromptsBuilder
import utils.db_utils as db
logger = logging.getLogger(__name__)

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
        if self.group:
            # 群聊中，优先使用 first_name + last_name
            user_display_name = f"{self.user.first_name or ''} {self.user.last_name or ''}".strip()
            if not user_display_name:
                user_display_name = self.user.user_name or self.user.nick or "未知用户"
        else:
            # 私聊中，保持原有逻辑
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
        logger.debug(f"Final private chat messages for LLM: {json.dumps(self.prompt_builder.messages, indent=2, ensure_ascii=False)}")
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


        if images:
            image_prompt = "<image_input>\r\n用户发送了图片，请仔细查看图片内容并根据图片内容回复。\r\n</image_input>\r\n"
            self.prompt_builder.insert_any({"location":"input_mark_start","mode":"before","content":f"{image_prompt}"})

        self.prompt_builder.insert_any({"location":"input_mark_start","mode":"before","content":f"<群聊模式>\r\n现在的时间是{str(datetime.datetime.now())}\r\n"
                                                                                                f"我们正处于群聊模式，你需要先看看群友在聊什么，再加入他们的对话\r\n{group_dialog}\r\n</群聊模式>"})
        self.prompt_builder.insert_any({"location":"input_mark_end","mode":"after","content":profile_prompt})

        # 4. 构建最终消息
        self.prompt_builder.build_openai_messages()
        logger.debug(f"Final group chat messages for LLM: {json.dumps(self.prompt_builder.messages, indent=2, ensure_ascii=False)}")
        return self.prompt_builder.messages
