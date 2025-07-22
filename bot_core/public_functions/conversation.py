import asyncio
import logging
import random

from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from bot_core.public_functions.error import BotError
from bot_core.public_functions.messages import (
    finalize_message,
    send_message,
    update_message,
)
from utils import db_utils as db
from utils import text_utils as txt
from utils.config_utils import get_api_multiple
from utils.db_utils import dialog_summary_add
from utils.LLM_utils import LLM, PromptsBuilder
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


class User:
    """
    表示一个用户的类。

    该类用于存储用户的基本信息，如ID和昵称。
    """

    def __init__(self, user_id):
        """
        初始化用户对象。

        参数:
        user_id (int or str): 用户的唯一标识符。

        属性:
        id (int or str): 用户ID。
        nick (str): 用户昵称，从数据库中获取。
        """
        self.id = user_id
        self.nick = db.user_config_get(user_id).get('user_nick')  # 从数据库获取用户昵称
        self.frequency = db.user_info_get(user_id).get('remain')
        self.tmp_frequency = db.user_sign_info_get(user_id).get('frequency')


class GroupUser:
    """
    表示群组中用户的类。

    该类从Telegram更新对象中提取用户信息。
    """

    def __init__(self, update: Update):
        """
        初始化群组用户对象。

        参数:
        update (Update): Telegram更新对象，包含用户信息。

        属性:
        id (int): 用户ID。
        first_name (str): 用户名（如果存在，否则为空字符串）。
        last_name (str): 用户姓氏（如果存在，否则为空字符串）。
        username (str): 用户Telegram用户名（如果存在，否则为空字符串）。
        user_name (str): 组合后的全名（first_name + last_name）。
        """
        self.id = update.message.from_user.id
        self.first_name = update.message.from_user.first_name or ""
        self.last_name = update.message.from_user.last_name or ""
        self.username = update.message.from_user.username or ""
        self.user_name = self.first_name + ' ' + self.last_name  # 组合全名


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
        else:
            self.text_processed = text  # 默认情况下，使用原始文本


class Config:
    """
    表示用户配置的类。

    该类从数据库中加载用户的API、字符设置、预设和流设置。
    """

    def __init__(self, user_id):
        """
        初始化配置对象。

        参数:
        user_id (int or str): 用户的唯一标识符。

        属性:
        api (str): 用户的API配置，从数据库获取。
        char (str): 用户的字符设置。
        preset (str): 用户的预设配置。
        stream (bool): 用户的流式处理设置。
        multiple (int or bool): API的多路复用设置，从文件中获取。
        """
        self.api = db.user_api_get(user_id)
        info = db.user_config_get(user_id)
        self.char, self.preset = info.get('char'), info.get('preset')
        self.stream = db.user_stream_get(user_id)
        self.multiple = get_api_multiple(self.api)  # 从文件中获取API倍率信息


class Group:
    """
    表示群组的类。

    该类存储群组的基本信息，如ID和名称。
    """

    def __init__(self, group_id):
        """
        初始化群组对象。

        参数:
        group_id (int): 群组的唯一标识符。

        属性:
        id (int): 群组ID。
        name (str): 群组名称，从数据库获取。
        """
        self.id = group_id
        self.name = db.group_name_get(group_id)  # 从数据库获取群组名称


class GroupConfig:
    """
    表示群组配置的类。

    该类从数据库中加载群组的API、字符设置和预设。
    """

    def __init__(self, group_id):
        """
        初始化群组配置对象。

        参数:
        group_id (int): 群组的唯一标识符。

        属性:
        api (str): 群组的API配置。
        char (str): 群组的字符设置。
        preset (str): 群组的预设配置。
        """
        self.api, self.char, self.preset = db.group_config_get(group_id)  # 从数据库获取配置


class GroupConv:
    """
    表示群组对话的类。
    该类管理群组中的对话逻辑，包括消息处理、提示构建和响应生成。
    """

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
        self.group = Group(update.message.chat.id)  # 创建关联的群组对象

        # 检查文本内容，优先检查 text，如果没有则检查 caption
        message_text = update.message.text or update.message.caption or ""
        self.input = Message(self.update.message.id, message_text, 'input')  # 创建输入消息对象

        self.output = None
        self.prompt_obj = None
        self.placeholder = None
        self.config = GroupConfig(update.message.chat.id)  # 创建群组配置对象
        self.trigger = None
        self.user = GroupUser(update)  # 创建用户对象
        self.id = db.conversation_group_get(self.group.id, self.user.id) or None  # 从数据库获取会话ID
        if not self.id:
            self._new()
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

    def _extract_images(self) -> list:
        """
        从更新对象中提取图片的 file_id。
        返回值:
        list: 图片 file_id 列表，如果没有图片则返回空列表。
        """
        images = []
        if self.update.message.photo:
            # 获取图片，photo 是一个列表，按分辨率排序，取最高分辨率的图片
            photo = self.update.message.photo[-1] if self.update.message.photo else None
            if photo:
                images.append(photo.file_id)
        elif self.update.message.document:
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
            self.placeholder = await self.update.message.reply_text("思考中")  # 发送占位消息
        except (BadRequest, TelegramError) as e:
            logger.warning(f"发送占位消息失败: {e}，跳过回复")
            return
        if self.trigger in ['random', 'keyword', '@']:
            logger.debug(f"触发了{self.trigger}")
            self.id = None  # 创建一次性响应任务
        else:
            if not self.id:
                self._new()  # 如果会话ID不存在，创建新会话
        _task = asyncio.create_task(self._response_to_user())  # 创建对话响应任务

    async def _response_to_user(self):
        """
        处理对话响应的异步逻辑。
        该方法是异步的，用于获取AI响应并更新对话状态。
        副作用:
        更新 self.output 和数据库记录。
        """
        try:
            self.prompt_obj = PromptsBuilder(self.config.preset,self.input.text_raw,self.config.char,self.user.user_name)
            self.prompt_obj.build_conv_messages(self.id,"group")
            group_dialog = self.prompt_obj.load_group_dialog(self.group.id)

            if self.images:               
                image_prompt = "<image_input>\r\n用户发送了图片，请仔细查看图片内容并根据图片内容回复。\r\n</image_input>\r\n"
                self.prompt_obj.insert_any({"location":"input_mark_start","mode":"before","content":f"{image_prompt}"})
                self.prompt_obj.insert_any({"location":"input_mark_start","mode":"before","content":f"<群聊模式>\r\n现在是群聊模式，你需要先看看群友在聊什么，再加入他们的对话\r\n"
                                                                                                    f"{group_dialog}\r\n</群聊模式>"})
                self.prompt_obj.build_openai_messages()
                self.client.set_messages(self.prompt_obj.messages)
                await self.client.embedd_image(self.images,self.context)
            else:
                self.prompt_obj.insert_any({"location":"input_mark_start","mode":"before","content":f"<群聊模式>\r\n现在是群聊模式，你需要先看看群友在聊什么，再加入他们的对话\r\n"
                                                                                                    f"{group_dialog}\r\n</群聊模式>"})
                self.prompt_obj.build_openai_messages()
                self.client.set_messages(self.prompt_obj.messages)

            response = await self.client.final_response()
            self.output = Message(self.placeholder.message_id, response, 'output')  # 创建输出消息对象
            await finalize_message(self.placeholder, self.output.text_processed)  # 完成消息处理
            self._update_usage_info()  # 更新使用信息
        except Exception as e:
            logger.error(f"响应用户时发生异常: {e}", exc_info=True)
            # 反馈错误到TG
            error_text = f"❌ 出错了：{str(e)}"
            await finalize_message(self.placeholder, error_text)

    def _new(self):
        """
        创建一个新的会话ID。
        该方法尝试多次创建唯一ID，如果失败则抛出异常。
        返回值:
        无，直接更新 self.id。
        异常:
        ValueError: 如果创建失败。
        """
        max_attempts = 5  # 限制尝试次数
        for _ in range(max_attempts):
            new_conv_id = random.randint(10000000, 99999999)  # 生成随机ID
            if db.conversation_group_create(new_conv_id, self.user.id, self.user.user_name, self.group.id,
                                            self.group.name):
                self.id = new_conv_id
                logger.debug(f"New conversation ID: {new_conv_id}")
                return
        raise ValueError(f"无法创建会话ID，经过{max_attempts}次尝试")  # 抛出异常

    def _update_usage_info(self):
        """
        更新使用信息，包括令牌计数和数据库记录。
        副作用:
        更新数据库中的群组信息、对话内容和令牌统计。
        """
        print("正在保存群聊记录")  # 打印日志
        db.group_info_update(self.group.id, 'call_count', 1, True)  # 更新调用计数
        input_token = self.client.calculate_token_count(str(self.client.messages))
        logger.debug(f"输入令牌:{input_token}")  # 计算对话令牌
        turn = db.dialog_turn_get(self.id, 'group')  # 获取当前回合
        db.dialog_content_add(self.id, USER, turn + 1, self.input.text_raw, self.input.text_processed,
                              self.input.id, GROUP)  # 添加用户对话
        db.dialog_content_add(self.id, ASSISTANT, turn + 2, self.output.text_raw, self.output.text_processed,
                              self.output.id, GROUP)  # 添加助手对话
        db.conversation_group_update(self.group.id, self.user.id, 'turns', 1)  # 更新回合数
        output_token = self.client.calculate_token_count(self.output.text_raw)  # 计算输出令牌
        db.group_info_update(self.group.id, 'input_token', input_token, True)  # 更新输入令牌
        db.group_info_update(self.group.id, 'output_token', output_token, True)  # 更新输出令牌
        logger.debug(f"输出令牌:{output_token}")
        db.group_dialog_update(self.input.id, 'trigger_type', self.trigger, self.group.id)  # 更新触发类型
        db.group_dialog_update(self.input.id, 'raw_response', self.output.text_raw, self.group.id)  # 更新原始响应
        db.group_dialog_update(self.input.id, 'processed_response', self.output.text_processed,
                               self.group.id)  # 更新处理后响应


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
        user (User): 用户对象, 包含用户的 ID 等信息.
        input (Message): 用户输入的消息对象.
        output (Message): LLM 生成的回复消息对象.
        config (Config): 配置对象, 包含与用户相关的配置信息, 如角色,预设等.
        id (int): 会话 ID, 用于在数据库中标识会话.
    """

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
        self.placeholder = None  # 用于存储占位消息
        self.context = context
        self.update = update
        self.input = None
        self.output = None
        # 根据 update 类型初始化用户和输入消息
        if update.message:
            self.user = User(update.message.chat.id)
            self.input = Message(update.message.message_id, update.message.text, 'input') or None  # 消息内容
        else:
            self.user = User(update.callback_query.from_user.id)
        # 获取或创建会话 ID
        self.id = db.user_conv_id_get(self.user.id)
        self.summary = db.dialog_summary_get(self.id) or []
        self.turn = db.dialog_turn_get(self.id, 'private')
        self.config = Config(self.user.id)
        try:
            self.client = LLM(self.config.api, 'private')
        except ValueError as e:
            if "未找到名为" in str(e) and "的API配置" in str(e):
                # API配置不存在，向用户发送友好提示
                error_msg = f"❌ API配置错误\n\n当前配置的API '{self.config.api}' 不存在。\n\n请使用 /api 指令查看并切换到可用的API配置。"
                asyncio.create_task(send_message(self.context, self.user.id, error_msg))
                raise BotError(f"API配置 '{self.config.api}' 不存在") from e
            else:
                raise e
        if not self.id:
            self.new()
        asyncio.create_task(self._check_summary())

    async def response(self, save=True):
        """
        生成并发送 LLM 的回复.
        该方法首先发送一个占位消息,然后根据配置选择流式或非流式回复模式,
        并创建一个异步任务来处理 LLM 的回复.
        Args:
            save (bool, optional): 是否保存对话记录到数据库. 默认为 True.
        """
        if self.user.frequency > 0 or self.user.tmp_frequency > 0:
            # 检查是否是从回调查询触发的
            if self.update.message:
                self.placeholder = await self.update.message.reply_text("思考中")
            else:
                # 如果是从回调查询触发的，直接发送新消息
                self.placeholder = await self.context.bot.send_message(chat_id=self.user.id, text="思考中")
            logger.info(f"输入：{self.input.text_raw}")
            _task = asyncio.create_task(self._response_to_user(save))
        else:
            await send_message(self.context, self.user.id, "你的额度已用尽，联系 @xi_cuicui")

    async def regen(self):
        """
        重新生成 LLM 的回复.
        该方法首先获取最后一条消息的 ID,然后从数据库中删除该消息及其回复,
        并重新构建 prompt,最后调用 response 方法生成新的回复.
        """
        last_msg_id_list = db.conversation_latest_message_id_get(self.id)
        last_input = db.dialog_last_input_get(self.id)
        db.conversation_delete_messages(self.id, last_msg_id_list[0])
        db.conversation_delete_messages(self.id, last_msg_id_list[1])
        self.input = Message(last_msg_id_list[1], last_input, 'input')
        await self.context.bot.delete_message(self.user.id, last_msg_id_list[0])
        await self.response()

    async def undo(self):
        """
        撤销最后一次对话.
        该方法首先获取最后两条消息的 ID,然后从 Telegram 中删除这些消息,
        并从数据库中删除相应的对话记录. 如果删除消息失败,会尝试逐个删除.
        """
        msg_list = db.conversation_latest_message_id_get(self.id)
        msg_list = [msg_id for msg_id in msg_list if msg_id is not None]  # 过滤掉 None 值
        try:
            await self.context.bot.delete_messages(self.user.id, msg_list)
        except Exception as e:
            logger.warning(f"批量删除消息失败: {str(e)}, 尝试逐个删除")
            # 尝试逐个删除消息
            for msg_id in msg_list:
                if msg_id:  # 检查 msg_id 是否为空
                    try:
                        await self.context.bot.delete_message(self.user.id, msg_id)
                    except Exception as e2:
                        logger.error(f"删除消息 {msg_id} 失败: {str(e2)}")
                else:
                    logger.warning("尝试删除空消息 ID，已跳过")
        # 删除数据库记录
        if len(msg_list) >= 2:  # 确保 msg_list 至少有两个元素
            db.conversation_delete_messages(self.id, msg_list[0])
            db.conversation_delete_messages(self.id, msg_list[1])
        else:
            logger.warning(f"msg_list 长度不足 (len={len(msg_list)})，无法删除数据库记录")

    def new(self):
        """
        创建一个新的会话.
        该方法生成一个随机的会话 ID,并在数据库中创建新的会话记录.
        如果创建失败,会尝试多次,直到成功或达到最大尝试次数.
        """
        max_attempts = 5  # 限制尝试次数，避免无限循环
        for _ in range(max_attempts):
            new_conv_id = random.randint(10000000, 99999999)
            if (db.conversation_private_create(new_conv_id, self.user.id, self.config.char,
                                               self.config.preset) and
                    db.user_config_arg_update(self.user.id, 'conv_id', new_conv_id)):
                db.user_info_update(self.user.id, 'conversations', 1, True)
                self.id = new_conv_id
                return
        raise ValueError(f"无法创建会话ID，经过{max_attempts}次尝试")

    async def _save(self):
        """
        保存对话记录到数据库.
        该方法首先检查 LLM 的回复是否出错,如果没有出错,则将对话内容保存到数据库,
        并更新用户的使用信息.
        """
        if not self.output.text_raw.startswith('API调用失败'):
            self._save_turn_content_to_db()
            await self._update_usage_info()

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
            self.prompt_obj = PromptsBuilder(self.config.preset,self.input.text_raw,self.config.char,self.user.nick)
            self.prompt_obj.build_conv_messages(self.id,"private")
            if self.summary :
                logger.debug(f"该对话有{len(self.summary)}个大总结")
                logger.debug(f"{(len(self.summary)-1)*30}轮之前的消息已作为总结添加")
                self.prompt_obj.insert_summary(str(self.summary[:-1]))
            self.prompt_obj.build_openai_messages()
            self.client.set_messages(self.prompt_obj.messages)
            async for chunk in self.client.response(self.config.stream):
                response_chunks.append(chunk)
                response = "".join(response_chunks)
                current_time = asyncio.get_event_loop().time()
                # 每 4 秒或内容显著变化时更新消息
                if current_time - last_update_time >= 4.0 and response != last_updated_content:
                    await update_message(response, self.placeholder)
                    last_updated_content = response
                    last_update_time = current_time
                await asyncio.sleep(0.01)
            self.output = Message(self.placeholder.message_id, "".join(response_chunks), 'output')
            await finalize_message(self.placeholder, self.output.text_processed, summary=self.output.text_summary)
            if save:
                await self._save()
        except Exception as e:
            logger.error(f"响应用户时发生异常: {e}", exc_info=True)
            error_text = f"❌ 出错了：{str(e)}"
            await finalize_message(self.placeholder, error_text)

    def _save_turn_content_to_db(self):
        """
        将一次对话的内容保存到数据库.
        该方法首先获取当前对话的轮次,然后将用户输入和 LLM 的回复
        分别保存到数据库中.
        """
        db.dialog_content_add(self.id, USER, self.turn + 1, self.input.text_raw, self.input.text_processed, self.input.id,
                              PRIVATE)
        db.dialog_content_add(self.id, ASSISTANT, self.turn + 2, self.output.text_raw, self.output.text_processed,
                              self.output.id,
                              PRIVATE)

    async def _update_usage_info(self):
        """
        更新用户的使用信息.
        该方法计算输入和输出的 token 数量,并更新数据库中用户的
        token 数量,对话轮次和剩余频率.
        """
        input_tokens = self.client.calculate_token_count(str(self.client.messages))  # 计算输入tokens
        logger.info(f"输入令牌：{input_tokens}")
        db.user_info_update(self.user.id, 'input_tokens', input_tokens, True)
        output_tokens = self.client.calculate_token_count(self.output.text_raw)  # 计算输出tokens
        logger.info(f"输出令牌：{output_tokens}")
        db.user_info_update(self.user.id, 'output_tokens', output_tokens, True)
        db.conversation_private_arg_update(self.id, 'turns', 1, True)  # 增加对话轮次计数
        db.user_info_update(self.user.id, 'dialog_turns', 1, True)
        self._update_frequency()

    def _update_frequency(self):
        """
        更新用户的额度信息。

        如果用户有临时频率（tmp_frequency > 0），则更新签到频率（frequency）；
        否则，更新剩余频率（remain_frequency）。
        """
        if self.user.tmp_frequency > 0:
            db.user_sign_info_update(self.user.id, 'frequency', self.config.multiple * -1)
        else:
            db.user_info_update(self.user.id, 'remain_frequency', self.config.multiple * -1, True)

    async def _check_summary(self):
        """
        检查当前会话是否需要总结。如果缺少总结则自动补全所有缺失区域的总结（后台任务，按序执行）。
        """
        logger.debug(f"开始检查对话{self.id}是否存在摘要")
        logger.debug(f"该对话轮次为{self.turn}轮")
        if self.turn <= 60:
            logger.debug("轮次不足，跳过检查")
            return False  # 轮次未超过60，无需检查

        # 计算需要检查的总结区域数量
        area_count = (self.turn - 1) // 30  # 61-90=>2, 91-120=>3, 121-150=>4
        summaries = self.summary

        # 构建已存在的总结区域集合
        exist_areas = set()
        for s in summaries:
            area = s.get('summary_area')
            if area:
                exist_areas.add(area)

        # 需要补全的区域列表
        missing_areas = []
        for i in range(1, area_count):
            start = (i - 1) * 30 + 1
            end = i * 30
            area_str = f"{start}-{end}"
            if area_str not in exist_areas:
                missing_areas.append((start, end, area_str))

        if not missing_areas:
            return True  # 所有区域都有总结

        logger.info(f"发现缺失总结的区域: {[a[2] for a in missing_areas]}，将依次补全（后台任务）。")

        async def generate_all_summaries():
            for start, end, area_str in missing_areas:
                result = await self._generate_summary(start, end)
                if not result:
                    logger.warning(f"区域 {area_str} 总结生成失败，后续区域不再尝试。")
                    break

        # 启动后台任务
        asyncio.create_task(generate_all_summaries())
        return False  # 返回False，表示总结还未全部补全

    async def _generate_summary(self, start: int, end: int):
        """
        为指定区域的内容生成并添加summary。

        Args:
            start (int): 区域起始轮次
            end (int): 区域结束轮次

        Returns:
            bool: 添加总结是否成功
        """
        area_str = f"{start}-{end}"
        max_retry = 4
        for attempt in range(1, max_retry + 1):
            try:
                summary_text = await LLM.generate_summary(self.id, summary_type='zip', start=start, end=end)
                # 检查summary_text长度
                if not summary_text or len(summary_text) < 300:
                    logger.warning(f"第{attempt}次尝试：区域 {area_str} 生成的总结过短（<300字符），将重试。")
                    continue
                result = dialog_summary_add(self.id, area_str, summary_text)
                if result:
                    logger.info(f"成功为区域 {area_str} 添加总结")
                    return True
                else:
                    logger.warning(f"为区域 {area_str} 添加总结失败")
                    # 这里也重试
            except Exception as e:
                logger.error(f"第{attempt}次尝试：生成或添加总结时出错: {e}")
                continue
        logger.error(f"区域 {area_str} 总结生成失败，已达最大重试次数。")
        return False