import asyncio
import random
from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes
from bot_core.public_functions.logging import logger
from utils import LLM_utils as llm, prompt_utils as prompt, db_utils as db, text_utils as txt, file_utils as file
import telegram

# 定义常量
PRIVATE = 'private'
GROUP = 'group'
USER = 'user'
ASSISTANT = 'assistant'
REPLY = 'reply'
KEYWORD = 'keyword'
RANDOM = 'random'


class User():
    def __init__(self, user_id):
        self.id = user_id
        self.nick = db.user_info_get(user_id).get('user_nick')


class Message:
    def __init__(self, id, text, mark):
        # print(text)
        self.id = id
        self.text_raw = text
        if mark == 'input':
            self.text_processed = txt.extract_special_control(text)[0] or text
        elif mark == 'output':
            self.text_processed = txt.extract_tag_content(text, 'content')
        else:
            self.text_processed = text


class Config:
    def __init__(self, user_id):
        self.api = db.user_api_get(user_id)
        info = db.user_config_get(user_id)
        self.char, self.preset = info.get('char'), info.get('preset')
        self.stream = db.user_stream_get(user_id)
        self.multiple = file.get_api_multiple(self.api)


"""
实现update解析用户信息
实现流式/非流式传输
实现撤回/重新生成
实现保存/删除
"""


class PrivateConv:

    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.placeholder = None
        self.context = context
        self.update = update
        self.input = None
        self.output = None
        self.prompt = None
        self.config = None
        if update.message:
            self.user = User(update.message.chat.id)
            self.input = Message(update.message.message_id, update.message.text, 'input') or None
        else:
            self.user = User(update.callback_query.from_user.id)
        self.id = db.user_conv_id_get(self.user.id)
        self.config = Config(self.user.id)
        if not self.id:
            self.new()

        if self.input:
            self.prompt = prompt.build_prompts(self.config.char, self.input.text_processed, self.config.preset)
        else:
            self.prompt = None

    async def response(self, save=True):
        self.placeholder = await self.context.bot.send_message(self.user.id, "思考中...")
        if self.config.stream:
            _task = asyncio.create_task(self._response_stream(save))
        else:
            _task = asyncio.create_task(self._response_non_stream(save))

    async def regen(self):
        last_msg_id_list = db.conversation_latest_message_id_get(self.id)
        last_input = db.dialog_last_input_get(self.id)
        db.conversation_delete_messages(self.id, last_msg_id_list[0])
        db.conversation_delete_messages(self.id, last_msg_id_list[1])
        self.input = Message(last_msg_id_list[1], last_input, 'input')
        self.prompt = prompt.build_prompts(self.config.char, self.input.text_processed, self.config.preset)
        await self.context.bot.delete_message(self.user.id, last_msg_id_list[0])
        await self.response()

    async def undo(self):
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
                        success = False  # 只要有一个消息删除失败，就标记为失败
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

    def save(self):
        if not self.output.text_raw.startswith('API调用失败'):
            self._save_turn_content_to_db()
            self._update_usage_info()

    def set_callback_data(self, data):
        self.input = Message(0, data, 'callback')
        self.prompt = prompt.build_prompts(self.config.char, self.input.text_processed, self.config.preset)

    async def _response_non_stream(self, save):
        response = await llm.get_response_no_stream(self.prompt, self.id, 'private', self.config.api)
        self.output = Message(self.placeholder.message_id, response, 'output')
        await self.placeholder.edit_text(self.output.text_processed)
        if save:
            self.save()

    async def _response_stream(self, save):
        # print("流式回复")
        last_update_time = asyncio.get_event_loop().time()
        last_updated_content = "..."
        response_chunks = []
        async for chunk in llm.get_response_stream(self.prompt, self.id, 'private', self.config.api):
            response_chunks.append(chunk)
            response = "".join(response_chunks)
            current_time = asyncio.get_event_loop().time()
            # 每 4 秒或内容显著变化时更新消息
            if current_time - last_update_time >= 4 and response != last_updated_content:
                await _update_message(response, self.placeholder)
                last_updated_content = response
                last_update_time = current_time
            # 短暂让出事件循环控制权，避免长时间占用
            await asyncio.sleep(0.01)
        self.output = Message(self.placeholder.message_id, "".join(response_chunks), 'output')
        await _finalize_message(self.placeholder, self.output.text_processed)
        if save:
            self.save()

    def _save_turn_content_to_db(self):
        turn = db.dialog_turn_get(self.id, 'private')
        db.dialog_content_add(self.id, USER, turn + 1, self.input.text_raw, self.input.text_processed, self.input.id,
                              PRIVATE)
        db.dialog_content_add(self.id, ASSISTANT, turn + 2, self.output.text_raw, self.output.text_processed,
                              self.output.id,
                              PRIVATE)

    def _update_usage_info(self):
        input_tokens = llm.calculate_token_count(str(llm.get_full_msg(self.id, 'private', self.prompt)))  # 计算输入tokens
        db.user_info_update(self.user.id, 'input_tokens', input_tokens, True)
        output_tokens = llm.calculate_token_count(self.output.text_raw)  # 计算输出tokens
        db.user_info_update(self.user.id, 'output_tokens', output_tokens, True)
        db.conversation_private_arg_update(self.id, 'turns', 1, True)  # 增加对话轮次计数
        db.user_info_update(self.user.id, 'remain_frequency', self.config.multiple * -1, True)  # 增加已使用计数
        db.user_info_update(self.user.id, 'dialog_turns', 1, True)


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
    except BadRequest as e:
        logger.warning(f"Markdown 解析错误: {str(e)}, 禁用 Markdown 重试")
        try:
            if len(cleared_response) <= max_len:
                await sent_message.edit_text(cleared_response, parse_mode=None)
            else:
                await sent_message.edit_text(cleared_response[:max_len], parse_mode=None)
                await sent_message.reply_text(cleared_response[max_len:], parse_mode=None)
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


class Conversation():
    """会话类，用于管理和处理用户与机器人的交互信息。"""

    def __init__(self, info: dict):
        """初始化会话对象。

        Args:
            info (dict): 包含会话所需信息的字典，例如用户信息、消息内容等。
        """
        self.info = info or None
        self.id = info.get('conv_id')
        self.char = info.get('char')
        self.preset = info.get('preset')
        self.api = info.get('api')
        self.type = PRIVATE if info.get('chat_type') == PRIVATE else GROUP
        self.history = llm.build_openai_messages(self.id, self.type) or None
        self.prompt = prompt.build_prompts(self.char, info.get('message_text'), self.preset) or None
        self.response_text = None
        self.cleared_response_text = None
        self.send_msg_id = None
        self.turn = db.dialog_turn_get(self.id, self.type) or 0
        self.trigger = None
        self.latest_message_id = db.conversation_latest_message_id_get(self.id) or [0]
        self.received_text = info.get("message_text") or None
        self.cleared_received_text = txt.extract_special_control(self.received_text)[0] or self.received_text
        logger.info(self.cleared_received_text)
        if self.type == GROUP or self.type == 'once':
            self._build_group_prompt()
        else:
            self._insert_user_nick()

    def save_to_db(self, role: str, msg_id=None):
        """将当前会话信息保存到数据库。
        Args:
            role (str): 当前消息的角色，'user' 或 'assistant'。
            msg_id
        """
        self.turn += 1
        token = llm.calculate_token_count(
            str(llm.get_full_msg(self.id, self.type, self.prompt)) if role == USER else self.response_text)
        if self.trigger not in [RANDOM, KEYWORD]:
            db.dialog_content_add(self.id, role, self.turn,
                                  self.received_text if role == USER else self.response_text,
                                  self.cleared_response_text if role == ASSISTANT else self.cleared_received_text,
                                  msg_id if msg_id else (
                                      self.info.get('message_id') if role == USER else self.send_msg_id), self.type)
        if self.type == PRIVATE:
            self._save_user_usage_info(token, role)
        else:
            self._save_group_dialog(token, role)

    def set_send_msg_id(self, msg_id: int):
        """设置机器人发送消息的ID。

        Args:
            msg_id (int): 消息ID。
        """
        self.send_msg_id = msg_id

    def set_trigger(self, trigger: str):
        """设置触发回复的类型。

        Args:
            trigger (str): 触发类型，例如 'reply', '@', 'keyword', 'random'。
        """
        self.trigger = trigger

    def set_response_text(self, text: str):
        """设置机器人的回复文本，并提取清理后的文本内容。
        Args:
            text (str): 机器人的原始回复文本。
        """
        self.response_text = text
        self.cleared_response_text = txt.extract_tag_content(text, 'content')
        logger.info(self.cleared_response_text)

    def set_once_type(self):
        self.type = 'once'

    def check_id(self, chat_type: str):
        """检查会话ID是否存在，如果不存在则创建新的会话ID。
        Args:
            chat_type (str): 聊天类型，'private' 或 'group'。
        Raises:
            ValueError: 如果尝试多次后仍无法创建ID。
        """
        logger.info(f"检查会话ID, chat_type: {chat_type}")
        if not self.id:  # 使用 get() 避免 KeyError
            try:
                if chat_type == GROUP:
                    new_conv_id = self.new(GROUP)
                    logger.info(
                        f"新建群聊对话, group_name: {self.info.get('group_name')}, user_name: {self.info.get('user_name')}, conv_id: {new_conv_id}")
                else:  # 假设为 'private'
                    new_conv_id = self.new(PRIVATE)
                    db.user_config_arg_update(self.info.get('user_id'), 'conv_id', new_conv_id)
                    logger.info(f"{self.info.get('user_name')} 新建私聊对话, conv_id: {new_conv_id}")
                self.id = new_conv_id  # 设置属性
            except Exception as e:  # 捕获一般异常，便于调试
                logger.error(f"创建会话ID失败: {e}")
                raise

    def new(self, conv_type: str) -> int or str:
        """辅助方法：生成新的会话ID并创建数据库记录。
        Args:
            conv_type (str): 'group' 或 'private'。
        Returns:
            int or str: 生成的新的会话ID。
        Raises:
            ValueError: 如果多次尝试后失败。
        """
        max_attempts = 5  # 限制尝试次数，避免无限循环
        for _ in range(max_attempts):

            new_conv_id = random.randint(10000000, 99999999)

            if conv_type == GROUP:
                if db.conversation_group_check(new_conv_id):  # 假设这个函数检查ID是否可用
                    db.conversation_group_create(new_conv_id, self.info.get('user_id'), self.info.get('user_name'),
                                                 self.info.get('group_id'), self.info.get('group_name'))
                    return new_conv_id
            else:  # 'private'
                if (db.conversation_private_create(new_conv_id, self.info.get('user_id'), self.info.get('char'),
                                                   self.info.get('preset')) and
                        db.user_config_arg_update(self.info.get('user_id'), 'conv_id', new_conv_id)):
                    db.user_info_update(self.info.get('user_id'), 'conversations', 1, True)
                    return new_conv_id

        raise ValueError(f"无法创建{conv_type}会话ID，经过{max_attempts}次尝试")

    async def get_response(self):
        full_response = await llm.get_response_no_stream(self.prompt, self.id, self.type, self.api)
        self.set_response_text(full_response)

    async def regenerate_response(self):
        last_input = db.dialog_last_input_get(self.id)
        self.received_text = last_input
        self.cleared_received_text = txt.extract_special_control(self.received_text)[0] or self.received_text
        self.prompt = prompt.build_prompts(self.char, self.received_text, self.preset)
        self._insert_user_nick()
        token = llm.calculate_token_count(str(llm.get_full_msg(self.id, self.type, self.prompt)))
        db.conversation_delete_messages(self.id, self.latest_message_id[0])
        db.conversation_delete_messages(self.id, self.latest_message_id[1])
        self.turn -= 2
        self._save_user_usage_info(token, USER)
        self.save_to_db(USER, self.latest_message_id[1])
        await self.get_response()

    async def set_director_control(self, text, save=False):
        self.received_text = text
        self.cleared_received_text = text
        self.prompt = prompt.build_prompts(self.char, self.received_text, self.preset)
        self._insert_user_nick()
        token = llm.calculate_token_count(str(llm.get_full_msg(self.id, self.type, self.prompt)))
        self._save_user_usage_info(token, USER)
        if save:
            self.save_to_db(USER, 0)
        await self.get_response()

    def _save_user_usage_info(self, token, role):
        db.user_info_update(self.info.get('user_id'), 'input_tokens' if role == USER else 'output_tokens', token,
                            True)
        db.user_info_update(self.info.get('user_id'), 'dialog_turns', 1, True)
        db.user_info_update(self.info.get('user_id'), 'remain_frequency', -1 if (role == ASSISTANT) and (
            not self.cleared_response_text.startswith('API调用失败')) else 0, True)
        db.conversation_private_arg_update(self.id, 'turns', 1, True)

    def _save_group_dialog(self, token, role):
        print(f"trigger is {self.trigger},role is {role},saving")
        if role == ASSISTANT:

            db.group_dialog_update(self.info.get('message_id'), 'raw_response', self.response_text,
                                   self.info.get('group_id'))
            db.group_dialog_update(self.info.get('message_id'), 'processed_response', self.cleared_response_text,
                                   self.info.get('group_id'))
            db.group_dialog_update(self.info.get('message_id'), 'trigger_type', self.trigger, self.info.get('group_id'))
            if self.trigger in [RANDOM, KEYWORD]:
                logger.info(
                    f"一次性群聊回复完成, group_name: {self.info.get('group_name')}, user_name: {self.info.get('user_name')}, output_token: {token}")
            else:
                db.conversation_group_update(self.info.get('group_id'), self.info.get('user_id'), 'turns', 1)
                db.group_dialog_update(self.id, 'trigger_type', REPLY, self.info.get('group_id'))
                db.group_dialog_update(self.id, 'raw_response', self.response_text, self.info.get('group_id'))
                db.group_dialog_update(self.id, 'processed_response', self.cleared_response_text,
                                       self.info.get('group_id'))

    def _build_group_prompt(self):
        self.prompt = prompt.insert_text(self.prompt,
                                         f"你需要回复的用户的姓名或网名是‘{self.info.get('user_name')}，以下是用户的输入’\r\n",
                                         '<user_input>\r\n', 'before')
        group_dialog = db.group_dialog_get(self.info.get('group_id'), 10)
        insert_txt = f"<现在是群聊模式，你需要先看看群友在聊什么，再输出内容：\r\n"
        for dialog in group_dialog:
            if dialog[1]:
                insert_txt += f"{dialog[1]}:\r\n{dialog[0]}\r\n"
        insert_txt += ">"
        self.prompt = prompt.insert_text(self.prompt, insert_txt, '<user_input>\r\n', 'before')

    def _insert_user_nick(self):
        self.prompt = prompt.insert_text(self.prompt,
                                         f"用户的昵称是：{self.info.get('user_nick')}，你需要按照这个方式来称呼他"
                                         f"如果用户的昵称不方便直接称呼，你可以自行决定如何称呼用户\r\n", '<character>',
                                         'before')
