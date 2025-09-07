import asyncio
import os
import time
import base64
import json
import re
import logging
from typing import Tuple, List, Dict, Any
from PIL import Image
from telegram import Update
from telegram.ext import ContextTypes

# 导入插件基类
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from bot_core.services.plugin_service import BasePlugin, PluginMeta

# 导入必要的依赖
import bot_core.services.utils.usage as fm
from utils.logging_utils import setup_logging
from utils.config_utils import get_config
from utils import file_utils, LLM_utils

setup_logging()
logger = logging.getLogger(__name__)


async def analyze_image_for_rating(
    base64_data: str,
    mime_type: str,
    hard_mode: bool = False,
    parse_mode: str = "markdown",
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    分析图像的base64数据，并返回分析结果和消息历史。

    Args:
        base64_data (str): 图像的base64编码数据。
        mime_type (str): 图像的MIME类型。
        hard_mode (bool): 是否启用更激进的评价模式。
        parse_mode (str): 输出格式，可以是 'markdown' 或 'html'。

    Returns:
        Tuple[str, List[Dict[str, Any]]]: 包含格式化响应和发送给LLM的消息列表的元组。

    Raises:
        ValueError: 如果缺少必要的 prompt 或数据。
    """


    prompt_name = "fuck_or_not_group" if parse_mode == "html" else "fuck_or_not"
    system_prompt = file_utils.load_single_prompt(prompt_name)
    if not system_prompt:
        raise ValueError(f"无法加载 '{prompt_name}' prompt。")

    if hard_mode:
        hard_supplement = file_utils.load_single_prompt("fuck_or_not_hard_mode_supplement")
        if hard_supplement:
            system_prompt += hard_supplement

    user_text = "兄弟看看这个，你想不想操？"
    if hard_mode:
        user_text += "（请使用最极端和粗俗的语言进行评价）"

    llm_messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_data}"},
                },
            ],
        },
    ]

    fuck_api = get_config("fuck_or_not_api", "gemini-2.5")
    llm = LLM_utils.LLM(api=fuck_api)
    llm.set_messages(llm_messages)
    response = await llm.final_response()

    try:
        match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
        json_str = match.group(1) if match else response
        data = json.loads(json_str)

        if parse_mode == "html":
            score = data.get("score", "N/A")
            reason_short = data.get("reason_short", "N/A")
            reason_detail = data.get("reason_detail", "N/A")
            fantasy_short = data.get("fantasy_short", "N/A")
            fantasy_detail = data.get("fantasy_detail", "N/A")
            formatted_response = (
                " <b>分析结果</b> \n\n"
                f"<b>评分</b>: {score}/10\n\n"
                f"<b>理由</b>: {reason_short}\n"
                f"<blockquote expandable>{reason_detail}</blockquote>\n\n"
                f"<b>评价</b>: {fantasy_short}\n"
                f"<blockquote expandable>{fantasy_detail}</blockquote>"
            )
        else:  # markdown
            score = data.get("score", "N/A")
            reason = data.get("reason", "N/A")
            fantasy = data.get("fantasy", "N/A")
            formatted_response = f"```\n分数：{score}\n```\n\n理由：{reason}\n\n评价：{fantasy}"
        
        return formatted_response, llm_messages
        
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"解析LLM JSON响应失败: {e}。将使用原始响应。")
        return response, llm_messages


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