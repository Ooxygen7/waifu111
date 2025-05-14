import asyncio
import json
import os
import re
from pathlib import Path

from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot_core.public_functions.conversation import Conversation
import bot_core.public_functions.update_parse as public
from bot_core.callback_handlers.inline import Inline
from bot_core.public_functions.logging import logger
from utils import db_utils as db, LLM_utils as llm
from .base import BaseCommand, CommandMeta


class StartCommand(BaseCommand):
    meta = CommandMeta(
        name='start',
        command_type='private',
        trigger='start',
        menu_text='开始使用 CyberWaifu',
        show_in_menu=True,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        info = public.update_info_get(update)
        await update.message.reply_text(
            f"您好，{info['first_name']} {info['last_name']}！这是由 @Xi_cuicui 开发的`CyberWaifu`项目。\r\n已为您创建用户档案。\r\n使用`/char`可以切换角色\r\n"
            f"使用`/setting`可以管理您的对话与角色设置\r\n"
        )


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
        info = public.update_info_get(update)
        mark = False
        try:
            msg_list = db.conversation_latest_message_id_get(info['conv_id'])
            print(msg_list)
            await context.bot.delete_messages(info['user_id'], msg_list)
            await context.bot.delete_message(info['user_id'], update.message.id)
            mark = db.conversation_delete_messages(info['conv_id'], msg_list[0]) and db.conversation_delete_messages(
                info['conv_id'], msg_list[1])
            if mark:
                await update.message.reply_text(f"撤回成功！")
        except Exception as e:
            if mark:
                await update.message.reply_text(f"无法删除消息：{str(e)}\r\n实际消息记录已撤回处理")


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
            f"您的帐户等级是：`{info['tier']}`；\r\n"
            f"您剩余额度还有`{info['remain']}`条；\r\n"
            f"您的余额是`{info['balance']}`。\r\n"
            f"您的对话昵称是`{info['user_nick']}`"
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
        conversation = Conversation(info)
        conversation.new('private')
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

            async def create_summary(conv_id, placeholder_message):
                summary = await llm.generate_summary(conv_id)
                if db.conversation_private_summary_add(conv_id, summary):
                    logger.info(f"保存对话并生成总结, conv_id: {conv_id}, summary: {summary}")
                    await placeholder_message.edit_text(f"保存成功，对话总结:`{summary}`")
                else:
                    await placeholder_message.edit_text("保存失败")

            task = asyncio.create_task(create_summary(config['conv_id'], placeholder_message))
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
        info = public.update_info_get(update)
        conversation = Conversation(info)
        try:
            await context.bot.delete_message(info['user_id'], update.message.id)
        except Exception as e:
            print(f"Failed to delete user message: {e}")
        try:
            await context.bot.delete_message(info['user_id'], conversation.latest_message_id[0])
        except Exception as e:
            print(f"Failed to delete latest message: {e}")
        _placeholder_message = await update.message.reply_text(f"重新生成...")

        async def _regen(placeholder_message):
            try:
                conversation.set_send_msg_id(placeholder_message.message_id)
                await conversation.regenerate_response()
                await placeholder_message.edit_text(conversation.cleared_response_text)
                conversation.save_to_db('assistant')
            except Exception as e:
                await placeholder_message.edit_text(f"重新生成失败！{e}")

        _task = asyncio.create_task(_regen(_placeholder_message))


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
        conversation = Conversation(public.update_info_get(update))
        conversation.new('private')
        markup = Inline.print_char_list('load', 'private', conversation.info['user_id'])
        if markup == "没有可操作的角色。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个角色：", reply_markup=markup)


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

            async def _generate_char(placeholder_message, desc, save_dir, char_name, user_id, context):
                generated_content = None
                try:
                    generated_content = await llm.generate_char(desc)
                    json_pattern = r'```json\s*([\s\S]*?)\s*```|```([\s\S]*?)\s*```|\{[\s\S]*\}'
                    match = re.search(json_pattern, generated_content)
                    if match:
                        json_str = next(group for group in match.groups() if group)
                        char_data = json.loads(json_str)
                        save_path = os.path.join(save_dir, f"{char_name}_{user_id}.json")
                        with open(save_path, 'w', encoding='utf-8') as f:
                            json.dump(char_data, f, ensure_ascii=False, indent=2)
                        await placeholder_message.edit_text(f"角色 {char_name} 已保存到 {save_path}")
                    else:
                        save_path = os.path.join(save_dir, f"{char_name}_{user_id}.txt")
                        with open(save_path, 'w', encoding='utf-8') as f:
                            f.write(generated_content)
                        await placeholder_message.edit_text(
                            "警告：未能从生成内容中提取 JSON 数据，保存原始内容到 {save_path}。")
                except json.JSONDecodeError as e:
                    save_path = os.path.join(save_dir, f"{char_name}_{user_id}.txt")
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(generated_content)
                    await placeholder_message.edit_text(
                        f"错误：无法解析生成的 JSON 内容，保存为原始文本到 {save_path}。错误信息：{str(e)}")
                except Exception as e:
                    await placeholder_message.edit_text(f"保存角色 {char_name} 时发生错误：{str(e)}")
                finally:
                    if user_id in context.bot_data.get('newchar_state', {}):
                        del context.bot_data['newchar_state'][user_id]

            task = asyncio.create_task(_generate_char(placeholder_message, desc, save_dir, char_name, user_id, context))
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
