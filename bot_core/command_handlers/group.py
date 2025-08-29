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
from bot_core.services.messages import handle_agent_session, MessageDeletionService, RealTimePositionService
from agent.llm_functions import run_agent_session, analyze_image_for_rating, analyze_image_for_kao
from utils.config_utils import get_config

# 导入新的交易服务模块（增强的订单驱动系统）
from bot_core.services.trading.order_service import order_service
from bot_core.services.trading.account_service import account_service
from bot_core.services.trading.position_service import position_service
from bot_core.services.trading.analysis_service import analysis_service
from bot_core.services.trading.loan_service import loan_service

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
                    "❌ 用法错误！\n正确格式: \n"
                    "市价开仓: /long <交易对> <金额>\n"
                    "挂单开仓: /long <交易对> <金额>@<价格>\n"
                    "带止盈止损: /long <交易对> <金额>@<价格> tp@<止盈价> sl@<止损价>\n"
                    "批量开仓: /long <币种1> <币种2> <币种3> <金额>\n"
                    "例如: /long btc 100 或 /long btc 4000@100000 tp@120000 sl@90000"
                )
                return

            # 解析参数，支持新的订单格式
            parsed_args = self._parse_trading_args(args)
            
            if not parsed_args['success']:
                await update.message.reply_text(f"❌ {parsed_args['error']}")
                return
            
            # 检查是否为批量开仓（简化版，只支持市价）
            if parsed_args['is_batch']:
                results = []
                for symbol, amount in zip(parsed_args['symbols'], parsed_args['amounts']):
                    result = await order_service.create_market_order(
                        user_id, group_id, f"{symbol}/USDT", "long", "open", amount
                    )
                    results.append(f"{symbol}: {result['message']}")

                response = "📈 批量做多结果:\n" + "\n".join(results)
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=response,
                    delay_seconds=30,
                    delete_user_message=True
                )
            else:
                # 单个开仓模式
                symbol = parsed_args['symbol']
                amount = parsed_args['amount']
                price = parsed_args.get('price')
                tp_price = parsed_args.get('tp_price')
                sl_price = parsed_args.get('sl_price')
                
                if price:
                    # 挂单模式
                    result = await order_service.create_limit_order(
                        user_id, group_id, f"{symbol}/USDT", "long", "open", amount, price
                    )
                    
                    # 如果挂单成功且有止盈止损设置，创建止盈止损订单
                    if result['success'] and (tp_price or sl_price):
                        order_id = result.get('order_id')
                        if tp_price:
                            await order_service.create_limit_order(
                                user_id, group_id, f"{symbol}/USDT", "short", "tp", amount, tp_price
                            )
                        if sl_price:
                            await order_service.create_market_order(
                                user_id, group_id, f"{symbol}/USDT", "short", "sl", amount
                            )
                else:
                    # 市价单模式
                    result = await order_service.create_market_order(
                        user_id, group_id, f"{symbol}/USDT", "long", "open", amount
                    )
                    
                    # 如果市价单成功且有止盈止损设置，创建止盈止损订单
                    if result['success'] and (tp_price or sl_price):
                        if tp_price:
                            await order_service.create_limit_order(
                                user_id, group_id, f"{symbol}/USDT", "short", "tp", amount, tp_price
                            )
                        if sl_price:
                            await order_service.create_market_order(
                                user_id, group_id, f"{symbol}/USDT", "short", "sl", amount
                            )
                
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=result['message'],
                    delay_seconds=10,
                    delete_user_message=True
                )

        except Exception as e:
            logger.error(f"做多命令失败: {e}")
            await update.message.reply_text("❌ 操作失败，请稍后重试")
    
    def _parse_trading_args(self, args):
        """解析交易参数，支持新的订单格式"""
        try:
            # 检查是否为批量模式（简化判断）
            if len(args) >= 3 and not '@' in ' '.join(args):
                # 批量模式：/long btc eth xrp 5000
                try:
                    last_amount = float(args[-1].replace('u', '').replace('U', ''))
                    if last_amount > 0:
                        symbols = [arg.upper() for arg in args[:-1]]
                        amounts = [last_amount] * len(symbols)
                        return {
                            'success': True,
                            'is_batch': True,
                            'symbols': symbols,
                            'amounts': amounts
                        }
                except ValueError:
                    pass
            
            # 单个订单模式
            if len(args) < 2:
                return {'success': False, 'error': '参数不足'}
            
            symbol = args[0].upper()
            amount_str = args[1]
            
            # 解析金额和价格
            if '@' in amount_str:
                # 挂单模式：btc 4000@100000
                amount_part, price_part = amount_str.split('@', 1)
                amount = float(amount_part.replace('u', '').replace('U', ''))
                price = float(price_part)
            else:
                # 市价模式：btc 4000
                amount = float(amount_str.replace('u', '').replace('U', ''))
                price = None
            
            if amount <= 0:
                return {'success': False, 'error': '金额必须大于0'}
            
            # 解析止盈止损
            tp_price = None
            sl_price = None
            
            for arg in args[2:]:
                if arg.startswith('tp@'):
                    tp_price = float(arg[3:])
                elif arg.startswith('sl@'):
                    sl_price = float(arg[3:])
            
            return {
                'success': True,
                'is_batch': False,
                'symbol': symbol,
                'amount': amount,
                'price': price,
                'tp_price': tp_price,
                'sl_price': sl_price
            }
            
        except ValueError as e:
            return {'success': False, 'error': f'参数格式错误: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'解析失败: {str(e)}'}



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
                    "❌ 用法错误！\n正确格式: \n"
                    "市价开仓: /short <交易对> <金额>\n"
                    "挂单开仓: /short <交易对> <金额>@<价格>\n"
                    "带止盈止损: /short <交易对> <金额>@<价格> tp@<止盈价> sl@<止损价>\n"
                    "批量开仓: /short <币种1> <币种2> <币种3> <金额>\n"
                    "例如: /short btc 100 或 /short btc 4000@90000 tp@80000 sl@95000"
                )
                return
            
            # 解析参数，支持新的订单格式
            parsed_args = self._parse_trading_args(args)
            
            if not parsed_args['success']:
                await update.message.reply_text(f"❌ {parsed_args['error']}")
                return
            
            # 检查是否为批量开仓（简化版，只支持市价）
            if parsed_args['is_batch']:
                results = []
                for symbol, amount in zip(parsed_args['symbols'], parsed_args['amounts']):
                    result = await order_service.create_market_order(
                        user_id, group_id, f"{symbol}/USDT", "short", "open", amount
                    )
                    results.append(f"{symbol}: {result['message']}")
                
                response = "📉 批量做空结果:\n" + "\n".join(results)
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=response,
                    delay_seconds=30,
                    delete_user_message=True
                )
            else:
                # 单个开仓模式
                symbol = parsed_args['symbol']
                amount = parsed_args['amount']
                price = parsed_args.get('price')
                tp_price = parsed_args.get('tp_price')
                sl_price = parsed_args.get('sl_price')
                
                if price:
                    # 挂单模式
                    result = await order_service.create_limit_order(
                        user_id, group_id, f"{symbol}/USDT", "short", "open", amount, price
                    )
                    
                    # 如果挂单成功且有止盈止损设置，创建止盈止损订单
                    if result['success'] and (tp_price or sl_price):
                        order_id = result.get('order_id')
                        if tp_price:
                            await order_service.create_limit_order(
                                user_id, group_id, f"{symbol}/USDT", "long", "tp", amount, tp_price
                            )
                        if sl_price:
                            await order_service.create_market_order(
                                user_id, group_id, f"{symbol}/USDT", "long", "sl", amount
                            )
                else:
                    # 市价单模式
                    result = await order_service.create_market_order(
                        user_id, group_id, f"{symbol}/USDT", "short", "open", amount
                    )
                    
                    # 如果市价单成功且有止盈止损设置，创建止盈止损订单
                    if result['success'] and (tp_price or sl_price):
                        if tp_price:
                            await order_service.create_limit_order(
                                user_id, group_id, f"{symbol}/USDT", "long", "tp", amount, tp_price
                            )
                        if sl_price:
                            await order_service.create_market_order(
                                user_id, group_id, f"{symbol}/USDT", "long", "sl", amount
                            )
                
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=result['message'],
                    delay_seconds=10,
                    delete_user_message=True
                )
            
        except Exception as e:
            logger.error(f"做空命令失败: {e}")
            await update.message.reply_text("❌ 操作失败，请稍后重试")
    
    def _parse_trading_args(self, args):
        """解析交易参数，支持新的订单格式"""
        try:
            # 检查是否为批量模式（简化判断）
            if len(args) >= 3 and not '@' in ' '.join(args):
                # 批量模式：/short btc eth xrp 5000
                try:
                    last_amount = float(args[-1].replace('u', '').replace('U', ''))
                    if last_amount > 0:
                        symbols = [arg.upper() for arg in args[:-1]]
                        amounts = [last_amount] * len(symbols)
                        return {
                            'success': True,
                            'is_batch': True,
                            'symbols': symbols,
                            'amounts': amounts
                        }
                except ValueError:
                    pass
            
            # 单个订单模式
            if len(args) < 2:
                return {'success': False, 'error': '参数不足'}
            
            symbol = args[0].upper()
            amount_str = args[1]
            
            # 解析金额和价格
            if '@' in amount_str:
                # 挂单模式：btc 4000@90000
                amount_part, price_part = amount_str.split('@', 1)
                amount = float(amount_part.replace('u', '').replace('U', ''))
                price = float(price_part)
            else:
                # 市价模式：btc 4000
                amount = float(amount_str.replace('u', '').replace('U', ''))
                price = None
            
            if amount <= 0:
                return {'success': False, 'error': '金额必须大于0'}
            
            # 解析止盈止损
            tp_price = None
            sl_price = None
            
            for arg in args[2:]:
                if arg.startswith('tp@'):
                    tp_price = float(arg[3:])
                elif arg.startswith('sl@'):
                    sl_price = float(arg[3:])
            
            return {
                'success': True,
                'is_batch': False,
                'symbol': symbol,
                'amount': amount,
                'price': price,
                'tp_price': tp_price,
                'sl_price': sl_price
            }
            
        except ValueError as e:
            return {'success': False, 'error': f'参数格式错误: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'解析失败: {str(e)}'}



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

            # 使用新交易系统获取完整信息
            message = await self._get_enhanced_position_info(user_id, group_id)

            # 发送初始消息
            initial_message = await update.message.reply_text(
                RealTimePositionService._build_realtime_message(message, 120),
                parse_mode='HTML'
            )

            # 启动实时更新
            context.application.create_task(
                RealTimePositionService.start_realtime_update(
                    update=update,
                    context=context,
                    user_id=user_id,
                    group_id=group_id,
                    initial_message=initial_message
                )
            )

        except Exception as e:
            logger.error(f"查看仓位失败: {e}")
            await update.message.reply_text("❌ 获取仓位信息失败，请稍后重试")
    
    async def _get_enhanced_position_info(self, user_id: int, group_id: int) -> str:
        """获取增强的仓位信息，包括挂单和止盈止损"""
        try:
            # 获取账户信息
            account = account_service.get_or_create_account(user_id, group_id)
            
            # 获取持仓
            positions = await position_service.get_positions(user_id, group_id)
            
            # 获取所有挂单
            orders_result = order_service.get_orders(user_id, group_id, 'pending')
            all_orders = orders_result.get('orders', []) if orders_result.get('success') else []
            
            # 分类订单
            pending_orders = [order for order in all_orders if order.get('order_type') == 'open']
            tp_orders = [order for order in all_orders if order.get('order_type') == 'tp']
            sl_orders = [order for order in all_orders if order.get('order_type') == 'sl']
            
            # 构建消息
            message_parts = []
            
            # 账户信息
            if account:
                message_parts.append(f"💰 账户余额: {account['balance']:.2f} USDT")
                message_parts.append(f"📊 总盈亏: {account.get('total_pnl', 0.0):.2f} USDT")
                message_parts.append(f"🔒 冻结保证金: {account.get('frozen_margin', 0.0):.2f} USDT")
                message_parts.append("")
            
            # 持仓信息
            if positions:
                message_parts.append("📈 当前持仓:")
                for pos in positions:
                    # 计算未实现盈亏
                    from bot_core.services.trading.price_service import price_service
                    current_price = await price_service.get_current_price(pos['symbol'])
                    if current_price:
                        if pos['side'] == 'long':
                            unrealized_pnl = (current_price - pos['entry_price']) * (pos['size'] / pos['entry_price'])
                        else:
                            unrealized_pnl = (pos['entry_price'] - current_price) * (pos['size'] / pos['entry_price'])
                    else:
                        unrealized_pnl = 0.0
                    
                    pnl_emoji = "🟢" if unrealized_pnl >= 0 else "🔴"
                    side_emoji = "📈" if pos['side'] == 'long' else "📉"
                    message_parts.append(
                        f"{side_emoji} {pos['symbol']} | {pos['size']:.4f} | "
                        f"入场: {pos['entry_price']:.4f} | "
                        f"PnL: {pnl_emoji}{unrealized_pnl:.2f}"
                    )
                message_parts.append("")
            
            # 挂单信息
            if pending_orders:
                message_parts.append("⏳ 挂单:")
                for order in pending_orders:
                    side_emoji = "📈" if order.get('side') == 'long' else "📉"
                    message_parts.append(
                        f"{side_emoji} {order.get('symbol', 'N/A')} | {order.get('amount', 0):.2f} USDT | "
                        f"价格: {order.get('price', 0):.4f}"
                    )
                message_parts.append("")
            
            # 止盈止损订单
            if tp_orders or sl_orders:
                message_parts.append("🎯 止盈止损:")
                for order in tp_orders:
                    message_parts.append(
                        f"🎯 {order.get('symbol', 'N/A')} TP | 价格: {order.get('price', 0):.4f} | "
                        f"数量: {order.get('amount', 0):.4f}"
                    )
                for order in sl_orders:
                    message_parts.append(
                        f"🛡️ {order.get('symbol', 'N/A')} SL | 价格: {order.get('price', 0):.4f} | "
                        f"数量: {order.get('amount', 0):.4f}"
                    )
                message_parts.append("")
            
            if not positions and not pending_orders and not tp_orders and not sl_orders:
                message_parts.append("📭 暂无持仓或挂单")
            
            return "\n".join(message_parts)
            
        except Exception as e:
            logger.error(f"获取增强仓位信息失败: {e}")
            return "❌ 获取仓位信息失败"



class PnlCommand(BaseCommand):
    meta = CommandMeta(
        name="pnl",
        command_type="group",
        trigger="pnl",
        menu_text="盈亏报告 (模拟盘)",
        show_in_menu=True,
        menu_weight=33,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id

            # 获取盈亏报告
            result = await analysis_service.get_pnl_report(user_id, group_id)

            # 生成盈亏折线图 (暂时禁用，新版本暂未实现)
            chart_image = analysis_service.generate_pnl_chart(user_id, group_id)

            if chart_image:
                # 有图表时，发送图片，caption只显示最近交易
                # 解析盈亏报告，提取最近交易部分
                recent_trades = self._extract_recent_trades(result['message'])

                # 构建简短caption
                caption = f"📊 Trading PnL Chart\n\n{recent_trades}"

                # 确保caption不超过Telegram限制
                if len(caption) > 1024:
                    caption = caption[:1020] + "..."

                # 发送图片和定时删除
                await MessageDeletionService.send_photo_and_schedule_delete(
                    update=update,
                    context=context,
                    photo=chart_image,
                    caption=caption,
                    parse_mode='HTML',
                    delay_seconds=180,  # 盈亏报告保留5分钟
                    delete_user_message=True
                )
            else:
                # 没有图表时，只发送文本报告
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=result['message'],
                    parse_mode='HTML',
                    delay_seconds=180,  # 盈亏报告保留5分钟
                    delete_user_message=True
                )

        except Exception as e:
            logger.error(f"盈亏报告命令失败: {e}")
            await update.message.reply_text("❌ 获取盈亏报告失败，请稍后重试")

    def _extract_recent_trades(self, full_message: str) -> str:
        """从完整消息中提取最近交易部分（精简版）"""
        try:
            # 查找最近交易的部分
            if "最近15笔交易" in full_message:
                # 找到最近交易的开始位置
                start = full_message.find("📋 最近15笔交易")
                if start != -1:
                    # 只取最近5笔交易来缩短caption
                    trades_section = full_message[start:start+800]  # 限制长度
                    lines = trades_section.split('\n')

                    # 提取最近5笔交易记录
                    recent_trades = []
                    trade_count = 0
                    for line in lines:
                        if '|' in line and ('📈' in line or '📉' in line):  # 交易记录行
                            recent_trades.append(line.strip())
                            trade_count += 1
                            if trade_count >= 5:  # 只取最近5笔
                                break

                    if recent_trades:
                        return "Recent 5 Trades:\n" + "\n".join(recent_trades)
            elif "暂无交易记录" in full_message:
                return "No recent trades"
            else:
                # 如果找不到交易记录，返回简短摘要
                return "No recent trading activity"

        except Exception as e:
            logger.error(f"提取最近交易失败: {e}")
            return "Error extracting trades"



class BeggingCommand(BaseCommand):
    meta = CommandMeta(
        name="begging",
        command_type="group",
        trigger="begging",
        menu_text="领取救济金 (模拟盘)",
        show_in_menu=True,
        menu_weight=34,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 领取救济金
            result = loan_service.begging(user_id, group_id)

            await MessageDeletionService.send_and_schedule_delete(
                update=update,
                context=context,
                text=result['message'],
                delay_seconds=120,
                delete_user_message=True
            )
            
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
        menu_weight=35,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id

            # 解析命令参数
            args = context.args

            # 如果没有参数，执行一键全平
            if len(args) == 0:
                result = await position_service.close_all_positions(user_id, group_id)
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=result['message'],
                    delay_seconds=30,
                    delete_user_message=True
                )
                return

            # 检查是否为批量平仓模式（多个币种参数，且没有数字参数）
            if len(args) >= 2:
                # 检查是否所有参数都是币种名称（没有数字参数）
                has_numeric = any(arg.replace('.', '').replace('u', '').replace('U', '').isdigit() for arg in args)
                if not has_numeric:
                    # 批量平仓模式：/close xrp btc eth
                    symbols = [arg.upper() for arg in args]
                    results = []

                    for symbol in symbols:
                        try:
                            # 使用市价单平仓 - 多头仓位使用卖出方向
                            result = await order_service.create_market_order(user_id, group_id, f"{symbol}/USDT", "short", "close", None)
                            results.append(f"{symbol}: {result['message']}")
                        except Exception as e:
                            results.append(f"{symbol}: ❌ 平仓失败 - {str(e)}")

                    response = "🔄 批量平仓结果:\n" + "\n".join(results)
                    await MessageDeletionService.send_and_schedule_delete(
                        update=update,
                        context=context,
                        text=response,
                        delay_seconds=120,
                        delete_user_message=True
                    )
                    return

            # 如果只有一个参数，智能平仓该币种的所有仓位
            if len(args) == 1:
                symbol = args[0].upper()
                # 使用市价单平仓替代老的 close_position 方法 - 多头仓位使用卖出方向
                result = await order_service.create_market_order(user_id, group_id, f"{symbol}/USDT", "short", "close", None)
                await MessageDeletionService.send_and_schedule_delete(
                    update=update,
                    context=context,
                    text=result['message'],
                    delay_seconds=120,
                    delete_user_message=True
                )
                return

            # 传统模式：单币种平仓（支持方向和金额参数）
            symbol = args[0].upper()

            # 检查第二个参数是方向还是金额
            second_arg = args[1].lower()
            if second_arg in ['long', 'short']:
                # 第二个参数是方向
                side = second_arg
                amount = None

                # 检查是否有第三个参数（金额）
                if len(args) >= 3:
                    try:
                        amount = float(args[2].replace('u', '').replace('U', ''))
                        if amount <= 0:
                            await update.message.reply_text("❌ 金额必须大于0！")
                            return
                    except ValueError:
                        await update.message.reply_text("❌ 金额格式错误！")
                        return
            else:
                # 第二个参数可能是金额，智能平仓
                try:
                    amount = float(second_arg.replace('u', '').replace('U', ''))
                    if amount <= 0:
                        await update.message.reply_text("❌ 金额必须大于0！")
                        return
                    side = None  # 智能平仓
                except ValueError:
                    # 既不是方向也不是有效金额，显示用法说明
                    await update.message.reply_text(
                        "❌ 用法错误！\n正确格式:\n" +
                        "• /close (一键全平所有仓位)\n" +
                        "• /close <交易对> (智能平仓该币种所有仓位)\n" +
                        "• /close <币种1> <币种2> <币种3> (批量平仓多个币种)\n" +
                        "• /close <交易对> <方向> (平指定方向仓位)\n" +
                        "• /close <交易对> <方向> <金额> (部分平仓)\n" +
                        "• /close <交易对> <金额> (智能部分平仓)\n" +
                        "例如:\n" +
                        "/close (全平所有仓位)\n" +
                        "/close btc (平BTC所有仓位)\n" +
                        "/close xrp btc eth (批量平仓XRP、BTC、ETH)\n" +
                        "/close btc long (平BTC多头仓位)\n" +
                        "/close btc 50 (智能平仓50U)"
                    )
                    return

            # 执行平仓操作 - 根据仓位方向使用相反的交易方向
            close_direction = "short" if side == "long" else "long"
            result = await order_service.create_market_order(
                user_id, group_id, f"{symbol}/USDT",
                close_direction, "close", amount
            )

            await MessageDeletionService.send_and_schedule_delete(
                update=update,
                context=context,
                text=result['message'],
                delay_seconds=10,
                delete_user_message=True
            )

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
        menu_weight=36,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            group_id = update.effective_chat.id
            
            # 检查是否有参数
            args = context.args
            is_global = len(args) > 0 and args[0].lower() == 'all'
            
            if is_global:
                # 获取全局排行榜数据
                result = await analysis_service.get_global_ranking_data()
                deadbeat_result = await analysis_service.get_global_deadbeat_ranking_data()
                title = "📊 <b>全球交易排行榜</b>\n"
            else:
                # 获取群组排行榜数据
                result = await analysis_service.get_ranking_data(group_id)
                deadbeat_result = await analysis_service.get_deadbeat_ranking_data(group_id)
                title = "📊 <b>群组交易排行榜</b>\n"
            
            if not result['success']:
                await update.message.reply_text("❌ 获取排行榜数据失败，请稍后重试")
                return
            
            # 构建排行榜消息
            message_parts = [title]
            
            # 盈利排行榜
            message_parts.append("💰 <b>盈利排行榜 TOP5</b>")
            if result['profit_ranking']:
                profit_lines = []
                for i, user_data in enumerate(result['profit_ranking'], 1):
                    user_id = user_data['user_id']
                    total_pnl = user_data['total_pnl']
                    group_name = user_data.get('group_name', '') if is_global else ''
                    
                    try:
                        # 对于全局排行榜，尝试从任意群组获取用户信息
                        if is_global:
                            # 尝试从当前群组获取用户信息，如果失败则使用默认名称
                            try:
                                user = await context.bot.get_chat_member(group_id, user_id)
                                username = user.user.first_name or f"用户{user_id}"
                            except:
                                username = f"用户{user_id}"
                        else:
                            user = await context.bot.get_chat_member(group_id, user_id)
                            username = user.user.first_name or f"用户{user_id}"
                    except:
                        username = f"用户{user_id}"
                    
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "💎" if i == 4 else "⭐"
                    pnl_text = f"+{total_pnl:.2f}"
                    
                    if is_global and group_name:
                        profit_lines.append(f"{emoji} {username} ({group_name}): {pnl_text} USDT")
                    else:
                        profit_lines.append(f"{emoji} {username}: {pnl_text} USDT")
                
                message_parts.append(f"<blockquote expandable>{'\n'.join(profit_lines)}</blockquote>")
            else:
                message_parts.append("<blockquote expandable>暂无数据</blockquote>")
            
            message_parts.append("")
            
            # 亏损排行榜
            message_parts.append("📉 <b>亏损排行榜 TOP5</b>")
            if result['loss_ranking']:
                loss_lines = []
                for i, user_data in enumerate(result['loss_ranking'], 1):
                    user_id = user_data['user_id']
                    total_pnl = user_data['total_pnl']
                    group_name = user_data.get('group_name', '') if is_global else ''
                    
                    try:
                        # 对于全局排行榜，尝试从任意群组获取用户信息
                        if is_global:
                            # 尝试从当前群组获取用户信息，如果失败则使用默认名称
                            try:
                                user = await context.bot.get_chat_member(group_id, user_id)
                                username = user.user.first_name or f"用户{user_id}"
                            except:
                                username = f"用户{user_id}"
                        else:
                            user = await context.bot.get_chat_member(group_id, user_id)
                            username = user.user.first_name or f"用户{user_id}"
                    except:
                        username = f"用户{user_id}"
                    
                    emoji = "💀" if i == 1 else "☠️" if i == 2 else "💔" if i == 3 else "😭" if i == 4 else "😢"
                    pnl_text = f"{total_pnl:.2f}"
                    
                    if is_global and group_name:
                        loss_lines.append(f"{emoji} {username} ({group_name}): {pnl_text} USDT")
                    else:
                        loss_lines.append(f"{emoji} {username}: {pnl_text} USDT")
                
                message_parts.append(f"<blockquote expandable>{'\n'.join(loss_lines)}</blockquote>")
            else:
                message_parts.append("<blockquote expandable>暂无数据</blockquote>")
            
            message_parts.append("")
            
            # 当前浮动余额排行榜
            message_parts.append("💰 <b>当前浮动余额排行榜 TOP10</b>")
            if result['balance_ranking']:
                balance_lines = []
                for i, user_data in enumerate(result['balance_ranking'], 1):
                    user_id = user_data['user_id']
                    floating_balance = user_data['floating_balance']
                    group_name = user_data.get('group_name', '') if is_global else ''
                    
                    try:
                        # 对于全局排行榜，尝试从任意群组获取用户信息
                        if is_global:
                            try:
                                user = await context.bot.get_chat_member(group_id, user_id)
                                username = user.user.first_name or f"用户{user_id}"
                            except:
                                username = f"用户{user_id}"
                        else:
                            user = await context.bot.get_chat_member(group_id, user_id)
                            username = user.user.first_name or f"用户{user_id}"
                    except:
                        username = f"用户{user_id}"
                    
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                    
                    if is_global and group_name:
                        balance_lines.append(f"{emoji} {username} ({group_name}): {floating_balance:.2f} USDT")
                    else:
                        balance_lines.append(f"{emoji} {username}: {floating_balance:.2f} USDT")
                
                message_parts.append(f"<blockquote expandable>{'\n'.join(balance_lines)}</blockquote>")
            else:
                message_parts.append("<blockquote expandable>暂无数据</blockquote>")
            
            message_parts.append("")
            
            # 爆仓次数排行榜
            message_parts.append("💥 <b>爆仓次数排行榜 TOP10</b>")
            if result['liquidation_ranking']:
                liquidation_lines = []
                for i, user_data in enumerate(result['liquidation_ranking'], 1):
                    user_id = user_data['user_id']
                    liquidation_count = user_data['liquidation_count']
                    group_name = user_data.get('group_name', '') if is_global else ''

                    try:
                        # 对于全局排行榜，尝试从任意群组获取用户信息
                        if is_global:
                            try:
                                user = await context.bot.get_chat_member(group_id, user_id)
                                username = user.user.first_name or f"用户{user_id}"
                            except:
                                username = f"用户{user_id}"
                        else:
                            user = await context.bot.get_chat_member(group_id, user_id)
                            username = user.user.first_name or f"用户{user_id}"
                    except:
                        username = f"用户{user_id}"

                    emoji = "💀" if i == 1 else "☠️" if i == 2 else "💥" if i == 3 else "🔥"

                    if is_global and group_name:
                        liquidation_lines.append(f"{emoji} {username} ({group_name}): {liquidation_count} 次")
                    else:
                        liquidation_lines.append(f"{emoji} {username}: {liquidation_count} 次")

                message_parts.append(f"<blockquote expandable>{'\n'.join(liquidation_lines)}</blockquote>")
            else:
                message_parts.append("<blockquote expandable>暂无数据</blockquote>")

            message_parts.append("")

            # 交易量排行榜
            message_parts.append("📊 <b>交易量排行榜 TOP10</b>")
            if result['volume_ranking']:
                volume_lines = []
                for i, user_data in enumerate(result['volume_ranking'], 1):
                    user_id = user_data['user_id']
                    total_volume = user_data['total_volume']
                    group_name = user_data.get('group_name', '') if is_global else ''

                    try:
                        # 对于全局排行榜，尝试从任意群组获取用户信息
                        if is_global:
                            try:
                                user = await context.bot.get_chat_member(group_id, user_id)
                                username = user.user.first_name or f"用户{user_id}"
                            except:
                                username = f"用户{user_id}"
                        else:
                            user = await context.bot.get_chat_member(group_id, user_id)
                            username = user.user.first_name or f"用户{user_id}"
                    except:
                        username = f"用户{user_id}"

                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"

                    if is_global and group_name:
                        volume_lines.append(f"{emoji} {username} ({group_name}): {total_volume:.0f} USDT")
                    else:
                        volume_lines.append(f"{emoji} {username}: {total_volume:.0f} USDT")

                message_parts.append(f"<blockquote expandable>{'\n'.join(volume_lines)}</blockquote>")
            else:
                message_parts.append("<blockquote expandable>暂无数据</blockquote>")

            message_parts.append("")
            
            # 老赖排行榜
            message_parts.append("🏴‍☠️ <b>老赖排行榜 TOP5</b>")
            if deadbeat_result.get('success') and deadbeat_result.get('deadbeat_ranking'):
                deadbeat_lines = []
                for i, deadbeat_data in enumerate(deadbeat_result['deadbeat_ranking'], 1):
                    user_id = deadbeat_data['user_id']
                    total_debt = deadbeat_data['total_debt']
                    net_balance = deadbeat_data['net_balance']
                    debt_ratio = deadbeat_data['debt_ratio']
                    overdue_days = deadbeat_data['overdue_days']
                    group_name = deadbeat_data.get('group_name', '') if is_global else ''
                    
                    try:
                        # 对于全局排行榜，尝试从任意群组获取用户信息
                        if is_global:
                            try:
                                user = await context.bot.get_chat_member(group_id, user_id)
                                username = user.user.first_name or f"用户{user_id}"
                            except:
                                username = f"用户{user_id}"
                        else:
                            user = await context.bot.get_chat_member(group_id, user_id)
                            username = user.user.first_name or f"用户{user_id}"
                    except:
                        username = f"用户{user_id}"
                    
                    emoji = "💀" if i == 1 else "☠️" if i == 2 else "🏴‍☠️" if i == 3 else "💸" if i == 4 else "🔴"
                    
                    # 格式化债务比例
                    if debt_ratio >= 999999:
                        ratio_text = "∞"
                    else:
                        ratio_text = f"{debt_ratio:.1f}x"
                    
                    # 格式化逾期信息
                    if overdue_days > 0:
                        overdue_text = f"逾期{overdue_days}天"
                    else:
                        overdue_text = "未逾期"
                    
                    if is_global and group_name:
                        deadbeat_lines.append(f"{emoji} {username} ({group_name}): 欠款{total_debt:.2f} USDT | 净余额{net_balance:.2f} | 比例{ratio_text} | {overdue_text}")
                    else:
                        deadbeat_lines.append(f"{emoji} {username}: 欠款{total_debt:.2f} USDT | 净余额{net_balance:.2f} | 比例{ratio_text} | {overdue_text}")
                
                message_parts.append(f"<blockquote expandable>{'\n'.join(deadbeat_lines)}</blockquote>")
            else:
                message_parts.append("<blockquote expandable>暂无老赖数据</blockquote>")
            
            final_message = "\n".join(message_parts)
            await MessageDeletionService.send_and_schedule_delete(
                update=update,
                context=context,
                text=final_message,
                parse_mode='HTML',
                delay_seconds=240,
                delete_user_message=True
            )
            
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


class LoanCommand(BaseCommand):
    meta = CommandMeta(
        name="loan",
        command_type="group",
        trigger="loan",
        menu_text="申请贷款 (模拟盘)",
        show_in_menu=True,
        menu_weight=37,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 解析命令参数
            args = context.args
            if len(args) != 1:
                await update.message.reply_text(
                    "❌ 用法错误！\n正确格式: /loan <金额>\n"
                    "例如: /loan 10000"
                )
                return
            
            try:
                amount = float(args[0].replace('u', '').replace('U', ''))
                if amount <= 0:
                    await update.message.reply_text("❌ 贷款金额必须大于0！")
                    return
            except ValueError:
                await update.message.reply_text("❌ 金额格式错误！")
                return
            
            # 申请贷款
            result = loan_service.apply_loan(user_id, group_id, amount)

            await MessageDeletionService.send_and_schedule_delete(
                update=update,
                context=context,
                text=result['message'],
                delay_seconds=120,
                delete_user_message=True
            )
            
        except Exception as e:
            logger.error(f"贷款申请失败: {e}")
            await update.message.reply_text("❌ 贷款申请失败，请稍后重试")


class RepayCommand(BaseCommand):
    meta = CommandMeta(
        name="repay",
        command_type="group",
        trigger="repay",
        menu_text="还款 (模拟盘)",
        show_in_menu=True,
        menu_weight=38,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 解析命令参数
            args = context.args
            amount = None
            
            if len(args) == 1:
                try:
                    amount = float(args[0].replace('u', '').replace('U', ''))
                    if amount <= 0:
                        await update.message.reply_text("❌ 还款金额必须大于0！")
                        return
                except ValueError:
                    await update.message.reply_text("❌ 金额格式错误！")
                    return
            elif len(args) > 1:
                await update.message.reply_text(
                    "❌ 用法错误！\n正确格式:\n"
                    "• /repay (一次性结清所有贷款)\n"
                    "• /repay <金额> (部分还款)\n"
                    "例如: /repay 或 /repay 5000"
                )
                return
            
            # 执行还款
            result = loan_service.repay_loan(user_id, group_id, amount)

            await MessageDeletionService.send_and_schedule_delete(
                update=update,
                context=context,
                text=result['message'],
                delay_seconds=120,
                delete_user_message=True
            )
            
        except Exception as e:
            logger.error(f"还款失败: {e}")
            await update.message.reply_text("❌ 还款失败，请稍后重试")


class BillCommand(BaseCommand):
    meta = CommandMeta(
        name="bill",
        command_type="group",
        trigger="bill",
        menu_text="查看贷款账单 (模拟盘)",
        show_in_menu=True,
        menu_weight=39,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 获取贷款账单
            result = loan_service.get_loan_bill(user_id, group_id)

            await MessageDeletionService.send_and_schedule_delete(
                update=update,
                context=context,
                text=result['message'],
                parse_mode='HTML',
                delay_seconds=120,
                delete_user_message=True
            )
            
        except Exception as e:
            logger.error(f"获取贷款账单失败: {e}")
            await update.message.reply_text("❌ 获取贷款账单失败，请稍后重试")


class TakeProfitCommand(BaseCommand):
    meta = CommandMeta(
        name="takeprofit",
        command_type="group",
        trigger="tp",
        menu_text="设置止盈 (模拟盘)",
        show_in_menu=True,
        menu_weight=34,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            args = context.args

            if not args:
                await update.message.reply_text(
                    "📋 止盈指令使用方法:\n"
                    "🎯 /tp <币种> <方向> <价格> - 为指定方向持仓设置止盈\n"
                    "🗑️ /tp <币种> <方向> cancel - 取消指定方向止盈\n"
                    "🗑️ /tp <币种> cancel - 取消所有止盈\n"
                    "📊 /tp list - 查看所有止盈订单\n\n"
                    "示例:\n"
                    "/tp btc long 95000 - 为BTC多头设置95000止盈\n"
                    "/tp btc short 85000 - 为BTC空头设置85000止盈\n"
                    "/tp eth long cancel - 取消ETH多头止盈"
                )
                return

            if args[0].lower() == 'list':
                await self._list_tp_orders(update, user_id, group_id)
                return

            if len(args) < 2:
                await update.message.reply_text("❌ 参数不足，请提供币种和价格或操作")
                return

            symbol = args[0].upper()
            
            # 检查是否有方向参数
            if len(args) >= 3 and args[1].lower() in ['long', 'short']:
                # 格式: /tp <币种> <方向> <价格/cancel>
                direction = args[1].lower()
                action = args[2].lower()
                
                if action == 'cancel':
                    await self._cancel_tp_order(update, user_id, group_id, symbol, direction)
                else:
                    try:
                        price = float(action)
                        await self._set_tp_order(update, user_id, group_id, symbol, price, direction)
                    except ValueError:
                        await update.message.reply_text(
                            "❌ 价格格式错误\n\n"
                            "正确格式: /tp <币种> <方向> <价格>\n"
                            "示例: /tp pepe long 0.000000001"
                        )
            else:
                # 格式: /tp <币种> <价格/cancel> (兼容旧格式)
                action = args[1].lower()
                
                if action == 'cancel':
                    await self._cancel_tp_order(update, user_id, group_id, symbol)
                else:
                    try:
                        price = float(action)
                        await self._set_tp_order(update, user_id, group_id, symbol, price)
                    except ValueError:
                        await update.message.reply_text(
                            "❌ 价格格式错误\n\n"
                            "正确格式: /tp <币种> <价格> 或 /tp <币种> <方向> <价格>\n"
                            "示例: /tp pepe 0.000000001 或 /tp pepe long 0.000000001"
                        )

        except Exception as e:
            logger.error(f"止盈命令失败: {e}")
            await update.message.reply_text("❌ 操作失败，请稍后重试")

    async def _set_tp_order(self, update, user_id: int, group_id: int, symbol: str, price: float, direction: str = None):
        """设置止盈订单"""
        try:
            # 检查是否有对应持仓
            positions = await position_service.get_positions(user_id, group_id)
            target_positions = []
            
            for pos in positions:
                if pos['symbol'].replace('/USDT', '').upper() == symbol:
                    if direction:
                        # 指定方向，只处理匹配的持仓
                        if pos['side'] == direction:
                            target_positions.append(pos)
                    else:
                        # 未指定方向，处理所有持仓
                        target_positions.append(pos)
            
            if not target_positions:
                direction_text = f"{direction}方向" if direction else ""
                await update.message.reply_text(f"❌ 未找到{symbol}{direction_text}持仓")
                return
            
            # 为每个匹配的持仓创建止盈订单
            success_count = 0
            for position in target_positions:
                result = await order_service.create_order(
                    user_id=user_id,
                    group_id=group_id,
                    symbol=f"{symbol}/USDT",
                    direction='ask' if position['side'] == 'long' else 'bid',
                    role='maker',
                    order_type='tp',
                    operation='addition',
                    volume=abs(position['size']),
                    price=price
                )
                
                if result['success']:
                    success_count += 1
            
            if success_count > 0:
                direction_text = f" {direction}方向" if direction else ""
                await update.message.reply_text(
                    f"✅ {symbol}{direction_text} 止盈订单已设置\n"
                    f"🎯 止盈价格: {price:.4f}\n"
                    f"📊 设置成功: {success_count}个持仓"
                )
            else:
                await update.message.reply_text(f"❌ 设置止盈失败")
                
        except Exception as e:
            logger.error(f"设置止盈失败: {e}")
            await update.message.reply_text("❌ 设置止盈失败")

    async def _cancel_tp_order(self, update, user_id: int, group_id: int, symbol: str, direction: str = None):
        """取消止盈订单"""
        try:
            # 查找对应的止盈订单
            tp_orders = await order_service.get_orders_by_type(user_id, group_id, 'tp')
            target_orders = []
            
            for order in tp_orders:
                if order['symbol'].replace('/USDT', '').upper() == symbol:
                    if direction:
                        # 指定方向，需要根据订单的side判断方向
                        # 止盈订单的side与持仓方向相反
                        order_direction = 'long' if order['side'] == 'sell' else 'short'
                        if order_direction == direction:
                            target_orders.append(order)
                    else:
                        # 未指定方向，取消所有
                        target_orders.append(order)
            
            if not target_orders:
                direction_text = f"{direction}方向" if direction else ""
                await update.message.reply_text(f"❌ 未找到{symbol}{direction_text}的止盈订单")
                return
            
            # 取消所有匹配的止盈订单
            cancelled_count = 0
            for order in target_orders:
                result = order_service.cancel_order(order['order_id'])
                if result['success']:
                    cancelled_count += 1
            
            if cancelled_count > 0:
                direction_text = f"{direction}方向" if direction else ""
                await update.message.reply_text(f"✅ 已取消{cancelled_count}个{symbol}{direction_text}止盈订单")
            else:
                direction_text = f"{direction}方向" if direction else ""
                await update.message.reply_text(f"❌ 取消{symbol}{direction_text}止盈订单失败")
                
        except Exception as e:
            logger.error(f"取消止盈失败: {e}")
            await update.message.reply_text("❌ 取消止盈失败")

    async def _list_tp_orders(self, update, user_id: int, group_id: int):
        """列出所有止盈订单"""
        try:
            tp_orders = await order_service.get_orders_by_type(user_id, group_id, 'tp')
            
            if not tp_orders:
                await update.message.reply_text("📭 暂无止盈订单")
                return
            
            message_parts = ["🎯 止盈订单列表:"]
            for order in tp_orders:
                symbol = order['symbol'].replace('/USDT', '')
                message_parts.append(
                    f"📈 {symbol} | 价格: {order['price']:.4f} | 数量: {order['amount']:.4f}"
                )
            
            await update.message.reply_text("\n".join(message_parts))
                
        except Exception as e:
            logger.error(f"查看止盈订单失败: {e}")
            await update.message.reply_text("❌ 查看止盈订单失败")


class StopLossCommand(BaseCommand):
    meta = CommandMeta(
        name="stoploss",
        command_type="group",
        trigger="sl",
        menu_text="设置止损 (模拟盘)",
        show_in_menu=True,
        menu_weight=35,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            args = context.args

            if not args:
                await update.message.reply_text(
                    "📋 止损指令使用方法:\n"
                    "🛡️ /sl <币种> <方向> <价格> - 为指定方向持仓设置止损\n"
                    "🛡️ /sl <币种> <价格> - 为所有持仓设置止损\n"
                    "🗑️ /sl <币种> <方向> cancel - 取消指定方向止损\n"
                    "🗑️ /sl <币种> cancel - 取消所有止损\n"
                    "📊 /sl list - 查看所有止损订单\n\n"
                    "示例:\n"
                    "/sl btc long 85000 - 为BTC多头设置85000止损\n"
                    "/sl btc short 95000 - 为BTC空头设置95000止损\n"
                    "/sl eth long cancel - 取消ETH多头止损"
                )
                return

            if args[0].lower() == 'list':
                await self._list_sl_orders(update, user_id, group_id)
                return

            if len(args) < 2:
                await update.message.reply_text("❌ 参数不足，请提供币种和价格或操作")
                return

            symbol = args[0].upper()
            
            # 检查是否有方向参数
            if len(args) >= 3 and args[1].lower() in ['long', 'short']:
                # 格式: /sl <币种> <方向> <价格/cancel>
                direction = args[1].lower()
                action = args[2].lower()
                
                if action == 'cancel':
                    await self._cancel_sl_order(update, user_id, group_id, symbol, direction)
                else:
                    try:
                        price = float(action)
                        await self._set_sl_order(update, user_id, group_id, symbol, price, direction)
                    except ValueError:
                        await update.message.reply_text(
                            "❌ 价格格式错误\n\n"
                            "正确格式: /sl <币种> <方向> <价格>\n"
                            "示例: /sl pepe long 0.000000001"
                        )
            else:
                # 格式: /sl <币种> <价格/cancel> (兼容旧格式)
                action = args[1].lower()
                
                if action == 'cancel':
                    await self._cancel_sl_order(update, user_id, group_id, symbol)
                else:
                    try:
                        price = float(action)
                        await self._set_sl_order(update, user_id, group_id, symbol, price)
                    except ValueError:
                        await update.message.reply_text(
                            "❌ 价格格式错误\n\n"
                            "正确格式: /sl <币种> <价格> 或 /sl <币种> <方向> <价格>\n"
                            "示例: /sl pepe 0.000000001 或 /sl pepe long 0.000000001"
                        )

        except Exception as e:
            logger.error(f"止损命令失败: {e}")
            await update.message.reply_text("❌ 操作失败，请稍后重试")

    async def _set_sl_order(self, update, user_id: int, group_id: int, symbol: str, price: float, direction: str = None):
        """设置止损订单"""
        try:
            # 检查是否有对应持仓
            positions = await position_service.get_positions(user_id, group_id)
            target_positions = []
            
            for pos in positions:
                if pos['symbol'].replace('/USDT', '').upper() == symbol:
                    if direction:
                        # 指定方向，只处理匹配的持仓
                        if pos['side'] == direction:
                            target_positions.append(pos)
                    else:
                        # 未指定方向，处理所有持仓
                        target_positions.append(pos)
            
            if not target_positions:
                direction_text = f"{direction}方向" if direction else ""
                await update.message.reply_text(f"❌ 未找到{symbol}{direction_text}持仓")
                return
            
            # 为每个匹配的持仓创建止损订单
            success_count = 0
            for position in target_positions:
                result = await order_service.create_order(
                    user_id=user_id,
                    group_id=group_id,
                    symbol=f"{symbol}/USDT",
                    direction='ask' if position['side'] == 'long' else 'bid',
                    role='maker',
                    order_type='sl',
                    operation='addition',
                    volume=abs(position['size']),
                    price=price
                )
                
                if result['success']:
                    success_count += 1
            
            if success_count > 0:
                direction_text = f" {direction}方向" if direction else ""
                await update.message.reply_text(
                    f"✅ {symbol}{direction_text} 止损订单已设置\n"
                    f"🛡️ 止损价格: {price:.4f}\n"
                    f"📊 设置成功: {success_count}个持仓"
                )
            else:
                await update.message.reply_text(f"❌ 设置止损失败")
                
        except Exception as e:
            logger.error(f"设置止损失败: {e}")
            await update.message.reply_text("❌ 设置止损失败")

    async def _cancel_sl_order(self, update, user_id: int, group_id: int, symbol: str, direction: str = None):
        """取消止损订单"""
        try:
            # 查找对应的止损订单
            sl_orders = await order_service.get_orders_by_type(user_id, group_id, 'sl')
            target_orders = []
            
            for order in sl_orders:
                if order['symbol'].replace('/USDT', '').upper() == symbol:
                    if direction:
                        # 指定方向，需要根据订单的side判断方向
                        # 止损订单的side与持仓方向相反
                        order_direction = 'long' if order['side'] == 'sell' else 'short'
                        if order_direction == direction:
                            target_orders.append(order)
                    else:
                        # 未指定方向，取消所有
                        target_orders.append(order)
            
            if not target_orders:
                direction_text = f"{direction}方向" if direction else ""
                await update.message.reply_text(f"❌ 未找到{symbol}{direction_text}的止损订单")
                return
            
            # 取消所有匹配的止损订单
            cancelled_count = 0
            for order in target_orders:
                result = order_service.cancel_order(order['order_id'])
                if result['success']:
                    cancelled_count += 1
            
            if cancelled_count > 0:
                direction_text = f"{direction}方向" if direction else ""
                await update.message.reply_text(f"✅ 已取消{cancelled_count}个{symbol}{direction_text}止损订单")
            else:
                direction_text = f"{direction}方向" if direction else ""
                await update.message.reply_text(f"❌ 取消{symbol}{direction_text}止损订单失败")
                
        except Exception as e:
            logger.error(f"取消止损失败: {e}")
            await update.message.reply_text("❌ 取消止损失败")

    async def _list_sl_orders(self, update, user_id: int, group_id: int):
        """列出所有止损订单"""
        try:
            sl_orders = await order_service.get_orders_by_type(user_id, group_id, 'sl')
            
            if not sl_orders:
                await update.message.reply_text("📭 暂无止损订单")
                return
            
            message_parts = ["🛡️ 止损订单列表:"]
            for order in sl_orders:
                symbol = order['symbol'].replace('/USDT', '')
                message_parts.append(
                    f"📉 {symbol} | 价格: {order['price']:.4f} | 数量: {order['amount']:.4f}"
                )
            
            await update.message.reply_text("\n".join(message_parts))
                
        except Exception as e:
            logger.error(f"查看止损订单失败: {e}")
            await update.message.reply_text("❌ 查看止损订单失败")


class CancelCommand(BaseCommand):
    meta = CommandMeta(
        name="cancel",
        command_type="group",
        trigger="cancel",
        menu_text="取消挂单",
        show_in_menu=True,
        menu_weight=15,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """取消挂单指令"""
        try:
            # 新交易系统已启用

            user_id = update.effective_user.id
            group_id = update.effective_chat.id
            
            # 获取参数
            args = context.args
            if not args:
                await self._show_pending_orders(update, user_id, group_id)
                return
            
            # 处理取消指令
            if args[0].lower() == 'all':
                await self._cancel_all_orders(update, user_id, group_id)
            else:
                # 尝试按订单ID取消
                order_id = args[0]
                await self._cancel_order_by_id(update, user_id, group_id, order_id)
                
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            await update.message.reply_text("❌ 取消订单失败")

    async def _show_pending_orders(self, update: Update, user_id: int, group_id: int):
        """显示所有挂单"""
        try:
            # 获取所有挂单
            orders_result = order_service.get_orders(user_id, group_id, 'pending')
            all_orders = orders_result.get('orders', []) if orders_result.get('success') else []
            
            if not all_orders:
                await update.message.reply_text("📭 暂无挂单")
                return
            
            message_parts = ["⏳ 当前挂单列表:"]
            message_parts.append("")
            
            for i, order in enumerate(all_orders, 1):
                order_type_emoji = {
                    'open': '📈' if order.get('direction') == 'bid' else '📉',
                    'tp': '🎯',
                    'sl': '🛡️'
                }.get(order.get('order_type'), '📋')
                
                symbol = order.get('symbol', '').replace('/USDT', '')
                price = order.get('price') or 0
                volume = order.get('volume') or 0
                order_type = order.get('order_type', 'open')
                
                message_parts.append(
                    f"{i}. {order_type_emoji} {symbol} | "
                    f"类型: {order_type.upper()} | "
                    f"价格: {price:.4f} | "
                    f"金额: {volume:.2f} USDT"
                )
                message_parts.append(f"   ID: `{order.get('order_id', '')}`")
                message_parts.append("")
            
            message_parts.append("💡 使用方法:")
            message_parts.append("/cancel <订单ID> - 取消指定订单")
            message_parts.append("/cancel all - 取消所有挂单")
            
            await update.message.reply_text("\n".join(message_parts), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"显示挂单列表失败: {e}")
            await update.message.reply_text("❌ 获取挂单列表失败")

    async def _cancel_all_orders(self, update: Update, user_id: int, group_id: int):
        """取消所有挂单"""
        try:
            # 获取所有挂单
            orders_result = order_service.get_orders(user_id, group_id, 'pending')
            all_orders = orders_result.get('orders', []) if orders_result.get('success') else []
            
            if not all_orders:
                await update.message.reply_text("📭 暂无挂单可取消")
                return
            
            cancelled_count = 0
            failed_count = 0
            
            for order in all_orders:
                order_id = order.get('order_id')
                if order_id:
                    result = order_service.cancel_order(order_id)
                    if result.get('success'):
                        cancelled_count += 1
                    else:
                        failed_count += 1
            
            message = f"✅ 已取消 {cancelled_count} 个订单"
            if failed_count > 0:
                message += f"\n❌ {failed_count} 个订单取消失败"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"取消所有订单失败: {e}")
            await update.message.reply_text("❌ 取消所有订单失败")

    async def _cancel_order_by_id(self, update: Update, user_id: int, group_id: int, order_id: str):
        """根据订单ID取消订单"""
        try:
            # 验证订单是否属于该用户
            orders_result = order_service.get_orders(user_id, group_id, 'pending')
            all_orders = orders_result.get('orders', []) if orders_result.get('success') else []
            
            target_order = None
            for order in all_orders:
                if order.get('order_id') == order_id:
                    target_order = order
                    break
            
            if not target_order:
                await update.message.reply_text("❌ 未找到指定的挂单或订单不属于您")
                return
            
            # 取消订单
            result = order_service.cancel_order(order_id)
            
            if result.get('success'):
                symbol = target_order.get('symbol', '').replace('/USDT', '')
                order_type = target_order.get('order_type', 'open')
                await update.message.reply_text(
                    f"✅ 已成功取消订单\n"
                    f"📋 {symbol} {order_type.upper()} 订单已取消"
                )
            else:
                error_msg = result.get('error', '未知错误')
                await update.message.reply_text(f"❌ 取消订单失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"取消指定订单失败: {e}")
            await update.message.reply_text("❌ 取消订单失败")

