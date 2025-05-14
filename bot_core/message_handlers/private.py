import asyncio

import telegram
from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from bot_core.public_functions.conversation import Conversation
import bot_core.public_functions.update_parse as public
from bot_core.public_functions.decorators import Decorators
from utils import LLM_utils as llm
from . import features
from .public import finalize_message
from ..public_functions.logging import logger


@Decorators.ensure_user_info_updated
async def private_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理私聊消息。

    Args:
        update (Update): Telegram 更新对象。
        context (ContextTypes.DEFAULT_TYPE): 上下文对象。

    Note:
        此函数已使用 @check_message_and_user 装饰器进行用户和消息有效性检查。
        如果消息无效或用户未注册，装饰器会自动处理并返回。
    """
    user_id = update.message.from_user.id
    try:
        # 检查是否在新建角色状态
        newchar_state = context.bot_data.get('newchar_state', {}).get(user_id)
        if newchar_state:
            logger.info(f"用户处于新建角色状态，用户ID: {user_id}")
            await features.private_newchar(update, newchar_state, user_id)
            return

        # 处理普通私聊消息
        await private_reply(update, context)
    except Exception as e:
        logger.error(f"处理私聊消息时出错: {str(e)}，用户ID: {user_id}", exc_info=True)


async def _streaming_response(update, conversation) -> None:
    """处理流式传输回复逻辑，生成并逐步更新响应内容。

    Args:
        update: Telegram 更新对象。
        conversation: 当前会话对象。
    """

    # logger.info(f"使用流式传输生成私聊回复, user_id: {conversation.info['user_id']}")
    sent_message = None  # 初始化 sent_message
    try:
        # 初始化响应消息
        sent_message = await update.message.reply_text("...", parse_mode="markdown")
        msg_id = sent_message.message_id
        conversation.set_send_msg_id(msg_id)
        # 获取流式响应并处理
        full_response = await _process_streaming_response_background(conversation, sent_message)
        conversation.set_response_text(full_response)
        await finalize_message(sent_message, conversation.cleared_response_text)
        conversation.save_to_db('assistant')
    except Exception as e:
        logger.error(f"处理流式响应时出错: {e}", exc_info=True)
        if sent_message:
            try:
                await sent_message.edit_text("处理消息时出错，请稍后再试。")
            except Exception as edit_e:
                logger.error(f"编辑流式错误消息失败: {edit_e}")


@Decorators.handle_command_errors
async def private_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理私聊文本消息。
    Args:
        update (Update): Telegram 更新对象。
        context (ContextTypes.DEFAULT_TYPE): 上下文对象。
    """
    # Keep existing logic, decorators are for commands
    try:
        info = public.update_info_get(update)
        conversation = Conversation(info)
        conversation.check_id('private')
        if info['remain'] > 0:
            conversation.save_to_db('user')
            if info['stream'] == 'yes':
                _task = asyncio.create_task(_streaming_response(update, conversation))
                return None
            else:
                placeholder_message = await update.message.reply_text("思考中...")  # 发送占位符
                conversation.set_send_msg_id(placeholder_message.message_id)
                _task = asyncio.create_task(_non_streaming_response(conversation, placeholder_message))
                return None
        else:
            await update.message.reply_text("您的额度已用尽，请联系 @xi_cuicui")

    except Exception as e:
        logger.error(f"处理私聊消息时出错: {str(e)}", exc_info=True)
        await update.message.reply_text(f"处理消息时发生错误{str(e)}，请稍后重试。")


async def _process_streaming_response_background(conversation, sent_message) -> str:
    """
    处理流式传输响应，定期更新消息内容。
    """
    response_chunks = []
    last_update_time = asyncio.get_event_loop().time()
    last_updated_content = "..."
    # Correctly iterate over the async generator
    async for chunk in llm.get_response_stream(conversation.prompt, conversation.id, 'private', conversation.api):
        response_chunks.append(chunk)
        full_response = "".join(response_chunks)
        current_time = asyncio.get_event_loop().time()
        # 每 8 秒或内容显著变化时更新消息
        if current_time - last_update_time >= 8 and full_response != last_updated_content:
            await _update_message(sent_message, full_response, last_updated_content)
            last_updated_content = full_response
            last_update_time = current_time
        # 短暂让出事件循环控制权，避免长时间占用
        await asyncio.sleep(0.01)
    return "".join(response_chunks)


async def _update_message(sent_message, full_response: str, last_updated_content: str) -> None:
    """
    更新消息内容，避免频繁更新导致 Telegram API 过载。
    Args:
        sent_message: 已发送的消息对象。
        full_response (str): 当前完整的响应内容。
        last_updated_content (str): 上次更新的内容。
    """
    try:
        # Telegram 单条消息最大长度限制4096字符，保险起见用4000
        MAX_LEN = 4000
        if len(full_response) > MAX_LEN:
            full_response = full_response[-MAX_LEN:]
        await sent_message.edit_text(full_response, parse_mode="markdown")
    except BadRequest as e:
        logger.warning(f"Markdown 解析错误: {str(e)}, 禁用 Markdown 重试")
        try:
            await sent_message.edit_text(full_response, parse_mode=None)
        except Exception as e2:
            logger.error(f"再次尝试发送消息失败: {e2}")
            sent_message.edit_text(f"Failed: {e2}")
    except TelegramError as e:
        if "Message is not modified" in str(e):
            logger.debug(f"消息内容未变化，跳过更新: {str(e)}")
            sent_message.edit_text(f"Failed: {e}")
        else:
            logger.error(f"更新消息时出错: {str(e)}")
            sent_message.edit_text(f"Failed: {e}")


async def _non_streaming_response(conversation, placeholder_message: telegram.Message) -> None:
    """
    处理非流式传输回复逻辑 (后台任务)。

    Args:
        conversation:conv对象。
        placeholder_message (telegram.Message): 占位符消息对象。
    """

    try:

        await conversation.get_response()
        await finalize_message(placeholder_message, conversation.cleared_response_text)
        conversation.save_to_db('assistant')

    except Exception as e:
        logger.error(f"{conversation.info['user_name']}后台处理非流式回复失败, 错误: {e}", exc_info=True)
        try:
            await placeholder_message.edit_text("处理消息时出错，请稍后再试。")
        except Exception as edit_e:
            logger.error(f"编辑错误消息失败: {edit_e}")
