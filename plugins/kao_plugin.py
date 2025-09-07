import time
import os
import asyncio
import logging
import base64
from PIL import Image
from telegram import Update
from telegram.ext import ContextTypes

# 导入插件基类
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from bot_core.services.plugin_service import BasePlugin, PluginMeta

# 导入必要的依赖
import bot_core.services.utils.usage as fm
from agent.llm_functions import analyze_image_for_kao
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class KaoPlugin(BasePlugin):
    """颜值评分插件
    
    该插件用于分析用户回复的图片消息，并生成一个包含颜值评分的回复。
    """
    
    def __init__(self):
        super().__init__()
        self.meta = PluginMeta(
            name="kao",
            version="1.0.0",
            description="颜值评分插件，分析图片并给出颜值评分",
            author="CyberWaifu Bot Team",
            trigger="kao",
            command_type="group",
            menu_text="颜值评分",
            show_in_menu=True,
            menu_weight=1
        )
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/kao命令，分析用户回复的图片消息。"""
        if not update.message.reply_to_message:
            await update.message.reply_text("请回复一条包含图片的消息来使用此命令。")
            return

        replied_message = update.message.reply_to_message

        if not (
            replied_message.photo
            or replied_message.sticker
            or replied_message.animation
        ):
            await update.message.reply_text(
                "请回复一条包含图片、贴纸或GIF的消息来使用此命令。"
            )
            return

        placeholder_msg = await replied_message.reply_text("正在分析，请稍候...")

        asyncio.create_task(
            self._process_kao_analysis(
                update, context, placeholder_msg, replied_message
            )
        )
    
    async def _process_kao_analysis(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        placeholder_msg,
        replied_message,
    ) -> None:
        """处理图片颜值分析的异步逻辑"""
        try:
            user_id = update.message.from_user.id
            group_id = update.message.chat.id

            file_id = None
            if replied_message.photo:
                file_id = replied_message.photo[-1].file_id
            elif replied_message.sticker:
                if replied_message.sticker.thumbnail:
                    file_id = replied_message.sticker.thumbnail.file_id
                else:
                    file_id = replied_message.sticker.file_id
            elif replied_message.animation:
                if replied_message.animation.thumbnail:
                    file_id = replied_message.animation.thumbnail.file_id
                else:
                    file_id = replied_message.animation.file_id

            pics_dir = "./data/pics"
            os.makedirs(pics_dir, exist_ok=True)
            timestamp = int(time.time())
            base_filename = f"{user_id}_{timestamp}"
            temp_filepath = os.path.join(pics_dir, f"{base_filename}.temp")
            final_filepath = os.path.join(pics_dir, f"{base_filename}.jpg")
            
            file = await context.bot.get_file(file_id)
            await file.download_to_drive(temp_filepath)

            if replied_message.sticker or replied_message.animation:
                try:
                    with Image.open(temp_filepath) as img:
                        img.convert("RGB").save(final_filepath, "jpeg")
                    os.remove(temp_filepath)
                except Exception as e:
                    logger.error("转换图片失败: %s, 将直接使用临时文件", e)
                    os.rename(temp_filepath, final_filepath)
            else:
                os.rename(temp_filepath, final_filepath)
            
            filepath = final_filepath
            base64_data = await self._image_to_base64(filepath)
            
            response, llm_messages = await analyze_image_for_kao(
                base64_data=base64_data,
                mime_type="image/jpeg",
                parse_mode="html",
            )

            logger.info("用户%s在群聊%s调用了kao命令", user_id, group_id)
            fm.update_user_usage(group_id, str(llm_messages), response, "group_photo")

            txt_filename = f"{base_filename}.txt"
            txt_filepath = os.path.join(pics_dir, txt_filename)
            with open(txt_filepath, "w", encoding="utf-8") as f:
                f.write(response)

            await context.bot.edit_message_text(
                text=response,
                chat_id=group_id,
                message_id=placeholder_msg.message_id,
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error(f"颜值分析失败: {e}", exc_info=True)
            try:
                await context.bot.edit_message_text(
                    text=f"颜值分析失败：{str(e)}",
                    chat_id=update.message.chat.id,
                    message_id=placeholder_msg.message_id,
                )
            except Exception as ex:
                logger.error(f"编辑占位消息失败: {ex}")
                await replied_message.reply_text(f"颜值分析失败：{str(e)}")

    async def _image_to_base64(self, filepath: str) -> str:
        """将图片文件转换为base64编码。"""
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(
                image_file.read()).decode("utf-8")
        return encoded_string