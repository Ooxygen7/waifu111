import os
import time
import asyncio
import logging
from PIL import Image

from telegram import Update
from telegram.ext import ContextTypes

# 导入插件基类
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from bot_core.services.plugin_service import BasePlugin, PluginMeta

# 导入必要的依赖
import bot_core.services.utils.usage as fm
from agent.llm_functions import analyze_image_for_rating
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class FuckPlugin(BasePlugin):
    """图片评分插件
    
    该插件用于分析用户回复的图片消息，并生成一个包含评分和评价的回复。
    支持分析图片、贴纸和GIF，可以通过添加 'hard' 参数启用更激进的评价模式。
    
    命令格式:
        /fuck - 普通评价模式
        /fuck hard - 激进评价模式
    
    使用方法:
        回复一条包含图片、贴纸或GIF的消息，然后发送 /fuck 命令
    """
    
    def __init__(self):
        super().__init__()
        self.meta = PluginMeta(
            name="fuck",
            version="1.0.0",
            description="图片评分插件，分析图片并给出评价",
            author="CyberWaifu Bot Team",
            trigger="fuck",
            command_type="group",
            menu_text="Fuck or not!",
            show_in_menu=True,
            menu_weight=0
        )
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/fuck命令，分析用户回复的图片消息。"""
        # 检查是否是回复消息
        if not update.message.reply_to_message:
            await update.message.reply_text("请回复一条包含图片的消息来使用此命令。")
            return

        replied_message = update.message.reply_to_message

        # 检查回复的消息是否包含图片、贴纸或GIF
        if not (
            replied_message.photo
            or replied_message.sticker
            or replied_message.animation
        ):
            await update.message.reply_text(
                "请回复一条包含图片、贴纸或GIF的消息来使用此命令。"
            )
            return

        # 解析命令参数
        command_args = context.args if context.args else []
        hard_mode = "hard" in command_args

        # 发送占位消息，回复原始图片所在的消息
        placeholder_msg = await replied_message.reply_text("正在分析，请稍候...")

        # 创建异步任务处理后续逻辑
        asyncio.create_task(
            self._process_fuck_analysis(
                update, context, placeholder_msg, replied_message, hard_mode
            )
        )
    
    async def _process_fuck_analysis(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        placeholder_msg,
        replied_message,
        hard_mode: bool = False,
    ) -> None:
        """处理图片分析的异步逻辑

        Args:
            update: Telegram 更新对象。
            context: 上下文对象。
            placeholder_msg: 占位消息对象。
            replied_message: 被回复的消息对象。
            hard_mode: 是否启用hard模式。
        """
        try:
            user_id = update.message.from_user.id
            group_id = update.message.chat.id

            file_id = None
            # 确定file_id
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

            # 下载并转换图片
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
            
            # 调用重构后的函数
            response, llm_messages = await analyze_image_for_rating(
                base64_data=base64_data,
                mime_type="image/jpeg",
                hard_mode=hard_mode,
                parse_mode="html",
            )

            # 更新使用记录
            logger.info("用户%s在群聊%s调用了fuck命令", user_id, group_id)
            fm.update_user_usage(group_id, str(llm_messages), response, "group_photo")

            # 保存AI回复为txt文件
            txt_filename = f"{base_filename}.txt"
            txt_filepath = os.path.join(pics_dir, txt_filename)
            with open(txt_filepath, "w", encoding="utf-8") as f:
                f.write(response)

            # 编辑占位消息
            await context.bot.edit_message_text(
                text=response,
                chat_id=group_id,
                message_id=placeholder_msg.message_id,
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error(f"图片分析失败: {e}", exc_info=True)
            try:
                await context.bot.edit_message_text(
                    text=f"图片分析失败：{str(e)}",
                    chat_id=update.message.chat.id,
                    message_id=placeholder_msg.message_id,
                )
            except Exception as ex:
                logger.error(f"编辑占位消息失败: {ex}")
                await replied_message.reply_text(f"图片分析失败：{str(e)}")

    async def _image_to_base64(self, filepath: str) -> str:
        """将图片文件转换为base64编码。

        Args:
            filepath: 图片文件路径。

        Returns:
            str: base64编码的图片数据。
        """
        import base64

        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(
                image_file.read()).decode("utf-8")
        return encoded_string