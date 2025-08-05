import asyncio
import datetime
import json
import logging
import os
import re
from pathlib import Path
from agent.llm_functions import generate_summary
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
from telegram.ext import ContextTypes
from bot_core.public_functions.messages import handle_agent_session, send_message
import bot_core.public_functions.update_parse as public
from bot_core.callback_handlers.inline import Inline
from agent.llm_functions import run_agent_session,generate_char
from bot_core.public_functions.conversation import PrivateConv
from utils import db_utils as db
from utils.logging_utils import setup_logging
from .base import BaseCommand, CommandMeta
from agent.tools_registry import MarketToolRegistry

setup_logging()
logger = logging.getLogger(__name__)


class StartCommand(BaseCommand):
    meta = CommandMeta(
        name="start",
        command_type="private",
        trigger="start",
        menu_text="开始使用 CyberWaifu",
        show_in_menu=False,
        menu_weight=99,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        await update.message.reply_text(
            f"您好，{info.get('first_name', '')} {info.get('last_name', '')}！这是由 @Xi_cuicui 开发的`CyberWaifu`项目。\r\n使用`/char`可以切换角色\r\n"
            f"使用`/setting`可以管理您的对话与角色设置\r\n"
            f"使用`/c` 可获取加密货币行情分析\r\n"
            f"使用`/sign` 可签到\r\n"
            f"直接发送图片可以获取`fuck or not`的评价\r\n"
            f"默认预设为正常模式，NSFW内容的生成质量有限\r\n"
            f"使用`/preset`可以切换预设，如果需要NSFW内容，建议替换默认预设为其它模式\r\n"
            f"使用`/newchar [角色名]`可以创建私人角色"
        )


class HelpCommand(BaseCommand):
    meta = CommandMeta(
        name="help",
        command_type="private",
        trigger="help",
        menu_text="获取帮助",
        show_in_menu=True,
        menu_weight=0,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        help_text = (
            "🤖 **CyberWaifu Bot 使用指南**\n\n"
            "📝 **角色管理**\n"
            "/char - 查看当前角色信息和角色列表\n"
            "/newchar - 创建新的AI角色\n"
            "/delchar - 删除已有角色\n"
            "/nick - 修改当前角色的昵称\n\n"
            "⚙️ **设置与配置**\n"
            "/setting - 个人设置（流式输出、模型选择等）\n"
            "/api - 查看和切换可用的API模型\n"
            "/preset - 管理对话预设模板\n\n"
            "💬 **对话管理**\n"
            "/new - 开始新的对话会话\n"
            "/save - 保存当前对话到历史记录\n"
            "/load - 加载之前保存的对话\n"
            "/delete - 删除指定的对话记录\n"
            "/undo - 撤销上一条消息\n"
            "/regen - 重新生成AI的最后一条回复\n"
            "/stream - 切换流式输出模式\n\n"
            "📊 **信息查看**\n"
            "/me - 查看个人信息和使用统计\n"
            "/sign - 每日签到获取额度奖励\n\n"
            "🔧 **高级功能**\n"
            "/c 或 /crypto - AI加密货币分析助手\n"
            "/director - 导演模式（多角色对话）\n"
            "/done - 标记当前任务为完成状态\n\n"
            "🏠 **群聊专用指令**\n"
            "在群聊中还可以使用以下指令：\n"
            "/remake - 重置群聊上下文(担任)\n"
            "/switch - 切换群聊角色\n"
            "/rate - 设置群聊回复概率\n"
            "/kw - 管理群聊关键词触发\n"
            "/e - 启用群聊话题讨论\n"
            "/d - 禁用群聊话题讨论\n"
            "/cc - 群聊加密货币分析\n\n"
            "💡 **使用提示**\n"
            "• 直接发送消息即可与AI对话\n"
            "• 如果喜欢NSFW内容，强烈建议使用 /newchar 创建属于您的角色，并通过 /preset 修改nsfw预设以获得更好的文本质量\n"
            "• 大部分指令支持简写形式\n"
            "• 在群聊中需要@机器人或回复机器人消息\n"
            "• 管理员拥有额外的管理指令权限"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")


class UndoCommand(BaseCommand):
    meta = CommandMeta(
        name="undo",
        command_type="private",
        trigger="undo",
        menu_text="撤回上一条消息",
        show_in_menu=True,
        menu_weight=1,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        conversation = PrivateConv(update, context)
        await conversation.undo()
        if conversation.input and conversation.input.id:
            await context.bot.delete_message(conversation.user.id, conversation.input.id)


class StreamCommand(BaseCommand):
    meta = CommandMeta(
        name="stream",
        command_type="private",
        trigger="stream",
        menu_text="切换流式传输模式",
        show_in_menu=True,
        menu_weight=5,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        if db.user_stream_switch(info["user_id"]):
            await update.message.reply_text("切换成功！")


class MeCommand(BaseCommand):
    meta = CommandMeta(
        name="me",
        command_type="private",
        trigger="me",
        menu_text="查看个人信息",
        show_in_menu=True,
        menu_weight=99,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        user_name = escape_markdown(info.get('user_name', '未知'), version=1)
        # --- 修复：使用正确的键名 ---
        tier = escape_markdown(str(info.get('account_tier', '未知')), version=1)
        remain = escape_markdown(str(info.get('remain_frequency', 0)), version=1)
        frequency = escape_markdown(str(info.get('frequency', 0)), version=1)
        balance = escape_markdown(str(info.get('balance', 0)), version=1)
        
        user_nick = escape_markdown(info.get('nick', '未设置'), version=1)
        char = escape_markdown(info.get('char', '未设置'), version=1)
        api = escape_markdown(info.get('api', '未设置'), version=1)
        preset = escape_markdown(info.get('preset', '未设置'), version=1)
        stream = escape_markdown(str(info.get('stream', '未知')), version=1)

        result = (
            f"您好，{user_name}！\r\n"
            f"您的帐户等级是`{tier}`；\r\n"
            f"您的额度还有`{remain}`条；\r\n"
            f"您的临时额度还有`{frequency}`条(上限100)；\r\n"
            f"您的余额是`{balance}`；\r\n"
            f"您的对话昵称是`{user_nick}`。\r\n"
            f"当前角色：`{char}`\r\n当前接口：`{api}`\r\n当前预设：`{preset}`\r\n流式传输：`{stream}`\r\n"
        )
        await update.message.reply_text(f"{result}", parse_mode="MarkDown")


class NewCommand(BaseCommand):
    meta = CommandMeta(
        name="new",
        command_type="private",
        trigger="new",
        menu_text="创建新对话",
        show_in_menu=True,
        menu_weight=5,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return

        import random
        # 1. 生成新的会话ID
        while True:
            new_conv_id = random.randint(10000000, 99999999)
            if db.conversation_private_check(new_conv_id):
                break
        
        # 2. 从info中获取角色和预设
        character = info.get('char')
        preset = info.get('preset')
        user_id = info.get('user_id')

        if not character or not preset or not user_id:
            await update.message.reply_text("无法获取用户配置，创建新对话失败。")
            return

        # 3. 创建新对话
        if db.conversation_private_create(new_conv_id, user_id, character, preset):
            # 4. 更新用户当前会话ID
            db.user_config_arg_update(user_id, "conv_id", new_conv_id)
            db.user_conversations_count_update(user_id)  # 更新用户对话计数
            await update.message.reply_text("创建成功！", parse_mode="MarkDown")
        else:
            await update.message.reply_text("创建新对话失败，请联系管理员。")
            return
        
        # 5. 显示预设和角色选择
        preset_markup = Inline.print_preset_list()
        if isinstance(preset_markup, str):
            await update.message.reply_text(preset_markup)
        else:
            await update.message.reply_text(
                "请为新对话选择一个预设：", reply_markup=preset_markup
            )
        
        char_markup = Inline.print_char_list("load", "private", user_id)
        if isinstance(char_markup, str):
            await update.message.reply_text(char_markup)
        else:
            await update.message.reply_text(
                "请为新对话选择一个角色：", reply_markup=char_markup
            )


class SaveCommand(BaseCommand):
    meta = CommandMeta(
        name="save",
        command_type="private",
        trigger="save",
        menu_text="保存当前对话",
        show_in_menu=True,
        menu_weight=5,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        config = public.update_info_get(update)
        if not config:
            return
        
        conv_id = config.get("conv_id")
        char = config.get("char")
        preset = config.get("preset")

        if conv_id and char and preset and db.conversation_private_update(
            conv_id, char, preset
        ) and db.conversation_private_save(conv_id):
            placeholder_message = await update.message.reply_text("保存中...")

            async def create_summary(current_conv_id, placeholder):
                summary = await generate_summary(current_conv_id)
                if summary and db.conversation_private_summary_add(current_conv_id, summary):
                    logger.info(
                        f"保存对话并生成总结, conv_id: {current_conv_id}, summary: {summary}"
                    )
                    escaped_summary = escape_markdown(summary, version=1)
                    try:
                        await placeholder.edit_text(
                            f"保存成功，对话总结:`{escaped_summary}`", parse_mode="MarkDown"
                        )
                    except Exception as e:
                        logger.warning(e)
                        await placeholder.edit_text(f"保存成功，对话总结:`{escaped_summary}`")
                else:
                    await placeholder.edit_text("保存失败")

            _task = asyncio.create_task(
                create_summary(conv_id, placeholder_message)
            )
            return


class RegenCommand(BaseCommand):
    meta = CommandMeta(
        name="regen",
        command_type="private",
        trigger="regen",
        menu_text="重新生成回复",
        show_in_menu=True,
        menu_weight=1,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        conversation = PrivateConv(update, context)
        await conversation.regen()
        await update.message.delete()


class CharCommand(BaseCommand):
    meta = CommandMeta(
        name="char",
        command_type="private",
        trigger="char",
        menu_text="选择角色",
        show_in_menu=True,
        menu_weight=6,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        conversation = PrivateConv(update, context)
        if not conversation.user:
            return
        markup = Inline.print_char_list("load", "private", conversation.user.id)
        if isinstance(markup, str):
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个角色：", reply_markup=markup)
        await update.message.delete()


class DelcharCommand(BaseCommand):
    meta = CommandMeta(
        name="delchar",
        command_type="private",
        trigger="delchar",
        menu_text="删除角色",
        show_in_menu=True,
        menu_weight=7,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        markup = Inline.print_char_list("del", "private", info["user_id"])
        if isinstance(markup, str):
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个角色：", reply_markup=markup)


class NewcharCommand(BaseCommand):
    meta = CommandMeta(
        name="newchar",
        command_type="private",
        trigger="newchar",
        menu_text="创建新的角色",
        show_in_menu=True,
        menu_weight=6,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        args = context.args if hasattr(context, "args") else []
        if not args or len(args[0].strip()) == 0:
            await update.message.reply_text(
                "请使用 /newchar char_name 的格式指定角色名。"
            )
            return
        char_name = args[0].strip()
        if not hasattr(context.bot_data, "newchar_state"):
            context.bot_data["newchar_state"] = {}
        context.bot_data["newchar_state"][info["user_id"]] = {
            "char_name": char_name,
            "desc_chunks": [],
        }
        await update.message.reply_text(
            "请直接发送文本描述，完成后发送 /done 结束输入。\n如描述较长可分多条消息发送。"
        )


class NickCommand(BaseCommand):
    meta = CommandMeta(
        name="nick",
        command_type="private",
        trigger="nick",
        menu_text="设置你的昵称",
        show_in_menu=True,
        menu_weight=44,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        args = context.args if hasattr(context, "args") else []
        if not args or len(args[0].strip()) == 0:
            await update.message.reply_text(
                "请使用 /nick nickname 的格式指定昵称。如：/nick 脆脆鲨"
            )
            return
        nick_name = args[0].strip()
        if db.user_config_arg_update(info["user_id"], "nick", nick_name):
            await update.message.reply_text(f"昵称已更新为：{nick_name}")
        else:
            await update.message.reply_text("昵称更新失败")
        await update.message.delete()


class DoneCommand(BaseCommand):
    meta = CommandMeta(
        name="done",
        command_type="private",
        trigger="done",
        menu_text="完成角色创建",
        show_in_menu=False,  # 通常 /done 命令不直接显示在菜单中
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        user_id = info["user_id"]
        state = context.bot_data.get("newchar_state", {}).get(user_id)
        if not state:
            await update.message.reply_text(
                "当前无待保存的角色描述。请先使用 /newchar char_name。"
            )
            return
        char_name = state["char_name"]
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
        grandparent_dir = Path(project_root).resolve().parent.parent
        save_dir = os.path.join(grandparent_dir, "characters")
        os.makedirs(save_dir, exist_ok=True)
        if "file_saved" in state:
            save_path = state["file_saved"]
            del context.bot_data["newchar_state"][user_id]
            await update.message.reply_text(f"角色 {char_name} 已保存到 {save_path}")
            return
        desc = "\n".join(state["desc_chunks"])
        try:
            placeholder_message = await update.message.reply_text("正在生成...")

            async def _generate_char(
                placeholder, char_description, save_to, name_char, uid, tg_context
            ):
                generated_content = None
                try:
                    generated_content = await generate_char(char_description)
                    if not generated_content:
                        await placeholder.edit_text(f"角色 {name_char} 生成失败，LLM未返回任何内容。")
                        return

                    json_pattern = (
                        r"```json\s*([\s\S]*?)\s*```|```([\s\S]*?)\s*```|\{[\s\S]*\}"
                    )
                    match = re.search(json_pattern, generated_content)
                    if match:
                        json_str = next(group for group in match.groups() if group)
                        char_data = json.loads(json_str)
                        save_path = os.path.join(save_to, f"{name_char}_{uid}.json")
                        with open(save_path, "w", encoding="utf-8") as f:
                            json.dump(char_data, f, ensure_ascii=False, indent=2)
                        await placeholder.edit_text(
                            f"角色 {name_char} 已保存到 {save_path}"
                        )
                    else:
                        save_path = os.path.join(save_to, f"{name_char}_{uid}.txt")
                        with open(save_path, "w", encoding="utf-8") as f:
                            f.write(generated_content)
                        await placeholder.edit_text(
                            f"警告：未能从生成内容中提取 JSON 数据，保存原始内容到 {save_path}。"
                        )
                except json.JSONDecodeError as error:
                    save_path = os.path.join(save_to, f"{name_char}_{uid}.txt")
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(generated_content or "")
                    await placeholder.edit_text(
                        f"错误：无法解析生成的 JSON 内容，保存为原始文本到 {save_path}。错误信息：{str(error)}"
                    )
                except Exception as error:
                    await placeholder.edit_text(
                        f"保存角色 {name_char} 时发生错误：{str(error)}"
                    )
                finally:
                    if uid in tg_context.bot_data.get("newchar_state", {}):
                        del tg_context.bot_data["newchar_state"][uid]

            _task = asyncio.create_task(
                _generate_char(
                    placeholder_message,
                    f"角色名称：{char_name}\r\n角色描述：{desc}",
                    save_dir,
                    char_name,
                    user_id,
                    context,
                )
            )
        except Exception as e:
            await update.message.reply_text(f"初始化保存过程时发生错误：{str(e)}")


class ApiCommand(BaseCommand):
    meta = CommandMeta(
        name="api",
        command_type="private",
        trigger="api",
        menu_text="选择API",
        show_in_menu=True,
        menu_weight=13,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        markup = Inline.print_api_list(info.get("tier", 0))
        if isinstance(markup, str):
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个api：", reply_markup=markup)
        await update.message.delete()


class PresetCommand(BaseCommand):
    meta = CommandMeta(
        name="preset",
        command_type="private",
        trigger="preset",
        menu_text="选择预设",
        show_in_menu=True,
        menu_weight=6,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        markup = Inline.print_preset_list()
        if isinstance(markup, str):
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个预设：", reply_markup=markup)
        await update.message.delete()


class LoadCommand(BaseCommand):
    meta = CommandMeta(
        name="load",
        command_type="private",
        trigger="load",
        menu_text="加载保存的对话",
        show_in_menu=False,
        menu_weight=7,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        markup = Inline.print_conversations(info["user_id"])
        if isinstance(markup, str):
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个对话：", reply_markup=markup)
        await update.message.delete()


class DeleteCommand(BaseCommand):
    meta = CommandMeta(
        name="delete",
        command_type="private",
        trigger="delete",
        menu_text="删除保存的对话",
        show_in_menu=False,
        menu_weight=7,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        markup = Inline.print_conversations(info["user_id"], "delete")
        if isinstance(markup, str):
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个对话：", reply_markup=markup)
        await update.message.delete()


class DialogCommand(BaseCommand):
    meta = CommandMeta(
        name="dialog",
        command_type="private",
        trigger="dialog",
        menu_text="对话管理",
        show_in_menu=True,
        menu_weight=5,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        info = public.update_info_get(update)
        if not info:
            return
        markup = Inline.print_dialog_conversations(info["user_id"])
        if isinstance(markup, str):
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个对话：", reply_markup=markup)
        await update.message.delete()


class SettingCommand(BaseCommand):
    meta = CommandMeta(
        name="setting",
        command_type="private",
        trigger="setting",
        menu_text="设置",
        show_in_menu=False,
        menu_weight=1,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        """
        处理设置命令，显示设置菜单。
        """
        keyboard = [
            [InlineKeyboardButton("对话管理", callback_data="settings_dialogue_main")],
            [InlineKeyboardButton("角色管理", callback_data="settings_character_main")],
            [InlineKeyboardButton("预设设置", callback_data="settings_preset_main")],
            [InlineKeyboardButton("状态查询", callback_data="settings_status_main")],
            [InlineKeyboardButton("我的信息", callback_data="settings_myinfo_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "请选择要管理的选项：", reply_markup=reply_markup
        )


class DirectorCommand(BaseCommand):
    meta = CommandMeta(
        name="director",
        command_type="private",
        trigger="director",
        menu_text="导演模式",
        show_in_menu=True,
        menu_weight=0,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        """
        处理导演模式命令，显示导演模式菜单。
        """
        keyboard = [
            [
                InlineKeyboardButton("推进", callback_data="director_nav_propel_menu"),
                InlineKeyboardButton("控制", callback_data="director_nav_control_menu"),
                InlineKeyboardButton("镜头", callback_data="director_nav_camera_menu"),
            ],
            [
                InlineKeyboardButton("重新生成", callback_data="director_act_regen"),
                InlineKeyboardButton("撤回", callback_data="director_act_undo"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "请选择导演模式操作：", reply_markup=reply_markup
        )
        await update.message.delete()


class SignCommand(BaseCommand):
    meta = CommandMeta(
        name="sign",
        command_type="private",
        trigger="sign",
        menu_text="签到获取额度",
        show_in_menu=True,
        menu_weight=1,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.from_user:
            return
        user_id = update.message.from_user.id
        sign_info = db.user_sign_info_get(user_id)
        if sign_info.get("last_sign") == 0:
            db.user_sign_info_create(user_id)
            sign_info = db.user_sign_info_get(user_id)
            await update.message.reply_text(
                f"签到成功！临时额度+50！\r\n你的临时额度为: {sign_info.get('frequency')}条(上限100)"
            )
        else:
            concurrent_time = datetime.datetime.now()
            last_sign_str = sign_info.get("last_sign")
            if not last_sign_str:
                await update.message.reply_text("签到时间数据异常，请联系管理员。")
                return
            try:
                last_sign_time = datetime.datetime.strptime(
                    str(last_sign_str), "%Y-%m-%d %H:%M:%S.%f"
                )
            except ValueError:
                try:
                    last_sign_time = datetime.datetime.strptime(
                        str(last_sign_str), "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError as e:
                    logger.error(f"无法解析签到时间格式: {last_sign_str}, 错误: {e}")
                    await update.message.reply_text("签到时间数据异常，请联系管理员。")
                    return
            time_delta = concurrent_time - last_sign_time
            total_seconds = time_delta.total_seconds()
            if total_seconds < 28800:  # 8小时 = 28800秒
                remaining_hours = (28800 - total_seconds) // 3600
                await update.message.reply_text(
                    f"您8小时内已完成过签到，您可以在{int(remaining_hours)}小时后再次签到。"
                )
            else:
                db.user_sign(user_id)
                sign_info = db.user_sign_info_get(
                    user_id
                )
                await update.message.reply_text(
                    f"签到成功！临时额度+50！\r\n你的临时额度为: {sign_info.get('frequency')}条(上限100)"
                )


class CryptoCommand(BaseCommand):
    meta = CommandMeta(
        name="crypto",
        command_type="private",
        trigger="c",
        menu_text="分析加密货币实时行情",
        show_in_menu=True,
        menu_weight=99,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return

        if not context.args:
            await update.message.reply_text(
                "请在 `/c` 命令后提供具体内容，例如：`/c 分析下大饼` 或 `/c long 分析下大饼`",
                parse_mode="Markdown",
            )
            return

        args = list(context.args)
        bias_type = "neutral"
        if args and args[0].lower() in ["long", "short"]:
            bias_type = args.pop(0).lower()

        if not args:
            await update.message.reply_text(
                f"请在 `/c {bias_type}` 后提供具体分析内容。",
                parse_mode="Markdown",
            )
            return
            
        user_input = " ".join(args)

        context.application.create_task(
            self.process_tool_request(update, user_input, bias_type), update=update
        )
        logger.debug("已创建后台任务处理 /c 请求")

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


class FeedbackCommand(BaseCommand):
    meta = CommandMeta(
        name="feedback",
        command_type="private",
        trigger="feedback",
        menu_text="发送反馈",
        show_in_menu=True,
        menu_weight=0,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        """
        处理用户反馈命令，将用户的反馈消息发送给所有管理员。
        命令格式: /feedback <反馈内容>
        """
        from utils.config_utils import ADMIN_LIST as ADMIN

        args = context.args if hasattr(context, "args") else []

        # 1. 参数校验
        if not args:
            await update.message.reply_text(
                "❌ 请提供反馈内容！\n\n"
                "格式：`/feedback <反馈内容>`\n\n"
                "💡 示例：`/feedback 建议增加更多角色选择`",
                parse_mode="Markdown",
            )
            return

        # 2. 获取反馈内容（所有参数组合）
        feedback_content = " ".join(args)

        if not feedback_content.strip():
            await update.message.reply_text(
                "❌ 反馈内容不能为空！\n请提供具体的反馈内容。", parse_mode="Markdown"
            )
            return

        # 3. 获取用户信息
        info = public.update_info_get(update)
        if not info:
            await update.message.reply_text("无法获取您的用户信息，反馈失败。")
            return
        user_info = f"用户ID: {info.get('user_id')}\n用户名: {info.get('user_name', '未知')}\n昵称: {info.get('first_name', '')} {info.get('last_name', '')}"

        # 4. 构建发送给管理员的消息
        admin_message = (
            f"📝 **用户反馈**\n\n"
            f"👤 **用户信息**\n{user_info}\n\n"
            f"💬 **反馈内容**\n{feedback_content}\n\n"
            f"🕐 **时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 5. 发送反馈给所有管理员
        success_count = 0
        failed_count = 0

        for admin_id in ADMIN:
            try:
                await send_message(context, admin_id, admin_message)
                success_count += 1
                logger.info(f"反馈已发送给管理员 {admin_id}")
            except Exception as e:
                failed_count += 1
                logger.warning(f"向管理员 {admin_id} 发送反馈失败: {str(e)}")

        # 6. 向用户发送确认消息
        if success_count > 0:
            await update.message.reply_text(
                f"✅ 反馈已成功发送给管理员！\n\n"
                f"📝 您的反馈：{feedback_content}\n\n"
                f"📊 发送状态：成功 {success_count} 个，失败 {failed_count} 个\n\n"
                f"💡 感谢您的反馈，我们会认真考虑您的建议！",
                parse_mode="Markdown",
            )

            # 记录用户反馈日志
            logger.info(
                f"用户 {info.get('user_id')} ({info.get('user_name', '未知')}) 发送反馈: {feedback_content}"
            )
        else:
            await update.message.reply_text(
                "❌ 反馈发送失败！\n\n"
                "所有管理员都无法接收消息，请稍后重试或联系技术支持。",
                parse_mode="Markdown",
            )
            logger.error(f"用户 {info.get('user_id')} 的反馈发送完全失败")
