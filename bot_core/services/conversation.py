import asyncio
import logging
import random
from types import SimpleNamespace
from typing import Optional, List, Dict, Any
from bot_core.models import User, Conversation
from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes
from bot_core.models import User as UserModel, Conversation as ConversationModel, Group, GroupConfig
from bot_core.services.utils.error import BotError
from bot_core.services.messages import (
    MessageFactory,
    send_message,
)
from bot_core.repository import UserRepository, ConversationRepository,GroupRepository
import bot_core.services.utils.usage as usage
from bot_core.services.utils.prompt import PromptService
from bot_core.services.utils.summary import SummaryService
from utils import db_utils as db
from utils import text_utils as txt
from utils.LLM_utils import LLM
from utils.text_utils import contains_nsfw
from utils.logging_utils import setup_logging
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

            factory = MessageFactory(update=self.update, context=self.context)
            if self.placeholder:
                self.output = Message(self.placeholder.message_id, response, 'output')
                await factory.edit(self.placeholder, self.output.text_processed)
            
            # 确保 self.output 被实例化
            if not self.output:
                self.output = Message(self.placeholder.message_id if self.placeholder else 0, response, 'output')

            # 无论是否存在会话ID，都更新 group_dialogs 表
            if self.trigger:
                db.group_dialog_response_update(
                    group_id=self.group.id,
                    msg_id=self.input.id,
                    trigger_type=self.trigger,
                    raw_response=self.output.text_raw,
                    processed_response=self.output.text_processed
                )
            else:
                logger.warning(f"无法更新 group_dialogs，因为 trigger 为 None。Group: {self.group.id}, Msg: {self.input.id}")

            # 如果存在会话ID，则保存到长期对话历史中
            if self.id:
                self.conv_service.save_group_turn(self.group, self.id, self.input, self.output, self.trigger, messages)
        except Exception as e:
            logger.error(f"响应用户时发生异常: {e}", exc_info=True)
            error_text = f"❌ 出错了：{str(e)}"
            if self.placeholder:
                factory = MessageFactory(update=self.update, context=self.context)
                await factory.edit(self.placeholder, error_text)




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

        # --- 修复：始终从数据库加载最新的用户数据以确保额度准确 ---
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
            await send_message(self.context, self.user.id, f"你的额度已用尽，\r\n当前额度：{self.user.remain_frequency}，临时额度：{self.user.temporary_frequency}\r\n若有疑问联系 @xi_cuicui")

    async def regen(self):
        """
        重新生成最后一次 LLM 的回复。
        此方法会撤销上一次对话，并使用之前的用户输入重新调用 LLM 生成流式响应。
        """
        factory = MessageFactory(update=self.update, context=self.context)
        if not (self.user.remain_frequency > 0 or self.user.temporary_frequency > 0):
            await send_message(self.context, self.user.id, f"你的额度已用尽，\n当前额度：{self.user.remain_frequency}，临时额度：{self.user.temporary_frequency}\n若有疑问联系 @xi_cuicui")
            return

        try:
            # 撤销上一回合，并获取上一回合的用户输入
            last_input_text = await self.conv_service.undo_last_turn()
            if last_input_text is None:
                await send_message(self.context, self.user.id, "❌ 重新生成失败，找不到上一条对话记录。")
                return

            # 设置占位消息
            self.placeholder = await self.context.bot.send_message(chat_id=self.user.id, text="重新生成中...")
            
            # 将上一轮的用户输入设置为当前输入
            self.input = Message(0, last_input_text, 'input') # msg_id 设为 0，因为它已被删除

            # 复用 _response_to_user 进行流式响应
            asyncio.create_task(self._response_to_user(save=True))

        except Exception as e:
            logger.error(f"重新生成响应时发生异常: {e}", exc_info=True)
            error_text = f"❌ 重新生成时出错了：{str(e)}"
            if self.placeholder:
                await factory.edit(self.placeholder, error_text)
            else:
                await send_message(self.context, self.user.id, error_text)

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
        factory = MessageFactory(update=self.update, context=self.context)

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
                        display_text = response
                        if len(display_text) > 4000:
                            display_text = display_text[:4000] + "..."
                        
                        try:
                            await self.placeholder.edit_text(display_text)
                        except TelegramError as e:
                            if "Message is not modified" not in str(e):
                                logger.warning(f"临时更新消息失败: {e}")
                    last_updated_content = response
                    last_update_time = current_time
                await asyncio.sleep(0.01)

            final_response_text = "".join(response_chunks)
            logger.info(f"AI原始回复: {final_response_text}")
            logger.info(f"AI原始回复长度: {len(final_response_text)}")

            if self.placeholder:
                self.output = Message(self.placeholder.message_id, final_response_text, 'output')
                logger.info(f"处理后的text_processed: {repr(self.output.text_processed)}")
                logger.info(f"处理后的text_summary: {repr(self.output.text_summary)}")
                logger.info(f"处理后的text_comment: {repr(self.output.text_comment)}")

                # 使用 MessageFactory.edit 进行最终更新，它会处理长消息分割和格式化
                await factory.edit(
                    placeholder=self.placeholder,
                    text=self.output.text_processed,
                    summary=self.output.text_summary,
                    comment=self.output.text_comment
                )
            else:
                self.output = Message(0, final_response_text, 'output') # Placeholder for message ID

            if contains_nsfw(self.output.text_raw) and self.user.preset == 'Default_meeting':
                await send_message(self.context, self.user.id, "检测到您正在使用默认配置，使用 `/preset` 切换nsfw配置可获得更好的nsfw内容质量")
            if save:
                self.conv_service.save_turn(self.input, self.output, messages)
        except Exception as e:
            logger.error(f"响应用户时发生异常: {e}", exc_info=True)
            error_text = f"❌ 出错了：{str(e)}"
            if self.placeholder:
                await factory.edit(self.placeholder, error_text)


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
        self.user_repo = UserRepository()
        self.group_repo = GroupRepository()

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

    async def undo_last_turn(self) -> Optional[str]:
        """
        撤销私聊中的最后一轮对话，并返回上一轮用户的输入文本。
        - 获取最后一次用户输入和消息ID。
        - 从 Telegram 删除消息。
        - 从数据库删除消息记录。
        - 返回上一次用户的输入文本，用于重新生成。
        """
        if not self.conversation or not self.conversation.id:
            logger.warning("无法撤销，因为没有活动的会话ID。")
            return None

        conv_id = self.conversation.id
        user_id = self.user.id

        # 1. 获取最后的用户输入和消息ID
        last_input_text = db.dialog_last_input_get(conv_id)
        msg_ids = db.conversation_latest_message_id_get(conv_id)
        msg_ids = [msg_id for msg_id in msg_ids if msg_id is not None]

        if not msg_ids:
            logger.warning(f"在会话 {conv_id} 中找不到可供撤销的消息。")
            return None # 返回 None 表示没有找到消息

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
        deleted_count = 0
        if len(msg_ids) >= 2:
            self.conv_repo.delete_message(conv_id, msg_ids[0]) # AI
            self.conv_repo.delete_message(conv_id, msg_ids[1]) # User
            deleted_count = 2
        elif len(msg_ids) == 1:
            self.conv_repo.delete_message(conv_id, msg_ids[0])
            deleted_count = 1

        if deleted_count > 0:
            logger.info(f"成功撤销了会话 {conv_id} 中的 {deleted_count} 条消息: {msg_ids}")
            # 更新轮次计数
            self.conversation.turns -= deleted_count
            self.conv_repo.update_conversation_turns(conv_id, self.conversation.turns)
        else:
            logger.warning(f"消息ID列表长度不足 (len={len(msg_ids)})，无法从数据库中删除记录。")

        return last_input_text

    def save_turn(self, input_message, output_message, messages: List[Dict[str, Any]]):
        """
        保存一轮完整的对话（用户输入和AI回复）到数据库。

        Args:
            input_message: 代表用户输入的 Message 对象。
            output_message: 代表AI输出的 Message 对象。
            messages: 发送给LLM的完整消息列表。
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

        # 将更新后的轮次计数持久化到数据库
        self.conv_repo.update_conversation_turns(self.conversation.id, self.conversation.turns)

        # 更新用户的使用统计信息，并获取返回的新额度
        updated_frequencies = usage.update_user_usage(self.user, messages, output_message.text_raw, 'private_chat')

        # --- 修复：如果成功获取新额度，则更新当前 User 模型 ---
        if updated_frequencies:
            self.user.remain_frequency, self.user.temporary_frequency = updated_frequencies
            logger.info(f"用户 {self.user.id} 的额度已在内存中更新: remain={self.user.remain_frequency}, temp={self.user.temporary_frequency}")

        logger.info(f"成功保存了会话 {self.conversation.id} 的第 {current_turn + 1} 和 {current_turn + 2} 轮。")

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
                logger.info(f"为用户 {self.user.id} 在群组 {group.id} 中创建了新的会话ID: {new_conv_id}")
                return new_conv_id

        logger.error(f"为用户 {self.user.id} 在群组 {group.id} 中创建会话ID失败，已达最大尝试次数。")
        return None

    def save_group_turn(self, group: Group, conv_id: int, input_message, output_message, trigger: Optional[str], messages: List[Dict[str, Any]]):
        """
        保存一轮完整的群组对话到数据库。

        Args:
            group: 当前群组模型。
            conv_id: 当前会话ID。
            input_message: 代表用户输入的 Message 对象。
            output_message: 代表AI输出的 Message 对象。
            trigger: 触发类型。
            messages: 发送给LLM的完整消息列表。
        """
        if not conv_id or not output_message:
            logger.warning("无法保存群聊记录：缺少 conv_id 或 output。")
            return

        # 1. 保存会话内容到 group_user_dialogs (用于长期对话上下文)
        # 注意：这与 group_dialogs 表不同，后者用于短期日志和上下文。
        turn = db.dialog_turn_get(conv_id, 'group')
        db.dialog_content_add(conv_id, 'user', turn + 1, input_message.text_raw, input_message.text_processed, chat_type='group')
        db.dialog_content_add(conv_id, 'assistant', turn + 2, output_message.text_raw, output_message.text_processed, chat_type='group')

        # 2. 更新群组会话的轮次和时间戳
        self.group_repo.update_group_conversation_turn(conv_id, turns_increase=2)

        # 3. 更新群组本身的统计数据和时间戳
        self.group_repo.update_group_stats(group.id, call_count_increase=1)

        # 4. 更新用户的统计数据和时间戳
        # 创建一个符合 frequency_manager 期望的复合对象
        group_context = SimpleNamespace(user=self.user, group=group)
        usage.update_user_usage(group_context, messages, output_message.text_raw, 'group_chat')

        # 5. 更新 group_dialogs 表中已存在的记录，补充AI回复和触发类型
        db.group_dialog_update(input_message.id, 'trigger_type', trigger, group.id)
        db.group_dialog_update(input_message.id, 'raw_response', output_message.text_raw, group.id)
        db.group_dialog_update(input_message.id, 'processed_response', output_message.text_processed, group.id)

        logger.info(f"成功更新了群组 {group.id} 在 group_dialogs 中的记录 (msg_id: {input_message.id})，并保存了会话。")


