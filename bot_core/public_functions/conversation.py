import asyncio
import random
from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes
from bot_core.public_functions.logging import logger
from utils import LLM_utils as llm, prompt_utils as prompt, db_utils as db, text_utils as txt, file_utils as file
from utils.LLM_utils import LLM

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

    def __init__(self, id, text, mark):
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
        self.id = id
        self.text_raw = text
        if mark == 'input':
            self.text_processed = txt.extract_special_control(text)[0] or text  # 对于输入消息，提取特殊控制内容
        elif mark == 'output':
            self.text_processed = txt.extract_tag_content(text, 'content')  # 对于输出消息，提取标签内容
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
        self.multiple = file.get_api_multiple(self.api)  # 从文件中获取API多路复用信息


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
        self.prompt = None
        self.placeholder = None
        self.config = GroupConfig(update.message.chat.id)  # 创建群组配置对象
        self.trigger = None
        self.user = GroupUser(update)  # 创建用户对象
        self.id = db.conversation_group_get(self.group.id, self.user.id) or None  # 从数据库获取会话ID
        if not self.id:
            self._new()
        self.images = self._extract_images()
        self.client = LLM(self.config.api,'group')


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
        self._build_prompts()

    def _build_prompts(self):
        self.prompt = prompt.build_prompts(self.config.char, self.input.text_raw, self.config.preset)
        self.prompt = prompt.insert_text(self.prompt,
                                         f"<user_nickname>\r\n你需要回复的用户的姓名或网名是‘{self.user.user_name}’，如果这个名字不方便称呼"
                                         f"，你可以自行决定怎么称呼用户\r\n</user_nickname>\r\n",
                                         '<user_input>\r\n', 'before')  # 在指定位置插入用户昵称信息
        group_dialog = db.group_dialog_get(self.group.id, 15)  # 获取最近15条群组对话
        insert_txt = f"<group_messages>\r\n现在是群聊模式，你需要先看看群友在聊什么，再输出内容：\r\n"
        for dialog in group_dialog:
            if dialog[1]:  # 假设 dialog[1] 是用户名
                if dialog[2]:
                    insert_txt += f"{dialog[3]}  {dialog[1]}:\r\n{dialog[0]}\r\n"  # 格式化对话内容
                    insert_txt += f"{dialog[3]}  AI助手:\r\n{dialog[2]}\r\n"
                else:
                    insert_txt += f"{dialog[3]}  {dialog[1]}:\r\n{dialog[0]}\r\n"
        insert_txt += "</group_messages>"
        self.prompt = prompt.insert_text(self.prompt, insert_txt, '<user_input>\r\n', 'before')  # 插入群组消息

        # 确保用户输入内容被嵌入到 <user_input> 标签内
        if self.input.text_processed:
            user_input_text = f"<user_input>\r\n{self.input.text_raw}\r\n</user_input>\r\n"
            self.prompt = prompt.insert_text(self.prompt, user_input_text, '<user_input>\r\n', 'after')

        # 如果有图片，添加图片提示
        if self.images:
            image_prompt = "<image_input>\r\n用户发送了图片，请仔细查看图片内容并根据图片内容回复。\r\n</image_input>\r\n"
            self.prompt = prompt.insert_text(self.prompt, image_prompt, '<user_input>\r\n', 'after')

    async def response(self):
        """
        处理响应逻辑，包括发送占位消息和异步任务。
        该方法是异步的，用于Telegram机器人环境。
        副作用:
        发送占位消息并启动异步任务。
        """
        self.placeholder = await self.update.message.reply_text("思考中")  # 发送占位消息
        if self.trigger in ['random', 'keyword','@']:
            self.id = 0# 创建一次性响应任务
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
        self.client.build_conv_messages(self.id)
        self.client.set_prompt(self.prompt)
        await self.client.embedd_all_text(self.images,self.context)
        last_update_time = asyncio.get_event_loop().time()
        last_updated_content = "..."
        response_chunks = []
        response='Error：未能获取模型回复。'
        async for chunk in self.client.response(False):
            response_chunks.append(chunk)
            response = "".join(response_chunks)
            current_time = asyncio.get_event_loop().time()
            if current_time - last_update_time >= 4.0 and response != last_updated_content:
                await _update_message(response, self.placeholder)
                last_updated_content = response
                last_update_time = current_time
            await asyncio.sleep(0.01)
        self.output = Message(self.placeholder.message_id, response, 'output')  # 创建输出消息对象
        await _finalize_message(self.placeholder, self.output.text_processed)  # 完成消息处理
        self._update_usage_info()  # 更新使用信息

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
        if self.trigger in ['random', 'keyword']:
            input_token = llm.calculate_token_count(self.prompt)  # 计算输入令牌
        else:
            input_token = llm.calculate_token_count(str(self.client.messages))  # 计算对话令牌
            turn = db.dialog_turn_get(self.id, 'group')  # 获取当前回合
            db.dialog_content_add(self.id, USER, turn + 1, self.input.text_raw, self.input.text_processed,
                                  self.input.id, GROUP)  # 添加用户对话
            db.dialog_content_add(self.id, ASSISTANT, turn + 2, self.output.text_raw, self.output.text_processed,
                                  self.output.id, GROUP)  # 添加助手对话
            db.conversation_group_update(self.group.id, self.user.id, 'turns', 1)  # 更新回合数
        output_token = llm.calculate_token_count(self.output.text_raw)  # 计算输出令牌
        db.group_info_update(self.group.id, 'input_token', input_token, True)  # 更新输入令牌
        db.group_info_update(self.group.id, 'output_token', output_token, True)  # 更新输出令牌
        db.group_dialog_update(self.input.id, 'trigger_type', self.trigger, self.group.id)  # 更新触发类型
        db.group_dialog_update(self.input.id, 'raw_response', self.output.text_raw, self.group.id)  # 更新原始响应
        db.group_dialog_update(self.input.id, 'processed_response', self.output.text_processed,
                               self.group.id)  # 更新处理后响应


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
        prompt (str): 用于传递给 LLM 的提示字符串.
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
        self.config = Config(self.user.id)
        self.client = LLM(self.config.api,'private')
        if not self.id:
            self.new()
        # 构建 prompt
        if self.input:
            self.prompt = prompt.build_prompts(self.config.char, self.input.text_raw, self.config.preset)
            self.prompt = prompt.insert_text(self.prompt,
                                             f"用户的昵称是：{self.user.nick}，你需要按照这个方式来称呼他"
                                             f"如果用户的昵称不方便直接称呼，你可以自行决定如何称呼用户\r\n",
                                             '<character>',
                                             'before')
        else:
            self.prompt = None

    async def response(self, save=True):
        """
        生成并发送 LLM 的回复.
        该方法首先发送一个占位消息,然后根据配置选择流式或非流式回复模式,
        并创建一个异步任务来处理 LLM 的回复.
        Args:
            save (bool, optional): 是否保存对话记录到数据库. 默认为 True.
        """
        if self.user.frequency > 0 or self.user.tmp_frequency > 0:
            self.placeholder = await self.context.bot.send_message(self.user.id, "思考中...")
            logger.info(f"输入：{self.input.text_raw}")
            _task = asyncio.create_task(self._response_to_user(save))
        else:
            await self.context.bot.send_message(self.user.id, "你的额度已用尽，联系 @xi_cuicui")

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
        self.prompt = prompt.build_prompts(self.config.char, self.input.text_raw, self.config.preset)
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
        该方法用于处理回调查询,将回调数据设置为输入消息,并重新构建 prompt.
        Args:
            data (str): 回调数据.
        """
        self.input = Message(0, data, 'callback')
        self.prompt = prompt.build_prompts(self.config.char, self.input.text_processed, self.config.preset)
        self.prompt = prompt.insert_text(self.prompt,
                                         f"<user_nickname>\r\n用户的昵称是：{self.user.nick}，你需要按照这个方式来称呼他"
                                         f"如果用户的昵称不方便直接称呼，你可以自行决定如何称呼用户\r\n</user_nickname>\r\n",
                                         '<character>',
                                         'before')


    async def _response_to_user(self, save):
        """
        Args:
            save (bool): 是否保存对话记录到数据库.
        """
        # print("流式回复")
        last_update_time = asyncio.get_event_loop().time()
        last_updated_content = "..."
        response_chunks = []

        self.client.build_conv_messages(self.id)
        print(f"已设置{self.id}")
        self.client.set_prompt(self.prompt)
        await self.client.embedd_all_text()

        async for chunk in self.client.response(self.config.stream):
            response_chunks.append(chunk)
            response = "".join(response_chunks)
            current_time = asyncio.get_event_loop().time()
            # 每 4 秒或内容显著变化时更新消息
            if current_time - last_update_time >= 4.0 and response != last_updated_content:
                await _update_message(response, self.placeholder)
                last_updated_content = response
                last_update_time = current_time
            # 短暂让出事件循环控制权，避免长时间占用
            await asyncio.sleep(0.01)
        self.output = Message(self.placeholder.message_id, "".join(response_chunks), 'output')
        await _finalize_message(self.placeholder, self.output.text_processed)
        if save:
            await self._save()

    def _save_turn_content_to_db(self):
        """
        将一次对话的内容保存到数据库.
        该方法首先获取当前对话的轮次,然后将用户输入和 LLM 的回复
        分别保存到数据库中.
        """
        turn = db.dialog_turn_get(self.id, 'private')
        db.dialog_content_add(self.id, USER, turn + 1, self.input.text_raw, self.input.text_processed, self.input.id,
                              PRIVATE)
        db.dialog_content_add(self.id, ASSISTANT, turn + 2, self.output.text_raw, self.output.text_processed,
                              self.output.id,
                              PRIVATE)

    async def _update_usage_info(self):
        """
        更新用户的使用信息.
        该方法计算输入和输出的 token 数量,并更新数据库中用户的
        token 数量,对话轮次和剩余频率.
        """
        input_tokens = llm.calculate_token_count(str(self.client.messages)) # 计算输入tokens
        db.user_info_update(self.user.id, 'input_tokens', input_tokens, True)
        output_tokens = llm.calculate_token_count(self.output.text_raw)  # 计算输出tokens
        db.user_info_update(self.user.id, 'output_tokens', output_tokens, True)
        db.conversation_private_arg_update(self.id, 'turns', 1, True)  # 增加对话轮次计数
        db.user_info_update(self.user.id, 'dialog_turns', 1, True)
        self._update_frequency()

    def _update_frequency(self):
        if self.user.tmp_frequency > 0:
            db.user_sign_info_update(self.user.id, 'frequency', self.config.multiple * -1, True)
        else:
            db.user_info_update(self.user.id, 'remain_frequency', self.config.multiple * -1, True)


async def _update_message(text, placeholder):
    try:
        # Telegram 单条消息最大长度限制4096字符，保险起见用4000
        MAX_LEN = 4000
        if len(text) > MAX_LEN:
            text = text[-MAX_LEN:]
        await placeholder.edit_text(text, parse_mode="markdown")
    except BadRequest as e:
        logger.warning(f"Markdown 解析错误: {str(e)}, 禁用 Markdown 重试")
        try:
            await placeholder.edit_text(text, parse_mode=None)
        except Exception as e2:
            logger.error(f"再次尝试发送消息失败: {e2}")
            placeholder.edit_text(f"Failed: {e2}")
    except TelegramError as e:
        if "Message is not modified" in str(e):
            logger.debug(f"消息内容未变化，跳过更新: {str(e)}")
            placeholder.edit_text(f"Failed: {e}")
        else:
            logger.error(f"更新消息时出错: {str(e)}")
            placeholder.edit_text(f"Failed: {e}")


async def _finalize_message(sent_message, cleared_response: str) -> None:
    """
    最终更新消息内容，确保显示最终的处理后的响应。
    Args:
        sent_message: 已发送的消息对象。
        cleared_response (str): 处理后的最终响应内容。
    """
    max_len = 4000
    try:
        # Telegram 单条消息最大长度限制4096字符，保险起见用4000
        if len(cleared_response) <= max_len:
            await sent_message.edit_text(cleared_response, parse_mode="markdown")
        else:
            # 超长时分两段发送，先发前半段，再发后半段
            await sent_message.edit_text(cleared_response[:max_len], parse_mode="markdown")
            await sent_message.reply_text(cleared_response[max_len:], parse_mode="markdown")
        logger.info(f"输出：\r\n{cleared_response}")
    except BadRequest as e:
        logger.warning(f"Markdown 解析错误: {str(e)}, 禁用 Markdown 重试")
        try:
            if len(cleared_response) <= max_len:
                await sent_message.edit_text(cleared_response, parse_mode=None)
            else:
                await sent_message.edit_text(cleared_response[:max_len], parse_mode=None)
                await sent_message.reply_text(cleared_response[max_len:], parse_mode=None)
            logger.info(f"输出：\r\n{cleared_response}")
        except Exception as e2:
            logger.error(f"再次尝试发送消息失败: {e2}")
            await sent_message.edit_text(f"Failed: {e2}")
    except TelegramError as e:
        if "Message is not modified" in str(e):
            logger.debug(f"最终更新时消息内容未变化，跳过更新: {str(e)}")
            await sent_message.edit_text(f"Failed: {e}")
        else:
            logger.error(f"最终更新消息时出错: {str(e)}")
            await sent_message.edit_text(f"Failed: {e}")
