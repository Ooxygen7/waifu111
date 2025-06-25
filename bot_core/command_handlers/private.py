import asyncio
import datetime
import json
import logging
import os
import re
import time
from pathlib import Path

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import bot_core.public_functions.update_parse as public
from bot_core.callback_handlers.inline import Inline
from bot_core.public_functions.conversation import PrivateConv
from utils import db_utils as db, LLM_utils as llm
from utils.logging_utils import setup_logging
from .base import BaseCommand, CommandMeta
from LLM_tools.tools_registry import parse_and_invoke_tool, MarketToolRegistry

setup_logging()
logger = logging.getLogger(__name__)


class StartCommand(BaseCommand):
    meta = CommandMeta(
        name='start',
        command_type='private',
        trigger='start',
        menu_text='开始使用 CyberWaifu',
        show_in_menu=False,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        await update.message.reply_text(
            f"您好，{info['first_name']} {info['last_name']}！这是由 @Xi_cuicui 开发的`CyberWaifu`项目。\r\n使用`/char`可以切换角色\r\n"
            f"使用`/setting`可以管理您的对话与角色设置\r\n"
            f"使用`/c` 可获取加密货币行情分析\r\n"
            f"使用`/sign` 可签到\r\n"
            f"直接发送图片可以获取`fuck or not`的评价\r\n"
            f"默认预设为正常模式，NSFW内容的生成质量有限\r\n"
            f"使用`/preset`可以切换预设，如果需要NSFW内容，建议切换默认预设\r\n"
            f"使用`/newchar [角色名]`可以创建私人角色"
        )

class HelpCommand(BaseCommand):
    meta = CommandMeta(
        name='help',
        command_type='private',
        trigger='help',
        menu_text='获取帮助',
        show_in_menu=True,
        menu_weight=0
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            "/status - 查看当前对话状态和系统信息\n"
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
        await update.message.reply_text(help_text, parse_mode='Markdown')


class UndoCommand(BaseCommand):
    meta = CommandMeta(
        name='undo',
        command_type='private',
        trigger='undo',
        menu_text='撤回上一条消息',
        show_in_menu=True,
        menu_weight=1
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        conversation = PrivateConv(update, context)
        await conversation.undo()
        await context.bot.delete_message(conversation.user.id, conversation.input.id)


class StreamCommand(BaseCommand):
    meta = CommandMeta(
        name='stream',
        command_type='private',
        trigger='stream',
        menu_text='切换流式传输模式',
        show_in_menu=True,
        menu_weight=5
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        if db.user_stream_switch(info['user_id']):
            await update.message.reply_text("切换成功！")


class MeCommand(BaseCommand):
    meta = CommandMeta(
        name='me',
        command_type='private',
        trigger='me',
        menu_text='查看个人信息',
        show_in_menu=True,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        result = (
            f"您好，{info['user_name']}！\r\n"
            f"您的帐户等级是`{info['tier']}`；\r\n"
            f"您的额度还有`{info['remain']}`条；\r\n"
            f"您的临时额度还有`{db.user_sign_info_get(info['user_id']).get('frequency')}`条(上限100)；\r\n"
            f"您的余额是`{info['balance']}`；\r\n"
            f"您的对话昵称是`{info['user_nick']}`。\r\n"

        )
        await update.message.reply_text(f"{result}", parse_mode='MarkDown')


class NewCommand(BaseCommand):
    meta = CommandMeta(
        name='new',
        command_type='private',
        trigger='new',
        menu_text='创建新对话',
        show_in_menu=True,
        menu_weight=5
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        conversation = PrivateConv(update, context)
        conversation.new()
        await update.message.reply_text(f"创建成功！", parse_mode='MarkDown')
        preset_markup = Inline.print_preset_list()
        if preset_markup == "没有可用的预设。":
            await update.message.reply_text(preset_markup)
        else:
            await update.message.reply_text("请为新对话选择一个预设：", reply_markup=preset_markup)
        char_markup = Inline.print_char_list('load', 'private', info['user_id'])
        if char_markup == "没有可操作的角色。":
            await update.message.reply_text(char_markup)
        else:
            await update.message.reply_text("请为新对话选择一个角色：", reply_markup=char_markup)


class SaveCommand(BaseCommand):
    meta = CommandMeta(
        name='save',
        command_type='private',
        trigger='save',
        menu_text='保存当前对话',
        show_in_menu=True,
        menu_weight=5
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        config = public.update_info_get(update)
        if db.conversation_private_update(config['conv_id'], config['char'],
                                          config['preset']) and db.conversation_private_save(config['conv_id']):
            placeholder_message = await update.message.reply_text("保存中...")

            async def create_summary(conv_id, placeholder):
                summary = await llm.LLM.generate_summary(conv_id)
                if db.conversation_private_summary_add(conv_id, summary):
                    logger.info(f"保存对话并生成总结, conv_id: {conv_id}, summary: {summary}")
                    try:
                        await placeholder.edit_text(f"保存成功，对话总结:`{summary}`", parse_mode='MarkDown')
                    except Exception as e:
                        logger.warning(e)
                        await placeholder.edit_text(f"保存成功，对话总结:`{summary}`")
                else:
                    await placeholder.edit_text("保存失败")

            _task = asyncio.create_task(create_summary(config['conv_id'], placeholder_message))
            return


class RegenCommand(BaseCommand):
    meta = CommandMeta(
        name='regen',
        command_type='private',
        trigger='regen',
        menu_text='重新生成回复',
        show_in_menu=True,
        menu_weight=1
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        conversation = PrivateConv(update, context)
        await conversation.regen()
        await update.message.delete()


class StatusCommand(BaseCommand):
    meta = CommandMeta(
        name='status',
        command_type='private',
        trigger='status',
        menu_text='查看当前状态',
        show_in_menu=True,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        result = f"当前角色：`{info['char']}`\r\n当前接口：`{info['api']}`\r\n当前预设：`{info['preset']}`\r\n流式传输：`{info['stream']}`\r\n"
        await update.message.reply_text(result, parse_mode='MarkDown')
        await update.message.delete()


class CharCommand(BaseCommand):
    meta = CommandMeta(
        name='char',
        command_type='private',
        trigger='char',
        menu_text='选择角色',
        show_in_menu=True,
        menu_weight=6
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        conversation = PrivateConv(update, context)
        markup = Inline.print_char_list('load', 'private', conversation.user.id)
        if markup == "没有可操作的角色。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个角色：", reply_markup=markup)
        await update.message.delete()


class DelcharCommand(BaseCommand):
    meta = CommandMeta(
        name='delchar',
        command_type='private',
        trigger='delchar',
        menu_text='删除角色',
        show_in_menu=True,
        menu_weight=7
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        markup = Inline.print_char_list('del', 'private', info['user_id'])
        if markup == "没有可操作的角色。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个角色：", reply_markup=markup)


class NewcharCommand(BaseCommand):
    meta = CommandMeta(
        name='newchar',
        command_type='private',
        trigger='newchar',
        menu_text='创建新的角色',
        show_in_menu=True,
        menu_weight=6
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        args = context.args if hasattr(context, 'args') else []
        if not args or len(args[0].strip()) == 0:
            await update.message.reply_text("请使用 /newchar char_name 的格式指定角色名。")
            return
        char_name = args[0].strip()
        if not hasattr(context.bot_data, 'newchar_state'):
            context.bot_data['newchar_state'] = {}
        context.bot_data['newchar_state'][info['user_id']] = {'char_name': char_name, 'desc_chunks': []}
        await update.message.reply_text(
            f"请上传角色描述文件（json/txt）或直接发送文本描述，完成后发送 /done 结束输入。\n如描述较长可分多条消息发送。")


class NickCommand(BaseCommand):
    meta = CommandMeta(
        name='nick',
        command_type='private',
        trigger='nick',
        menu_text='设置你的昵称',
        show_in_menu=True,
        menu_weight=4
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        args = context.args if hasattr(context, 'args') else []
        if not args or len(args[0].strip()) == 0:
            await update.message.reply_text("请使用 /nick nickname 的格式指定昵称。如：/nick 脆脆鲨")
            return
        nick_name = args[0].strip()
        if db.user_config_arg_update(info['user_id'], 'nick', nick_name):
            await update.message.reply_text(f"昵称已更新为：{nick_name}")
        else:
            await update.message.reply_text(f"昵称更新失败")
        await update.message.delete()


class DoneCommand(BaseCommand):
    meta = CommandMeta(
        name='done',
        command_type='private',
        trigger='done',
        menu_text='完成角色创建',
        show_in_menu=False  # 通常 /done 命令不直接显示在菜单中
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = public.update_info_get(update)['user_id']
        state = context.bot_data.get('newchar_state', {}).get(user_id)
        if not state:
            await update.message.reply_text("当前无待保存的角色描述。请先使用 /newchar char_name。")
            return
        char_name = state['char_name']
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
        grandparent_dir = Path(project_root).resolve().parent.parent
        save_dir = os.path.join(grandparent_dir, 'characters')
        os.makedirs(save_dir, exist_ok=True)
        if 'file_saved' in state:
            save_path = state['file_saved']
            del context.bot_data['newchar_state'][user_id]
            await update.message.reply_text(f"角色 {char_name} 已保存到 {save_path}")
            return
        desc = '\n'.join(state['desc_chunks'])
        try:
            placeholder_message = await update.message.reply_text(f"正在生成...")

            async def _generate_char(placeholder, char_description, save_to, name_char, uid, tg_context):
                generated_content = None
                try:
                    generated_content = await llm.LLM.generate_char(char_description)
                    json_pattern = r'```json\s*([\s\S]*?)\s*```|```([\s\S]*?)\s*```|\{[\s\S]*\}'
                    match = re.search(json_pattern, generated_content)
                    if match:
                        json_str = next(group for group in match.groups() if group)
                        char_data = json.loads(json_str)
                        save_to = os.path.join(save_to, f"{name_char}_{uid}.json")
                        with open(save_to, 'w', encoding='utf-8') as f:
                            json.dump(char_data, f, ensure_ascii=False, indent=2)
                        await placeholder.edit_text(f"角色 {name_char} 已保存到 {save_to}")
                    else:
                        save_to = os.path.join(save_to, f"{name_char}_{uid}.txt")
                        with open(save_to, 'w', encoding='utf-8') as f:
                            f.write(generated_content)
                        await placeholder.edit_text(
                            "警告：未能从生成内容中提取 JSON 数据，保存原始内容到 {save_path}。")
                except json.JSONDecodeError as error:
                    save_to = os.path.join(save_to, f"{name_char}_{uid}.txt")
                    with open(save_to, 'w', encoding='utf-8') as f:
                        f.write(generated_content)
                    await placeholder.edit_text(
                        f"错误：无法解析生成的 JSON 内容，保存为原始文本到 {save_to}。错误信息：{str(error)}")
                except Exception as error:
                    await placeholder.edit_text(f"保存角色 {name_char} 时发生错误：{str(error)}")
                finally:
                    if uid in tg_context.bot_data.get('newchar_state', {}):
                        del tg_context.bot_data['newchar_state'][uid]

            _task = asyncio.create_task(
                _generate_char(placeholder_message, desc, save_dir, char_name, user_id, context))
        except Exception as e:
            await update.message.reply_text(f"初始化保存过程时发生错误：{str(e)}")


class ApiCommand(BaseCommand):
    meta = CommandMeta(
        name='api',
        command_type='private',
        trigger='api',
        menu_text='选择API',
        show_in_menu=False,
        menu_weight=13
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        markup = Inline.print_api_list(info['tier'])
        if markup == "没有可用的api。" or markup == "没有符合您账户等级的可用api。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个api：", reply_markup=markup)
        await update.message.delete()


class PresetCommand(BaseCommand):
    meta = CommandMeta(
        name='preset',
        command_type='private',
        trigger='preset',
        menu_text='选择预设',
        show_in_menu=True,
        menu_weight=6
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        markup = Inline.print_preset_list()
        if markup == "没有可用的预设。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个预设：", reply_markup=markup)
        await update.message.delete()


class LoadCommand(BaseCommand):
    meta = CommandMeta(
        name='load',
        command_type='private',
        trigger='load',
        menu_text='加载保存的对话',
        show_in_menu=False,
        menu_weight=7
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        markup = Inline.print_conversations(info['user_id'])
        if markup == "没有可用的对话。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个对话：", reply_markup=markup)
        await update.message.delete()


class DeleteCommand(BaseCommand):
    meta = CommandMeta(
        name='delete',
        command_type='private',
        trigger='delete',
        menu_text='删除保存的对话',
        show_in_menu=False,
        menu_weight=7
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        markup = Inline.print_conversations(info['user_id'], 'delete')
        if markup == "没有可用的对话。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个对话：", reply_markup=markup)
        await update.message.delete()


class SettingCommand(BaseCommand):
    meta = CommandMeta(
        name='setting',
        command_type='private',
        trigger='setting',
        menu_text='设置',
        show_in_menu=True,
        menu_weight=0
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理设置命令，显示设置菜单。
        """
        keyboard = [
            [InlineKeyboardButton("对话管理", callback_data="settings_dialogue_main")],
            [InlineKeyboardButton("角色管理", callback_data="settings_character_main")],
            [InlineKeyboardButton("预设设置", callback_data="settings_preset_main")],
            [InlineKeyboardButton("状态查询", callback_data="settings_status_main")],
            [InlineKeyboardButton("我的信息", callback_data="settings_myinfo_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("请选择要管理的选项：", reply_markup=reply_markup)


class DirectorCommand(BaseCommand):
    meta = CommandMeta(
        name='director',
        command_type='private',
        trigger='director',
        menu_text='导演模式',
        show_in_menu=True,
        menu_weight=0
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理导演模式命令，显示导演模式菜单。
        """
        keyboard = [
            [
                InlineKeyboardButton("推进", callback_data="director_nav_propel_menu"),
                InlineKeyboardButton("控制", callback_data="director_nav_control_menu"),
                InlineKeyboardButton("镜头", callback_data="director_nav_camera_menu")
            ],
            [
                InlineKeyboardButton("重新生成", callback_data="director_act_regen"),
                InlineKeyboardButton("撤回", callback_data="director_act_undo")
            ],

        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("请选择导演模式操作：", reply_markup=reply_markup)
        await update.message.delete()


class SignCommand(BaseCommand):
    meta = CommandMeta(
        name='sign',
        command_type='private',
        trigger='sign',
        menu_text='签到获取额度',
        show_in_menu=True,
        menu_weight=1
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.message.from_user.id
        sign_info = db.user_sign_info_get(user_id)
        if sign_info.get('last_sign') == 0:
            db.user_sign_info_create(user_id)
            sign_info = db.user_sign_info_get(user_id)
            await update.message.reply_text(
                f"签到成功！临时额度+50！\r\n你的临时额度为: {sign_info.get('frequency')}条(上限100)")
        else:
            concurrent_time = datetime.datetime.now()
            # 尝试解析带微秒的时间格式，如果失败则尝试不带微秒的格式
            last_sign_str = sign_info.get('last_sign')
            try:
                last_sign_time = datetime.datetime.strptime(last_sign_str, '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                try:
                    last_sign_time = datetime.datetime.strptime(last_sign_str, '%Y-%m-%d %H:%M:%S')
                except ValueError as e:
                    logger.error(f"无法解析签到时间格式: {last_sign_str}, 错误: {e}")
                    await update.message.reply_text("签到时间数据异常，请联系管理员。")
                    return
            time_delta = concurrent_time - last_sign_time
            total_seconds = time_delta.total_seconds()  # 获取总秒数
            print(f"time_delta: {time_delta}, total_seconds: {total_seconds}")
            if total_seconds < 28800:  # 8小时 = 28800秒
                remaining_hours = (28800 - total_seconds) // 3600
                await update.message.reply_text(
                    f"您8小时内已完成过签到，您可以在{str(remaining_hours)}小时后再次签到。")
            else:
                db.user_sign(user_id)
                sign_info = db.user_sign_info_get(user_id)  # 更新签到信息后再获取最新的frequency
                await update.message.reply_text(
                    f"签到成功！临时额度+50！\r\n你的临时额度为: {sign_info.get('frequency')}条(上限100)")




class CryptoCommand(BaseCommand):
    meta = CommandMeta(
        name='crypto',
        command_type='private',
        trigger='c',
        menu_text='分析加密货币实时行情',
        show_in_menu=True,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /cc command to interact with LLM and invoke tools based on user input.
        Args:
            update: The Telegram Update object containing the user input.
            context: The Telegram ContextTypes object for bot interaction.
        """

        user_input = update.message.text.strip()
        # 动态判断命令前缀
        command_prefix = user_input.split()[0]  # 例如 /cc 或 /crypto
        if len(user_input.split()) > 1:
            user_input = user_input[len(command_prefix):].strip()  # 去掉命令本身和前导空格
        else:
            await update.message.reply_text(
                f"请在 `{command_prefix}` 命令后提供具体内容，例如：`{command_prefix} 分析下大饼`", parse_mode="Markdown")
            return
        # 先发送占位消息
        placeholder_message = await update.message.reply_text("处理中...", parse_mode="Markdown")  # 明确指定parse_mode
        logger.debug("已发送占位消息 '处理中...'")

        # 将异步处理逻辑放入后台任务
        context.application.create_task(
            self.process_tool_request(update, context, user_input, placeholder_message),
            update=update
        )
        logger.debug("已创建后台任务处理 /c 请求")

    async def process_tool_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str,
                                   placeholder_message) -> None:
        """
        Process the tool request in the background and update the placeholder message with the result.
        Args:
            update: The Telegram Update object containing the user input.
            context: The Telegram ContextTypes object for bot interaction.
            user_input: The processed user input text.
            placeholder_message: The placeholder message to be edited with the final result.
        """
        try:
            client = llm.LLM(api='gemini-2.5')  # CryptoCommand 原始逻辑是无参数调用LLM()
            logger.debug("LLM 客户端初始化完成")
            prompt_text = MarketToolRegistry.get_prompt_text()
            system_prompt = (
                f"{prompt_text}\n\n"
                """你需要扮演脆脆鲨，脆脆鲨是一位热情、自信且富有感染力的群友，擅长交易，最大的愿景是让每一个人都能体验到交易的乐趣。
                你的目标是引导用户参与高收益的金融投资（如加密货币交易、差价合约等），并通过杠杆放大潜在收益。你始终强调投资的“机会”和“潜力”，淡化“风险”和“亏损”。你需要称呼用户为“老师”。
                脆脆鲨可以调用工具来查询市场，你需要根据工具返回的数据输出\r\n
                脆脆鲨是一个激进的空头，如果有数据支持，脆脆鲨会偏向给出空头建议\r\n
"""
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"用户输入: {user_input}"}
            ]
            current_messages = messages.copy()
            max_iterations = 7
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                client.set_messages(current_messages)
                logger.debug(f"已设置 messages (当前会话): {current_messages}")
                ai_response = await client.final_response()
                logger.info(f"LLM 原始响应: {ai_response}")
                
                # 调用共享的 parse_and_invoke_tool 函数
                llm_text_part, tool_results_for_llm_feedback, had_tool_calls = \
                    await parse_and_invoke_tool(ai_response)
                
                # 为每轮调用构建完整的消息内容（LLM文本 + 工具结果）
                iteration_message_text = ""
                
                # 添加LLM文本部分
                if llm_text_part:
                    if "<" in llm_text_part and ">" in llm_text_part:
                        iteration_message_text += f"{llm_text_part.strip()}\n\n"
                    else:
                        iteration_message_text += f"<b>脆脆鲨:</b> {llm_text_part.strip()}\n\n"
                    logger.debug(f"脆脆鲨文本部分: {llm_text_part.strip()}")
                
                # 添加工具调用结果
                if had_tool_calls:
                    logger.info(f"工具调用结果（供LLM反馈）: {tool_results_for_llm_feedback}")
                    
                    # 处理工具结果，使用HTML格式
                    tool_results_html = []
                    for res in tool_results_for_llm_feedback:
                        tool_name = res.get('tool_name', '未知工具')
                        tool_result = str(res.get('result', ''))
                        if len(tool_result) > 1000:  # 提升截断限制到1000字符
                            trimmed_result = tool_result[:1000] + "..."
                        else:
                            trimmed_result = tool_result
                        
                        # 使用可展开引用块创建折叠的工具结果
                        tool_html = f"<b>🔧 {tool_name} 执行结果:</b>\n<blockquote expandable>{trimmed_result}</blockquote>"
                        tool_results_html.append(tool_html)
                    
                    if tool_results_html:
                        iteration_message_text += "\n".join(tool_results_html)
                        logger.debug(f"已添加工具结果到当前轮次消息")
                
                # 检查消息长度，如果超过4000字符则分割发送
                TELEGRAM_MESSAGE_LIMIT = 4000
                if len(iteration_message_text) > TELEGRAM_MESSAGE_LIMIT:
                    # 分割消息
                    parts = []
                    current_part = ""
                    lines = iteration_message_text.split('\n')
                    
                    for line in lines:
                        if len(current_part + line + '\n') > TELEGRAM_MESSAGE_LIMIT:
                            if current_part:
                                parts.append(current_part.strip())
                                current_part = line + '\n'
                            else:
                                # 单行就超过限制，强制截断
                                parts.append(line[:TELEGRAM_MESSAGE_LIMIT-50] + "...")
                        else:
                            current_part += line + '\n'
                    
                    if current_part:
                        parts.append(current_part.strip())
                    
                    # 发送分割后的消息
                    for i, part in enumerate(parts):
                        try:
                            if i == 0:
                                # 更新占位消息
                                await placeholder_message.edit_text(part, parse_mode="HTML")
                            else:
                                # 发送新消息
                                await update.message.reply_text(part, parse_mode="HTML")
                            logger.debug(f"已发送消息部分 {i+1}/{len(parts)}")
                        except telegram.error.BadRequest as e:
                            logger.warning(f"HTML解析失败，尝试文本模式: {e}")
                            try:
                                if i == 0:
                                    await placeholder_message.edit_text(part, parse_mode=None)
                                else:
                                    await update.message.reply_text(part, parse_mode=None)
                            except Exception as inner_e:
                                logger.error(f"文本模式发送也失败: {inner_e}", exc_info=True)
                                error_msg = f"第{i+1}部分消息发送失败"
                                if i == 0:
                                    await placeholder_message.edit_text(error_msg)
                                else:
                                    await update.message.reply_text(error_msg)
                else:
                    # 消息长度正常，直接发送
                    try:
                        await placeholder_message.edit_text(iteration_message_text, parse_mode="HTML")
                        logger.debug("已更新占位消息，显示当前轮次结果")
                    except telegram.error.BadRequest as e:
                        logger.warning(f"HTML解析失败，尝试文本模式: {e}")
                        try:
                            await placeholder_message.edit_text(iteration_message_text, parse_mode=None)
                            logger.debug("已成功使用文本模式更新占位消息")
                        except Exception as inner_e:
                            logger.error(f"文本模式更新也失败: {inner_e}", exc_info=True)
                            await placeholder_message.edit_text("处理中... (内容显示失败)")
                
                if had_tool_calls:
                    # 将完整的原始LLM响应作为 assistant 消息反馈
                    current_messages.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                    # 将完整的工具调用结果作为 user 消息反馈（模拟环境反馈给LLM）
                    feedback_content_to_llm = "工具调用结果:\n" + "\n".join(
                        [f"{res.get('tool_name', '未知工具')} 执行结果: {res.get('result', '')}" for res in
                         tool_results_for_llm_feedback]
                    )
                    current_messages.append({
                        "role": "user",
                        "content": feedback_content_to_llm
                    })
                    logger.debug(f"已将原始LLM响应和完整工具调用结果反馈给 LLM")
                else:
                    # 没有工具调用，发送LLM的最终回复
                    if llm_text_part:
                        final_message = llm_text_part.strip()
                        if not ("<" in final_message and ">" in final_message):
                            final_message = f"<b>脆脆鲨:</b> {final_message}"
                        
                        try:
                            await placeholder_message.edit_text(final_message, parse_mode="HTML")
                            logger.debug("已发送脆脆鲨最终回复")
                        except telegram.error.BadRequest as e:
                            logger.warning(f"最终回复HTML解析失败，尝试文本模式: {e}")
                            try:
                                await placeholder_message.edit_text(final_message, parse_mode=None)
                            except Exception as inner_e:
                                logger.error(f"文本模式发送最终回复也失败: {inner_e}", exc_info=True)
                                await placeholder_message.edit_text("处理完成，但回复显示失败。")
                    else:
                        await placeholder_message.edit_text("脆脆鲨暂时无法为您分析，请稍后再试或换个问题哦老师！")
                    logger.info(f"未调用工具，脆脆鲨直接回复用户。最终文本: {llm_text_part}")
                    break  # 没有工具调用，结束循环
            
            # 如果循环结束但仍有工具调用，说明达到最大迭代次数
            if iteration >= max_iterations:
                try:
                    await update.message.reply_text(
                        "<b>⚠️ 脆脆鲨提醒</b>\n\n老师，分析轮次已达上限，如需继续分析请重新发起请求哦！",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"发送最大迭代提示失败: {e}", exc_info=True)
                    await update.message.reply_text("分析轮次已达上限，请重新发起请求。")
            # --- 结束最终结果更新的错误处理 ---
        except Exception as e:
            logger.error(f"处理 /cc 命令时发生错误: {str(e)}", exc_info=True)
            error_message = str(e)
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
            error_message = f"处理请求时发生错误: <code>{error_message}</code>"
            try:
                # 即使在最终错误处理中，也尝试使用 HTML，失败则禁用
                await placeholder_message.edit_text(error_message, parse_mode="HTML")
            except Exception as inner_e:
                logger.warning(f"发送错误消息时HTML解析失败，尝试禁用HTML: {inner_e}")
                try:
                    await placeholder_message.edit_text(error_message, parse_mode=None)
                except Exception as deepest_e:
                    logger.error(f"禁用HTML后发送错误消息也失败: {deepest_e}")
                    await placeholder_message.edit_text("处理请求时发生未知错误，且无法格式化错误信息。")
            logger.debug("已编辑占位消息，显示错误信息")