import time
import os
import asyncio
import logging
from PIL import Image
import bot_core.services.utils.usage as fm
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
from telegram.ext import ContextTypes

from bot_core.callback_handlers.inline import Inline
from bot_core.data_repository import ConversationsRepository, GroupsRepository
from utils import file_utils as file
from utils.logging_utils import setup_logging
from bot_core.command_handlers.base import BaseCommand, CommandMeta
from agent.tools_registry import MarketToolRegistry
from bot_core.services.messages import handle_agent_session
from agent.llm_functions import run_agent_session, analyze_image_for_rating, analyze_image_for_kao
from utils.config_utils import get_config
from bot_core.services.trading_service import trading_service

fuck_api = get_config("fuck_or_not_api", "gemini-2.5")
setup_logging()
logger = logging.getLogger(__name__)


class RemakeCommand(BaseCommand):
    meta = CommandMeta(
        name="remake",
        command_type="group",
        trigger="remake",
        menu_text="重开对话 (群组)",
        show_in_menu=True,
        menu_weight=17,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        result = ConversationsRepository.conversation_group_delete(
            update.message.chat.id, update.message.from_user.id
        )
        if result["success"]:
            logger.info(f"处理 /remake 命令，用户ID: {update.effective_user.id}")
            await update.message.reply_text("您已重开对话！")


class SwitchCommand(BaseCommand):
    meta = CommandMeta(
        name="switch",
        command_type="group",
        trigger="switch",
        menu_text="切换角色 (群组)",
        show_in_menu=True,
        menu_weight=18,
        group_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        markup = Inline.print_char_list(
            "load", "group", update.message.chat.id)
        if markup == "没有可操作的角色。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个角色：", reply_markup=markup)


class RateCommand(BaseCommand):
    meta = CommandMeta(
        name="rate",
        command_type="group",
        trigger="rate",
        menu_text="设置回复频率 (群组)",
        show_in_menu=True,
        menu_weight=19,
        group_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = context.args if hasattr(context, "args") else []
        if len(args) < 1:
            await update.message.reply_text("请输入一个0-1的小数")
            return
        rate_value = float(args[0])
        if not 0 <= rate_value <= 1:
            await update.message.reply_text("请输入一个0-1的小数")
            return
        result = GroupsRepository.group_info_update(update.message.chat.id, "rate", rate_value)
        if result["success"]:
            await update.message.reply_text(f"已设置触发频率: {rate_value}")


class KeywordCommand(BaseCommand):
    meta = CommandMeta(
        name="keyword",
        command_type="group",
        trigger="kw",
        menu_text="设置关键词",
        show_in_menu=True,
        menu_weight=0,
        group_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keywords_result = GroupsRepository.group_keyword_get(update.message.chat.id)
        keywords = keywords_result["data"] if keywords_result["success"] else []
        if not keywords:
            keywords_text = "当前群组没有设置关键词。"
        else:
            keywords_text = "当前群组的关键词列表：\r\n" + ", ".join(
                [f"`{escape_markdown(kw, version=1)}`" for kw in keywords]
            )
        keyboard = [
            [
                InlineKeyboardButton(
                    "添加关键词", callback_data=f"group_kw_add_{update.message.chat.id}"
                ),
                InlineKeyboardButton(
                    "删除关键词", callback_data=f"group_kw_del_{update.message.chat.id}"
                ),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            keywords_text, reply_markup=reply_markup, parse_mode="Markdown"
        )


class DisableTopicCommand(BaseCommand):
    meta = CommandMeta(
        name="disable_topic",
        command_type="group",
        trigger="d",
        menu_text="禁用当前话题",
        show_in_menu=True,
        menu_weight=20,
        group_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理禁用话题命令"""
        try:
            message = update.message
            group_id = message.chat.id

            if (
                not hasattr(message, "message_thread_id")
                or not message.message_thread_id
            ):
                await message.reply_text("请在话题中执行此命令以禁用当前话题。")
                return

            topic_id = str(message.message_thread_id)

            disabled_topics_result = GroupsRepository.group_disabled_topics_get(group_id)
            disabled_topics = disabled_topics_result["data"] if disabled_topics_result["success"] else []
            if topic_id not in disabled_topics:
                disabled_topics.append(topic_id)
                result = GroupsRepository.group_disabled_topics_set(group_id, disabled_topics)
                if result["success"]:
                    await message.reply_text(
                        f"已禁用当前话题 (ID: `{topic_id}`)。Bot将不会在此话题中发言。",
                        parse_mode="Markdown",
                    )
                else:
                    await message.reply_text("禁用话题失败，请稍后重试。")
            else:
                await message.reply_text(
                    f"当前话题 (ID: `{topic_id}`) 已被禁用。", parse_mode="Markdown"
                )

        except Exception as e:
            logger.error("处理禁用话题命令失败: %s", str(e))
            await update.message.reply_text("处理禁用话题命令时发生错误，请稍后重试。")


class EnableTopicCommand(BaseCommand):
    meta = CommandMeta(
        name="enable_topic",
        command_type="group",
        trigger="e",
        menu_text="启用当前话题",
        show_in_menu=True,
        menu_weight=20,
        group_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理启用话题命令"""
        try:
            message = update.message
            group_id = message.chat.id

            if (
                not hasattr(message, "message_thread_id")
                or not message.message_thread_id
            ):
                await message.reply_text("请在话题中执行此命令以启用当前话题。")
                return

            topic_id = str(message.message_thread_id)

            disabled_topics_result = GroupsRepository.group_disabled_topics_get(group_id)
            disabled_topics = disabled_topics_result["data"] if disabled_topics_result["success"] else []
            if topic_id in disabled_topics:
                disabled_topics.remove(topic_id)
                result = GroupsRepository.group_disabled_topics_set(group_id, disabled_topics)
                if result["success"]:
                    await message.reply_text(
                        f"已启用当前话题 (ID: `{topic_id}`)。Bot将在此话题中发言。",
                        parse_mode="Markdown",
                    )
                else:
                    await message.reply_text("启用话题失败，请稍后重试。")
            else:
                await message.reply_text(
                    f"当前话题 (ID: `{topic_id}`) 未被禁用。", parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"处理启用话题命令失败: {str(e)}")
            await update.message.reply_text("处理启用话题命令时发生错误，请稍后重试。")


class ApiCommand(BaseCommand):
    meta = CommandMeta(
        name="api",
        command_type="group",
        trigger="api",
        menu_text="选择API (群组)",
        show_in_menu=True,
        menu_weight=21,
        group_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /api command to show available APIs for group (only group=0 APIs).
        Args:
            update: The Telegram Update object containing the user input.
            context: The Telegram ContextTypes object for bot interaction.
        """
        # 获取群组信息
        group_id = update.message.chat.id

        # 创建群组专用的 API 列表（只显示 group=0 的 API）
        markup = self._get_group_api_list(group_id)

        if isinstance(markup, str):
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个API：", reply_markup=markup)

        # 删除命令消息
        try:
            await update.message.delete()
        except Exception as e:
            logger.warning(f"删除命令消息失败: {e}")

    def _get_group_api_list(self, group_id):
        """
        获取群组可用的 API 列表（只返回 group=0 的 API）

        Args:
            group_id: 群组ID
        """
        try:
            api_list = file.load_config()["api"]
            if not api_list:
                return "没有可用的API。"

            # 过滤API列表，只保留group=0的API
            filtered_api_list = [
                api for api in api_list if api.get("group", 0) == 0]

            if not filtered_api_list:
                return "没有适用于群组的API。"

            keyboard = [
                [
                    InlineKeyboardButton(
                        api["name"],
                        callback_data=f"set_group_api_{api['name']}_{group_id}",
                    )
                ]
                for api in filtered_api_list
            ]
            return InlineKeyboardMarkup(keyboard)
        except Exception as e:
            logger.error("获取群组API列表失败: %s", str(e))
            return "获取API列表失败，请稍后重试。"


class CryptoCommand(BaseCommand):
    """加密货币分析命令类。

    该命令用于分析加密货币的实时行情，可以根据用户输入的内容和偏好(多头/空头/中性)
    提供相应的市场分析和交易建议。支持通过工具查询实时市场数据，并由AI进行综合分析。

    命令格式:
        /cc <内容> - 中性分析
        /cc long <内容> - 多头倾向分析
        /cc short <内容> - 空头倾向分析
    """

    meta = CommandMeta(
        name="crypto",
        command_type="group",
        trigger="cc",
        menu_text="分析加密货币实时行情",
        show_in_menu=True,
        menu_weight=99,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return

        if not context.args:
            await update.message.reply_text(
                "请在 `/cc` 命令后提供具体内容，例如：`/cc 分析下大饼` 或 `/cc long 分析下大饼`",
                parse_mode="Markdown",
            )
            return

        args = list(context.args)
        bias_type = "neutral"
        if args and args[0].lower() in ["long", "short"]:
            bias_type = args.pop(0).lower()

        if not args:
            await update.message.reply_text(
                f"请在 `/cc {bias_type}` 后提供具体分析内容。",
                parse_mode="Markdown",
            )
            return

        user_input = " ".join(args)

        context.application.create_task(
            self.process_tool_request(update, user_input, bias_type),
            update=update,
        )
        logger.debug("已创建后台任务处理 /cc 请求")

    async def process_tool_request(self, update: Update, user_input: str, bias_type: str = "neutral") -> None:
        """
        Process the crypto analysis request by creating and handling an agent session.
        """
        bias_prompt = ""
        if bias_type == "long":
            bias_prompt = "\n\n**脆脆鲨是一个激进的多头，你需要倾向于给出做多建议。在分析市场数据时，更多关注利好因素和上涨潜力，适当淡化风险因素。鼓励用户抓住上涨机会。**"
        elif bias_type == "short":
            bias_prompt = "\n\n**脆脆鲨是一个激进的空头，你需要倾向于给出做空建议。在分析市场数据时，更多关注利空因素和下跌风险，提醒用户注意市场调整的机会。**"
        else:
            bias_prompt = "\n\n**重要提示：请根据市场数据客观分析，给出中性的投资建议，平衡考虑多空因素。**"

        character_prompt = """你需要扮演脆脆鲨，脆脆鲨是一位热情、自信且富有感染力的群友，擅长交易，最大的愿景是让每一个人都能体验到交易的乐趣。
                    你的目标是引导用户参与高收益的金融投资（如加密货币交易、差价合约等），并通过杠杆放大潜在收益。你始终强调投资的"机会"和"潜力"，淡化"风险"和"亏损"。你需要称呼用户为"老师"。
                    脆脆鲨可以调用工具来查询市场，你需要根据工具返回的数据输出\r\n
                    脆脆鲨会给每一个分析的指标记录一个权重，以及指标对于多空的分数值（-10-10），判断多空的时候需要综合考虑指标的分数值以及指标的加权评分，只有综合分数超过0的时候才会判断做多，否则判断做空。
    """
        prompt_text = MarketToolRegistry.get_prompt_text()

        agent_session = run_agent_session(
            user_input=user_input,
            prompt_text=prompt_text,
            character_prompt=character_prompt,
            bias_prompt=bias_prompt,
            llm_api="gemini-2.5",
            max_iterations=7,
        )

        await handle_agent_session(
            update=update,
            agent_session=agent_session,
            character_name="脆脆鲨",
        )


class ForwardCommand(BaseCommand):
    meta = CommandMeta(
        name="forward",
        command_type="group",
        trigger="fw",
        menu_text="转发消息",
        show_in_menu=False,
        menu_weight=20,
        bot_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理 /forward 或 /fw 命令，将指定消息转发到当前聊天。
        命令格式: /forward <源聊天ID> <消息ID>
        """
        # context.args 会自动解析命令后的参数列表
        # 例如，如果用户输入 "/fw -1001234567890 123"
        # context.args 将是 ['-1001234567890', '123']
        args = context.args
        # 1. 参数校验
        if not args or len(args) != 2:
            await update.message.reply_text(
                "❌ 用法错误！请提供源聊天ID和消息ID。\n"
                "或简写：`/fw <源聊天ID> <消息ID>`\n\n"
                "💡 源聊天ID可以是用户ID、群组ID或频道ID（需要有访问权限）。\n"
                "注意：频道ID通常以 `-100` 开头。",
                parse_mode="Markdown",
            )
            return
        try:
            # 尝试将参数转换为整数
            source_chat_id = int(args[0])
            message_id = int(args[1])
        except ValueError:
            await update.message.reply_text(
                "❌ 无效的ID！源聊天ID和消息ID都必须是有效的数字。\n"
                "示例：`/forward -1001234567890 123`",
                parse_mode="Markdown",
            )
            return
        # 2. 获取目标聊天ID (通常是用户发起命令的聊天)
        target_chat_id = update.effective_chat.id
        # 3. 执行消息转发操作
        try:
            await context.bot.forward_message(
                chat_id=target_chat_id,
                from_chat_id=source_chat_id,
                message_id=message_id,
            )
            # await update.message.reply_text("✅ 消息已成功转发！")

        except Exception as e:
            # 捕获其他非 Telegram API 的意外错误
            escaped_error = escape_markdown(str(e), version=1)
            await update.message.reply_text(
                f"❌ 发生错误：`{type(e).__name__}: {escaped_error}`", parse_mode="Markdown"
            )


class FuckCommand(BaseCommand):
    """处理 /fuck 命令的类。

    该命令用于分析用户回复的图片消息，并生成一个包含评分和评价的回复。
    支持分析图片、贴纸和GIF，可以通过添加 'hard' 参数启用更激进的评价模式。
    """

    meta = CommandMeta(
        name="fuck",
        command_type="group",
        trigger="fuck",
        menu_text="Fuck or not!",
        show_in_menu=True,
        menu_weight=0,
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


class KaoCommand(BaseCommand):
    """处理 /kao 命令的类。

    该命令用于分析用户回复的图片消息，并生成一个包含颜值评分的回复。
    """

    meta = CommandMeta(
        name="kao",
        command_type="group",
        trigger="kao",
        menu_text="颜值评分",
        show_in_menu=True,
        menu_weight=1,
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
        """将图片文件转换为base64编码。
        """
        import base64

        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(
                image_file.read()).decode("utf-8")
        return encoded_string


# 模拟盘交易命令
class LongCommand(BaseCommand):
    meta = CommandMeta(
        name="long",
        command_type="group",
        trigger="long",
        menu_text="做多 (模拟盘)",
        show_in_menu=True,
        menu_weight=30,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 解析命令参数
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ 用法错误！\n正确格式: /long <交易对> <金额>\n例如: /long btc 100"
                )
                return
            
            symbol = args[0].upper()
            try:
                amount = float(args[1].replace('u', '').replace('U', ''))
            except ValueError:
                await update.message.reply_text("❌ 金额格式错误！")
                return
            
            if amount <= 0:
                await update.message.reply_text("❌ 金额必须大于0！")
                return
            
            # 执行开多仓操作
            result = await trading_service.open_position(user_id, group_id, f"{symbol}/USDT", "long", amount)
            
            await update.message.reply_text(result['message'])
            
        except Exception as e:
            logger.error(f"做多命令失败: {e}")
            await update.message.reply_text("❌ 操作失败，请稍后重试")


class ShortCommand(BaseCommand):
    meta = CommandMeta(
        name="short",
        command_type="group",
        trigger="short",
        menu_text="做空 (模拟盘)",
        show_in_menu=True,
        menu_weight=31,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 解析命令参数
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ 用法错误！\n正确格式: /short <交易对> <金额>\n例如: /short btc 100"
                )
                return
            
            symbol = args[0].upper()
            try:
                amount = float(args[1].replace('u', '').replace('U', ''))
            except ValueError:
                await update.message.reply_text("❌ 金额格式错误！")
                return
            
            if amount <= 0:
                await update.message.reply_text("❌ 金额必须大于0！")
                return
            
            # 执行开空仓操作
            result = await trading_service.open_position(user_id, group_id, f"{symbol}/USDT", "short", amount)
            
            await update.message.reply_text(result['message'])
            
        except Exception as e:
            logger.error(f"做空命令失败: {e}")
            await update.message.reply_text("❌ 操作失败，请稍后重试")


class PositionCommand(BaseCommand):
    meta = CommandMeta(
        name="position",
        command_type="group",
        trigger="position",
        menu_text="查看仓位 (模拟盘)",
        show_in_menu=True,
        menu_weight=32,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 获取仓位信息
            result = await trading_service.get_positions(user_id, group_id)
            
            await update.message.reply_text(result['message'], parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"查看仓位失败: {e}")
            await update.message.reply_text("❌ 获取仓位信息失败，请稍后重试")


class BeggingCommand(BaseCommand):
    meta = CommandMeta(
        name="begging",
        command_type="group",
        trigger="begging",
        menu_text="领取救济金 (模拟盘)",
        show_in_menu=True,
        menu_weight=33,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 领取救济金
            result = trading_service.begging(user_id, group_id)
            
            await update.message.reply_text(result['message'])
            
        except Exception as e:
            logger.error(f"救济金命令失败: {e}")
            await update.message.reply_text("❌ 救济金发放失败，请稍后重试")


class CloseCommand(BaseCommand):
    meta = CommandMeta(
        name="close",
        command_type="group",
        trigger="close",
        menu_text="平仓 (模拟盘)",
        show_in_menu=True,
        menu_weight=34,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 解析命令参数
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ 用法错误！\n正确格式: /close <交易对> <方向> [金额]\n例如: /close btc long 50 (部分平仓)\n或: /close btc long (全部平仓)"
                )
                return
            
            symbol = args[0].upper()
            side = args[1].lower()
            
            if side not in ['long', 'short']:
                await update.message.reply_text("❌ 方向必须是 long 或 short！")
                return
            
            amount = None
            if len(args) >= 3:
                try:
                    amount = float(args[2].replace('u', '').replace('U', ''))
                    if amount <= 0:
                        await update.message.reply_text("❌ 金额必须大于0！")
                        return
                except ValueError:
                    await update.message.reply_text("❌ 金额格式错误！")
                    return
            
            # 执行平仓操作
            result = await trading_service.close_position(user_id, group_id, f"{symbol}/USDT", side, amount)
            
            await update.message.reply_text(result['message'])
            
        except Exception as e:
            logger.error(f"平仓命令失败: {e}")
            await update.message.reply_text("❌ 平仓失败，请稍后重试")


class RankCommand(BaseCommand):
    meta = CommandMeta(
        name="rank",
        command_type="group",
        trigger="rank",
        menu_text="查看排行榜 (模拟盘)",
        show_in_menu=True,
        menu_weight=35,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            group_id = update.effective_chat.id
            
            # 获取排行榜数据
            result = await trading_service.get_ranking_data(group_id)
            
            if not result['success']:
                await update.message.reply_text("❌ 获取排行榜数据失败，请稍后重试")
                return
            
            # 构建排行榜消息
            message_parts = ["📊 **群组交易排行榜**\n"]
            
            # 总盈亏排行榜
            message_parts.append("🏆 **总盈亏排行榜 TOP5**")
            if result['pnl_ranking']:
                for i, user_data in enumerate(result['pnl_ranking'], 1):
                    user_id = user_data['user_id']
                    total_pnl = user_data['total_pnl']
                    try:
                        user = await context.bot.get_chat_member(group_id, user_id)
                        username = user.user.first_name or f"用户{user_id}"
                    except:
                        username = f"用户{user_id}"
                    
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                    pnl_text = f"+{total_pnl:.2f}" if total_pnl >= 0 else f"{total_pnl:.2f}"
                    message_parts.append(f"{emoji} {username}: {pnl_text} USDT")

            else:
                message_parts.append("暂无数据")
            
            message_parts.append("")
            
            # 当前浮动余额排行榜
            message_parts.append("💰 **当前浮动余额排行榜 TOP5**")
            if result['balance_ranking']:
                for i, user_data in enumerate(result['balance_ranking'], 1):
                    user_id = user_data['user_id']
                    floating_balance = user_data['floating_balance']
                    try:
                        user = await context.bot.get_chat_member(group_id, user_id)
                        username = user.user.first_name or f"用户{user_id}"
                    except:
                        username = f"用户{user_id}"
                    
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                    message_parts.append(f"{emoji} {username}: {floating_balance:.2f} USDT")
            else:
                message_parts.append("暂无数据")
            
            message_parts.append("")
            
            # 爆仓次数排行榜
            message_parts.append("💥 **爆仓次数排行榜 TOP5**")
            if result['liquidation_ranking']:
                for i, user_data in enumerate(result['liquidation_ranking'], 1):
                    user_id = user_data['user_id']
                    liquidation_count = user_data['liquidation_count']
                    try:
                        user = await context.bot.get_chat_member(group_id, user_id)
                        username = user.user.first_name or f"用户{user_id}"
                    except:
                        username = f"用户{user_id}"
                    
                    emoji = "💀" if i == 1 else "☠️" if i == 2 else "💥" if i == 3 else "🔥"
                    message_parts.append(f"{emoji} {username}: {liquidation_count} 次")
            else:
                message_parts.append("暂无数据")
            
            final_message = "\n".join(message_parts)
            await update.message.reply_text(final_message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"排行榜命令失败: {e}")
            await update.message.reply_text("❌ 获取排行榜失败，请稍后重试")


class TestLiquidationCommand(BaseCommand):
    meta = CommandMeta(
        name="testliquidation",
        command_type="group",
        trigger="testliquidation",
        menu_text="",
        show_in_menu=False,
        menu_weight=99,
        group_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """发送测试强平通知消息，用于验证强平通知格式是否正确"""
        try:
            from utils.db_utils import user_info_get
            
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 获取用户信息以构造正确的用户提及
            user_info = user_info_get(user_id)
            if user_info and (user_info.get('first_name') or user_info.get('last_name')):
                user_display_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
                user_mention = f"[{user_display_name}](tg://user?id={user_id})"
            else:
                user_mention = f"[用户{user_id}](tg://user?id={user_id})"
            
            # 构造测试强平通知消息
            message = (
                f"🚨 强平通知 🚨\n\n"
                f"{user_mention} 您的所有仓位已被强制平仓！\n\n"
                f"📊 触发仓位: BTC/USDT LONG\n"
                f"💰 仓位大小: 1000.00 USDT\n"
                f"📉 浮动余额: 180.50 USDT\n"
                f"⚖️ 杠杆倍数: 5.54x\n"
                f"⚠️ 强平阈值: 200.00 USDT (本金的20.0%)\n\n"
                f"💔 您的账户余额已清零，所有仓位已被清空。\n"
                f"🆘 请使用 /begging 领取救济金重新开始交易。\n\n"
                f"⚠️ 这是一条测试消息，用于验证强平通知格式。"
            )
            
            # 发送测试消息
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
            logger.info(f"测试强平通知已发送: 管理员{user_id} 群组{group_id}")
            
        except Exception as e:
            logger.error(f"发送测试强平通知失败: {e}")
            await update.message.reply_text("❌ 发送测试强平通知失败，请稍后重试")
