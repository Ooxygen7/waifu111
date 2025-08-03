import asyncio
import logging
import random
from typing import Optional

from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes
from agent.llm_functions import generate_summary
from bot_core.models import User as UserModel, Conversation as ConversationModel, Group, GroupConfig
from bot_core.public_functions.error import BotError
from bot_core.public_functions.messages import (
    finalize_message,
    send_message,
    update_message,
)
from bot_core.repository import UserRepository, ConversationRepository
from bot_core.services import PromptService, ConversationService, SummaryService
from utils import db_utils as db
from utils import text_utils as txt
from utils.config_utils import get_api_multiple
from utils.db_utils import dialog_summary_add
from utils.LLM_utils import LLM, PromptsBuilder
from utils.text_utils import contains_nsfw
from utils.logging_utils import setup_logging
import bot_core.public_functions.frequency_manager as fm
setup_logging()
logger = logging.getLogger(__name__)

# 定义常量
PRIVATE = 'private'
GROUP = 'group'
USER = 'user'
ASSISTANT = 'assistant'
REPLY = 'reply'
KEYWORD = 'keyword'
RANDOM = 'random'


class Message:
    """
    表示消息的类。

    该类处理消息的原始文本和处理后的文本，根据标记类型进行特殊处理。
    """

    def __init__(self, msg_id, text, mark):
        """
        初始化消息对象。

        参数:
        id (int): 消息的唯一标识符。
        text (str): 消息的原始文本。
        mark (str): 消息类型标记，例如 'input' 或 'output'，用于确定文本处理方式。

        属性:
        id (int): 消息ID。
        text_raw (str): 消息的原始文本。
        text_processed (str): 处理后的文本，根据标记进行提取或转换。
        """
        # print(text)  # 调试语句：打印原始文本
        self.id = msg_id
        self.text_raw = text
        if mark == 'input':
            self.text_processed = txt.extract_special_control(text)[0] or text  # 对于输入消息，提取特殊控制内容
        elif mark == 'output':
            self.text_processed = txt.extract_tag_content(text, 'content')  # 对于输出消息，提取标签内容
            self.text_summary = txt.extract_tag_content(text, 'summary')
            self.text_comment = txt.extract_tag_content(text, 'comment')
        else:
            self.text_processed = text  # 默认情况下，使用原始文本




class GroupConv:
    """
    表示群组对话的类。
    该类管理群组中的对话逻辑，包括消息处理、提示构建和响应生成。
    """
    user: UserModel

    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        初始化群组对话对象。
        参数:
        update (Update): Telegram更新对象。
        context (ContextTypes.DEFAULT_TYPE): Telegram上下文对象。
        属性:
        ...
        """
        self.update = update
        self.context = context
        
        if not update.message or not update.message.chat or not update.message.from_user:
            raise BotError("GroupConv 初始化失败：缺少必要的 message, chat 或 from_user 对象。")

        group_id = update.message.chat.id
        group_name = db.group_name_get(group_id)
        self.group = Group(id=group_id, name=group_name or "")

        message_text = update.message.text or update.message.caption or ""
        self.input = Message(update.message.id, message_text, 'input')

        self.output = None
        self.prompt_obj = None
        self.placeholder = None
        
        group_config_data = db.group_config_get(group_id)
        if group_config_data:
            api, char, preset = group_config_data
            self.config = GroupConfig(api=api, char=char, preset=preset)
        else:
            self.config = GroupConfig()
        self.trigger = None
        
        # --- 重构：使用 UserRepository 获取用户 ---
        user_repo = UserRepository()
        user = user_repo.get_or_create_user(
            user_id=update.message.from_user.id,
            first_name=update.message.from_user.first_name or '',
            last_name=update.message.from_user.last_name or '',
            user_name=update.message.from_user.username or ''
        )
        if not user:
            raise BotError(f"无法在 GroupConv 中加载或创建用户 {update.message.from_user.id}")
        self.user = user

        self.id = db.conversation_group_get(self.group.id, self.user.id) or None
        
        self.images = self._extract_images()
        try:
            self.client = LLM(self.config.api, 'group')
        except ValueError as e:
            if "未找到名为" in str(e) and "的API配置" in str(e):
                # API配置不存在，向用户发送友好提示
                error_msg = f"❌ API配置错误\n\n当前配置的API '{self.config.api}' 不存在。\n\n请使用 /api 指令查看并切换到可用的API配置。"
                asyncio.create_task(send_message(self.context, self.group.id, error_msg))
                raise BotError(f"API配置 '{self.config.api}' 不存在") from e
            else:
                raise e
        
        self.conv_service = ConversationService(self.client, self.user, self.context)
        if not self.id:
            self.id = self.conv_service.create_group_conversation(self.group)

    def _extract_images(self) -> list:
        """
        从更新对象中提取图片的 file_id。
        返回值:
        list: 图片 file_id 列表，如果没有图片则返回空列表。
        """
        images = []
        if self.update.message and self.update.message.photo:
            # 获取图片，photo 是一个列表，按分辨率排序，取最高分辨率的图片
            photo = self.update.message.photo[-1] if self.update.message.photo else None
            if photo:
                images.append(photo.file_id)
        elif self.update.message and self.update.message.document:
            # 检查是否为图片类型的文档
            doc = self.update.message.document
            if doc.mime_type and doc.mime_type.startswith('image/'):
                images.append(doc.file_id)
        return images

    def set_trigger(self, trigger):
        """
        设置触发类型并构建提示字符串。
        参数:
        trigger (str): 触发类型，例如 'random' 或 'keyword'。
        副作用:
        更新 self.trigger、self.prompt 属性。
        """
        self.trigger = trigger


    async def response(self):
        """
        处理响应逻辑，包括发送占位消息和异步任务。
        该方法是异步的，用于Telegram机器人环境。
        副作用:
        发送占位消息并启动异步任务。
        """
        
        # 检查机器人是否有发送消息的权限
        
        try:
            if self.update.message:
                self.placeholder = await self.update.message.reply_text("思考中")
        except (BadRequest, TelegramError) as e:
            logger.warning(f"发送占位消息失败: {e}，跳过回复")
            return
        if self.trigger in ['random', 'keyword', '@']:
            logger.debug(f"触发了{self.trigger}")
            self.id = None  # 创建一次性响应任务
        else:
            if not self.id:
                self.id = self.conv_service.create_group_conversation(self.group) # 如果会话ID不存在，创建新会话
        _task = asyncio.create_task(self._response_to_user())  # 创建对话响应任务

    async def _response_to_user(self):
        """
        处理对话响应的异步逻辑。
        该方法是异步的，用于获取AI响应并更新对话状态。
        副作用:
        更新 self.output 和数据库记录。
        """
        try:
            if not self.config.preset or not self.config.char:
                logger.warning(f"群组 {self.group.id} 未配置 preset 或 char，跳过响应。")
                if self.placeholder:
                    await self.placeholder.edit_text("群组未配置机器人，无法回复。")
                return

            # --- 重构：使用 PromptService 构建提示 ---
            # 注意：GroupConv 还没有迁移到使用 Conversation 模型，因此我们暂时传入 self.id
            # 这将在后续步骤中被重构。
            import datetime
            temp_conv_for_service = ConversationModel(
                conv_id=self.id or 0,
                user_id=self.user.id,
                character="",
                preset="",
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now()
            )

            prompt_service = PromptService(
                user=self.user,
                input_text=self.input.text_raw,
                conversation=temp_conv_for_service,
                group=self.group,
                group_config=self.config
            )
            messages = prompt_service.build_group_chat_prompts(images=self.images)
            # --- 重构：使用 ConversationService 获取响应 ---
            conv_service = ConversationService(self.client, self.user, self.context, temp_conv_for_service)
            
            if self.images:
                await self.client.embedd_image(self.images, self.context)

            response_chunks = []
            async for chunk in conv_service.get_llm_response(messages):
                response_chunks.append(chunk)
            
            response = "".join(response_chunks)

            if self.placeholder:
                self.output = Message(self.placeholder.message_id, response, 'output')
                await finalize_message(self.placeholder, self.output.text_processed)
            
            if self.id:
                self.conv_service.save_group_turn(self.group, self.id, self.input, self.output, self.trigger)
        except Exception as e:
            logger.error(f"响应用户时发生异常: {e}", exc_info=True)
            error_text = f"❌ 出错了：{str(e)}"
            if self.placeholder:
                await finalize_message(self.placeholder, error_text)




class ConvManager:
    def __init__(self, chat_type):
        self.chat_type = chat_type


class PrivateConv:
    """
    处理私聊场景下的对话逻辑.
    该类负责管理用户的对话状态,包括构建提示(prompt),调用语言模型(LLM)生成回复,
    以及保存对话记录到数据库. 它支持流式和非流式两种回复模式,并提供撤销(undo),
    重生成(regen)等功能.
    Attributes:
        update (Update): Telegram API 传递的更新对象, 包含了用户发送的消息或回调查询.
        context (ContextTypes.DEFAULT_TYPE): Telegram Bot 的上下文对象, 用于与 Telegram API 交互.
        placeholder: 用于存储占位消息的对象, 在等待 LLM 回复时显示.
        user (UserModel): 用户模型对象.
        conversation (ConversationModel): 会话模型对象.
        input (Message): 用户输入的消息对象.
        output (Message): LLM 生成的回复消息对象.
    """
    user: UserModel
    conversation: ConversationModel

    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        初始化 PrivateConv 对象.
        根据传入的 update 对象判断用户发送的是消息还是回调查询,
        并初始化相应的属性,包括用户对象,输入消息,配置信息和会话 ID.
        如果会话 ID 不存在,则创建一个新的会话.
        Args:
            update (Update): Telegram API 传递的更新对象.
            context (ContextTypes.DEFAULT_TYPE): Telegram Bot 的上下文对象.
        """
        self.placeholder = None
        self.context = context
        self.update = update
        self.input = None
        self.output = None

        # --- 重构：从 context 获取 User 模型 ---
        if context.user_data and 'model' in context.user_data:
            user: Optional[UserModel] = context.user_data.get('model')
        else:
            # 如果在 context 中找不到，作为后备方案，从数据库加载
            if not update.effective_user:
                raise BotError("在 PrivateConv 中无法确定有效用户。")
            user_id = update.effective_user.id
            user_repo = UserRepository()
            user = user_repo.get_user_by_id(user_id)

        if not user:
            user_identifier = update.effective_user.id if update.effective_user else "未知"
            raise BotError(f"在 PrivateConv 中无法加载用户 {user_identifier} 的信息。")
        self.user = user

        # --- 重构：使用 ConversationRepository 加载或创建会话 ---
        conv_repo = ConversationRepository()
        if self.user.active_conversation_id:
            conversation = conv_repo.get_conversation_by_id(self.user.active_conversation_id)
        else:
            conversation = None

        if not conversation:
            conversation = conv_repo.create_private_conversation(self.user)
            if not conversation:
                raise BotError(f"无法为用户 {self.user.id} 创建新的会话。")
            # 更新 user model 的 active_conversation_id
            self.user.active_conversation_id = conversation.id
        
        self.conversation = conversation

        if update.message:
            self.input = Message(update.message.message_id, update.message.text or "", 'input')
        elif update.callback_query:
            # 回调查询没有 self.input，但需要 user 和 conversation 对象
            pass
        
        try:
            self.client = LLM(self.user.api, 'private')
        except ValueError as e:
            if "未找到名为" in str(e) and "的API配置" in str(e):
                # API配置不存在，向用户发送友好提示
                error_msg = f"❌ API配置错误\n\n当前配置的API '{self.user.api}' 不存在。\n\n请使用 /api 指令查看并切换到可用的API配置。"
                asyncio.create_task(send_message(self.context, self.user.id, error_msg))
                raise BotError(f"API配置 '{self.user.api}' 不存在") from e
            else:
                raise e
        
        # --- 重构：使用 Service 处理业务逻辑 ---
        summary_service = SummaryService(self.conversation)
        summary_service.check_and_generate_summaries_async()
        self.conv_service = ConversationService(self.client, self.user, self.context, self.conversation)

    async def response(self, save=True):
        """
        生成并发送 LLM 的回复.
        该方法首先发送一个占位消息,然后根据配置选择流式或非流式回复模式,
        并创建一个异步任务来处理 LLM 的回复.
        Args:
            save (bool, optional): 是否保存对话记录到数据库. 默认为 True.
        """
        if self.update.message and self.update.message.text and self.update.message.text.startswith('/'):
            logger.warning(f"检测到命令 {self.update.message.text} 进入消息处理器，已跳过")
            return
        if self.user.remain_frequency > 0 or self.user.temporary_frequency > 0:
            # 检查是否是从回调查询触发的
            if self.update.message:
                self.placeholder = await self.update.message.reply_text("思考中")
            else:
                # 如果是从回调查询触发的，直接发送新消息
                self.placeholder = await self.context.bot.send_message(chat_id=self.user.id, text="思考中")
            if self.input:
                logger.info(f"输入：{self.input.text_raw}")
            _task = asyncio.create_task(self._response_to_user(save))
        else:
            await send_message(self.context, self.user.id, "你的额度已用尽，联系 @xi_cuicui")

    async def regen(self):
        """
        重新生成 LLM 的回复.
        该方法将重生成操作委托给 ConversationService 处理。
        """
        if not (self.user.remain_frequency > 0 or self.user.temporary_frequency > 0):
            await send_message(self.context, self.user.id, "你的额度已用尽，联系 @xi_cuicui")
            return

        self.placeholder = await self.context.bot.send_message(chat_id=self.user.id, text="重新生成中...")
        
        # 调用服务层来处理重生成逻辑
        full_response, last_input_text = await self.conv_service.regenerate_response()

        if full_response is None or last_input_text is None:
            await finalize_message(self.placeholder, "❌ 重新生成失败，找不到足够的信息。")
            return

        # 服务层返回了响应，现在由控制器负责后续处理
        # 1. 更新 input 对象以用于保存
        self.input = Message(0, last_input_text, 'input') # msg_id 设为 0，因为它已被删除
        
        # 2. 创建 output 对象
        self.output = Message(self.placeholder.message_id, full_response, 'output')
        
        # 3. 更新并最终化占位消息
        await finalize_message(self.placeholder, self.output.text_processed, summary=self.output.text_summary, comment=self.output.text_comment)
        
        # 4. 保存新的对话记录
        self.conv_service.save_turn(self.input, self.output)

    async def undo(self):
        """
        撤销最后一次对话。
        该方法将撤销操作委托给 ConversationService 处理。
        """
        await self.conv_service.undo_last_turn()



    def set_callback_data(self, data):
        """
        设置回调数据.
        该方法用于处理回调查询,将回调数据设置为输入消息
        Args:
            data (str): 回调数据.
        """
        self.input = Message(0, data, 'callback')

    async def _response_to_user(self, save):
        """
        Args:
            save (bool): 是否保存对话记录到数据库.
        """
        last_update_time = asyncio.get_event_loop().time()
        last_updated_content = "..."
        response_chunks = []

        try:
            if not self.input:
                logger.warning("无法响应，因为没有输入消息。")
                return

            # --- 重构：使用 PromptService 构建提示 ---
            prompt_service = PromptService(user=self.user, conversation=self.conversation, input_text=self.input.text_raw)
            messages = prompt_service.build_private_chat_prompts()
            # --- 重构：使用 ConversationService 获取响应 ---
            async for chunk in self.conv_service.get_llm_response(messages):
                response_chunks.append(chunk)
                response = "".join(response_chunks)
                current_time = asyncio.get_event_loop().time()
                # 每 4 秒或内容显著变化时更新消息
                if current_time - last_update_time >= 4.0 and response != last_updated_content:
                    if self.placeholder:
                        await update_message(response, self.placeholder)
                    last_updated_content = response
                    last_update_time = current_time
                await asyncio.sleep(0.01)
            if self.placeholder:
                self.output = Message(self.placeholder.message_id, "".join(response_chunks), 'output')
                await finalize_message(self.placeholder, self.output.text_processed, summary=self.output.text_summary, comment=self.output.text_comment)
            else:
                self.output = Message(0, "".join(response_chunks), 'output') # Placeholder for message ID
            if contains_nsfw(self.output.text_processed) and self.user.preset == 'Default_meeting':
                await send_message(self.context, self.user.id, "检测到您正在使用默认配置，使用 `/preset` 切换nsfw配置可获得更好的nsfw内容质量")
            if save:
                self.conv_service.save_turn(self.input, self.output)
        except Exception as e:
            logger.error(f"响应用户时发生异常: {e}", exc_info=True)
            error_text = f"❌ 出错了：{str(e)}"
            if self.placeholder:
                await finalize_message(self.placeholder, error_text)





