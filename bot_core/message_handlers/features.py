# Standard library imports
import asyncio
import base64
import json
import logging
import os
import re
import time
from typing import TYPE_CHECKING

# Third-party imports
from PIL import Image
from telegram import Update
from telegram.ext import ContextTypes

# Local application imports
import bot_core.public_functions.frequency_manager as fm
from bot_core.public_functions import messages
from utils import LLM_utils
from utils import db_utils as db
from utils.config_utils import get_config
from utils.logging_utils import setup_logging
from utils import text_utils
from utils import file_utils

# Conditional imports for type checking
if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Load configuration
fuck_api = get_config(
    "fuck_or_not_api", "gemini-2"
)  # 从配置文件读取API，默认使用gemini-2


async def private_newchar(update: "Update", newchar_state: dict, user_id: int):
    """处理用于创建新角色的文本输入。

    此函数处理角色创建工作流程中的传入文本消息。

    Args:
        update: Telegram更新对象。
        newchar_state: 用于存储新角色创建过程状态的字典，
                     包括 'char_name' 和 'desc_chunks'。
        user_id: Telegram用户的唯一标识符。
    """
    if not update.message or not update.message.text:
        return

    # 在此状态下忽略命令
    if update.message.text.startswith('/'):
        return
        
    newchar_state.setdefault("desc_chunks", []).append(update.message.text)
    await update.message.reply_text(
        "文本已接收，可继续发送，发送 /done 完成。"
    )


async def _cleanup_keyword_messages(
    context: "ContextTypes.DEFAULT_TYPE",
    chat_id: int,
    user_message_id: int,
    bot_message_id: int,
    original_message_id: int | None,
):
    """删除用户和机器人的消息并移除内联键盘。"""
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=user_message_id)
    except Exception as e:
        logger.warning(f"Failed to delete user reply message: {e}")

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=bot_message_id)
    except Exception as e:
        logger.warning(f"Failed to delete prompt message: {e}")

    if original_message_id:
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=original_message_id, reply_markup=None
            )
        except Exception as e:
            logger.warning(f"Failed to remove inline keyboard: {e}")


async def group_keyword_add(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """处理为群组添加新关键词的过程。

    当用户回复特定的机器人消息以添加关键字时，将触发此功能。
    它会验证上下文，解析新关键字，更新数据库并清理交互消息。

    Args:
        update: Telegram更新对象。
        context: 上下文对象，用于访问user_data和机器人实例。
    """
    if (
        not context.user_data
        or not update.message
        or context.user_data.get("keyword_action") != "add"
        or not update.message.reply_to_message
        or not update.message.reply_to_message.from_user
    ):
        return

    if update.message.reply_to_message.from_user.id != context.bot.id:
        await update.message.reply_text("请回复 Bot 的消息来添加关键词。")
        return

    group_id = context.user_data.get("group_id")
    if not group_id:
        logger.warning("group_keyword_add called without group_id in user_data.")
        return

    input_text = (update.message.text or "").strip()
    new_keywords = [kw.strip() for kw in input_text.split() if kw.strip()]

    if not new_keywords:
        await update.message.reply_text("未提供有效的关键词。")
        return

    current_keywords = db.group_keyword_get(group_id)
    updated_keywords = list(set(current_keywords + new_keywords))
    db.group_keyword_set(group_id, updated_keywords)

    await _cleanup_keyword_messages(
        context,
        chat_id=update.message.chat.id,
        user_message_id=update.message.message_id,
        bot_message_id=update.message.reply_to_message.message_id,
        original_message_id=context.user_data.get("original_message_id"),
    )

    await messages.send_message(
        context,
        update.message.chat.id,
        f"已成功添加关键词：{', '.join(new_keywords)}",
    )
    context.user_data.clear()






class ImageAnalyzer:
    """
    封装了与图像分析相关的所有逻辑。
    """

    def __init__(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        if not update.message or not update.message.from_user:
            raise ValueError("Update或Message对象无效。")
        self.update = update
        self.context = context
        self.user_id = update.message.from_user.id
        self.chat_id = update.message.chat.id
        self.placeholder_msg = None

    async def _build_llm_payload(self, file_id: str) -> list[dict]:
        """构建LLM API调用的有效负载。"""
        system_prompt = file_utils.load_single_prompt("fuck_or_not")
        if not system_prompt:
            raise ValueError("无法加载 'fuck_or_not' prompt。")
            
        image_data = await text_utils.convert_file_id_to_base64(file_id, self.context)
        if not image_data:
            raise ValueError("无法将file_id转换为Base64")
            
        mime_type = image_data["mime_type"]
        base64_data = image_data["data"]

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "兄弟看看这个，你想不想操？"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_data}"},
                    },
                ],
            },
        ]

    def _parse_llm_response(self, response: str) -> str:
        """解析来自LLM的JSON响应并进行格式化。"""
        try:
            match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
            json_str = match.group(1) if match else response
            data = json.loads(json_str)
            score = data.get("score", "N/A")
            reason = data.get("reason", "N/A")
            fantasy = data.get("fantasy", "N/A")
            return f"```\n分数：{score}\n```\n\n理由：{reason}\n\n评价：{fantasy}"
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"解析LLM JSON响应失败: {e}。将使用原始响应。")
            return response

    async def analyze(self):
        """执行完整的图像分析工作流程。"""
        if not self.update.message:
            logger.warning("ImageAnalyzer.analyze called with no message.")
            return

        self.placeholder_msg = await self.update.message.reply_text(
            "正在分析，请稍候...", reply_to_message_id=self.update.message.message_id
        )
        
        filepath = None
        try:
            filepath = await file_utils.download_and_convert_image(self.update, self.context, self.user_id)
            
            file_id = self.update.message.photo[-1].file_id if self.update.message.photo else \
                      (self.update.message.sticker.thumbnail.file_id if self.update.message.sticker and self.update.message.sticker.thumbnail else
                       (self.update.message.sticker.file_id if self.update.message.sticker else
                        (self.update.message.animation.thumbnail.file_id if self.update.message.animation and self.update.message.animation.thumbnail else
                         (self.update.message.animation.file_id if self.update.message.animation else None))))

            if not file_id:
                raise ValueError("未能识别到图片、贴纸或GIF。")

            llm_messages = await self._build_llm_payload(file_id)

            llm = LLM_utils.LLM(api=fuck_api)
            llm.set_messages(llm_messages)
            response = await llm.final_response()

            fm.update_user_usage(self.chat_id, str(llm_messages), response, "private_photo")

            formatted_response = self._parse_llm_response(response)

            txt_filename = f"{os.path.basename(filepath).split('.')[0]}.txt"
            txt_filepath = os.path.join("data/pics", txt_filename)
            with open(txt_filepath, "w", encoding="utf-8") as f:
                f.write(formatted_response)

            await self.placeholder_msg.delete()

            with open(filepath, "rb") as photo_file:
                await messages.send_message(
                    context=self.context,
                    chat_id=self.chat_id,
                    message_content=formatted_response,
                    parse="markdown",
                    photo=photo_file,
                )

        except Exception as e:
            logger.error(f"图像分析失败: {e}", exc_info=True)
            if self.placeholder_msg:
                try:
                    await self.placeholder_msg.delete()
                except Exception:
                    pass
            await self.context.bot.send_message(self.chat_id, f"图片分析失败：{str(e)}")


async def f_or_not(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """
    通过实例化和运行ImageAnalyzer来处理用户图像分析请求。
    """
    try:
        analyzer = ImageAnalyzer(update, context)
        asyncio.create_task(analyzer.analyze())
    except ValueError as e:
        logger.warning(f"无法初始化ImageAnalyzer: {e}")


