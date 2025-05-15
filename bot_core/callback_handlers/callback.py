# callback.py
import importlib
import inspect,asyncio
import os,time
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes

import bot_core.public_functions.update_parse as public
from bot_core.callback_handlers.base import BaseCallback, CallbackMeta
from bot_core.public_functions.error import BotError
from bot_core.public_functions.update_parse import update_info_get
from utils import db_utils as db
from .director_classes import DirectorMenu
from .inline import Inline
from ..public_functions.conversation import Conversation

from ..public_functions.logging import logger

# 设置日志配置

default_char = 'cuicuishark_public'


class SetCharCallback(BaseCallback):
    meta = CallbackMeta(
        name='set_char',
        callback_type='private',
        trigger='set_char_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理角色设置回调。
        """
        try:
            character = data
            info = public.update_info_get(update)
            if db.user_config_arg_update(info['user_id'], 'char', character):
                await update.callback_query.message.edit_text(
                    f"角色切换成功！会话已重开！当前角色: {character.split('_')[0]}。")
                # 加载角色文件并发送问候语
                from utils import file_utils  # 确保导入
                # 构建角色文件名，通常角色参数可能包含 user_id 后缀，需要正确处理
                # 假设 character 参数的格式是 'charname_userid' 或 'charname'
                char_file_name_parts = character.split('_')
                actual_char_name = char_file_name_parts[0]  # 取角色基本名
                # 尝试几种常见的文件名格式
                possible_filenames = [
                    f"{character}.json",  # 完整名.json (e.g., charname_123.json)
                    f"{actual_char_name}.json"  # 基本名.json (e.g., charname.json)
                ]
                char_data = None
                for fname in possible_filenames:
                    char_data = file_utils.load_char(fname)
                    if char_data:
                        break

                if char_data and 'meeting' in char_data:
                    meeting_message = char_data['meeting']
                    # 使用 query.message.reply_text 发送新消息，而不是 edit_text 修改回调按钮下的消息
                    await update.callback_query.message.reply_text(meeting_message)
                    info = public.update_info_get(update)
                    db.dialog_content_add(info['conv_id'], 'assistant', 1, meeting_message,
                                          meeting_message, 0, 'private')
                elif char_data is None:
                    logger.warning(f"未能加载角色 {character} 的数据文件。")
        except Exception as e:
            logger.error(f"设置角色失败, 错误: {str(e)}")


class DelCharCallback(BaseCallback):
    meta = CallbackMeta(
        name='del_char',
        callback_type='private',
        trigger='del_char_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理角色删除回调。
        """
        import random
        character = data
        info = public.update_info_get(update)
        db.user_config_arg_update(info['user_id'], 'char', default_char)
        db.conversation_private_arg_update(info['conv_id'], 'character', default_char)
        # 处理角色文件重命名逻辑
        char_dir = './characters/'
        json_path = os.path.join(char_dir, f'{character}.json')
        txt_path = os.path.join(char_dir, f'{character}.txt')
        delmark = str(random.randint(100000, 999999))
        if os.path.exists(json_path):
            del_path = os.path.join(char_dir, f'{character}_{delmark}_del.json')
            os.rename(json_path, del_path)
        elif os.path.exists(txt_path):
            del_path = os.path.join(char_dir, f'{character}_{delmark}_del.txt')
            os.rename(txt_path, del_path)
        await update.callback_query.message.edit_text(
            f"角色`{character.split('_')[0]}`删除成功！已为您切换默认角色`cuicuishark` 。")


class SetApiCallback(BaseCallback):
    meta = CallbackMeta(
        name='set_api',
        callback_type='private',
        trigger='set_api_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理API设置回调。
        """
        try:
            info = public.update_info_get(update)
            if db.user_config_arg_update(info['user_id'], 'api', data):
                await update.callback_query.message.edit_text(f"api切换成功！当前api: {data}。")
        except Exception as e:
            logger.error(f"设置api失败, 错误: {str(e)}")


class SetPresetCallback(BaseCallback):
    meta = CallbackMeta(
        name='set_preset',
        callback_type='private',
        trigger='set_preset_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理预设设置回调。
        """
        try:
            info = public.update_info_get(update)
            if db.user_config_arg_update(info['user_id'], 'preset', data):
                await update.callback_query.message.edit_text(f"预设切换成功！当前预设: {data}。")
        except Exception as e:
            logger.error(f"设置预设失败, 错误: {str(e)}")


class SetConversationCallback(BaseCallback):
    meta = CallbackMeta(
        name='set_conversation',
        callback_type='private',
        trigger='set_conv_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理对话加载回调。
        """
        try:
            info = public.update_info_get(update)
            if db.user_config_arg_update(info['user_id'], 'conv_id', data):
                char, preset = db.conversation_private_get(data)
                if db.user_config_arg_update(info['user_id'], 'preset', preset) and db.user_config_arg_update(
                        info['user_id'], 'char', char):
                    await update.callback_query.message.edit_text(f"加载对话成功！当前对话: {data}。")
        except Exception as e:
            logger.error(f"设置对话失败, 错误: {str(e)}")


class DelConversationCallback(BaseCallback):
    meta = CallbackMeta(
        name='del_conversation',
        callback_type='private',
        trigger='del_conv_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理对话删除回调。
        """
        db.conversation_private_delete(data)
        await update.callback_query.message.edit_text(f"删除对话成功！删除了对话: {data}。")


class GroupCharCallback(BaseCallback):
    meta = CallbackMeta(
        name='group_char',
        callback_type='group',
        trigger='group_char_',
        enabled=True,
        group_admin_required=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理群组角色设置回调。
        """
        try:
            parts = data.split('_')
            char = f"{parts[0]}_{parts[1]}"
            group_id = int(parts[2])
            db.group_info_update(group_id, 'char', char)
            await update.callback_query.message.edit_text(f"切换角色成功！当前角色: {char.split('_')[0]}。")
        except Exception as e:
            logger.error(f"设置群组角色失败, 错误: {str(e)}")


class GroupKeywordCancelCallback(BaseCallback):
    meta = CallbackMeta(
        name='group_keyword_cancel',
        callback_type='group',
        trigger='group_kw_cancel_',
        enabled=True,
        group_admin_required=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理关键词取消回调
        """
        query = update.callback_query
        await query.answer()
        group_id = int(query.data.split('_')[-1])
        original_message_id = context.user_data.get('original_message_id')
        if original_message_id:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=query.message.chat.id,
                    message_id=original_message_id,
                    reply_markup=None
                )
            except Exception as e:
                print(f"清除按钮失败: {e}")
        context.user_data.clear()
        await query.message.edit_text("操作已取消，关键词列表未修改。")


class GroupKeywordAddCallback(BaseCallback):
    meta = CallbackMeta(
        name='group_keyword_add',
        callback_type='group',
        trigger='group_kw_add_',
        enabled=True,
        group_admin_required=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理关键词添加回调
        """
        query = update.callback_query
        await query.answer()
        group_id = int(data)
        keyboard = [[InlineKeyboardButton("取消", callback_data=f"group_kw_cancel_{group_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data['original_message_id'] = query.message.message_id
        await query.message.edit_text("请回复此消息，输入要添加的关键词（用空格分隔）。", reply_markup=reply_markup)
        context.user_data['keyword_action'] = 'add'
        context.user_data['group_id'] = group_id


class GroupKeywordDeleteCallback(BaseCallback):
    meta = CallbackMeta(
        name='group_keyword_delete',
        callback_type='group',
        trigger='group_kw_del_',
        enabled=True,
        group_admin_required=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理关键词删除回调
        """
        query = update.callback_query
        await query.answer()
        group_id = int(data)
        keywords = db.group_keyword_get(group_id)
        if not keywords:
            await query.message.edit_text("当前群组没有关键词可删除。")
            return
        context.user_data['keyword_action'] = 'delete'
        context.user_data['group_id'] = group_id
        context.user_data['to_delete'] = []
        keyboard = []
        row = []
        for kw in keywords:
            row.append(InlineKeyboardButton(kw, callback_data=f"group_kw_select_{kw}_{group_id}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([
            InlineKeyboardButton("提交", callback_data=f"group_kw_submit_del_{group_id}"),
            InlineKeyboardButton("取消", callback_data=f"group_kw_cancel_{group_id}")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("请选择要删除的关键词：", reply_markup=reply_markup)


class GroupKeywordSelectCallback(BaseCallback):
    meta = CallbackMeta(
        name='group_keyword_select',
        callback_type='group',
        trigger='group_kw_select_',
        enabled=True,
        group_admin_required=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理关键词选择回调
        """
        query = update.callback_query
        await query.answer()
        parts = query.data.split('_')
        keyword = parts[0]
        group_id = int(parts[-1])
        if 'to_delete' not in context.user_data:
            context.user_data['to_delete'] = []
        if keyword not in context.user_data['to_delete']:
            context.user_data['to_delete'].append(keyword)
        keywords = db.group_keyword_get(group_id)
        remaining_keywords = [kw for kw in keywords if kw not in context.user_data['to_delete']]
        if not remaining_keywords:
            await query.message.edit_text("已选择所有关键词进行删除。")
            keyboard = [
                [InlineKeyboardButton("提交", callback_data=f"group_kw_submit_del_{group_id}"),
                 InlineKeyboardButton("取消", callback_data=f"group_kw_cancel_{group_id}")]
            ]
        else:
            keyboard = []
            row = []
            for kw in remaining_keywords:
                row.append(InlineKeyboardButton(kw, callback_data=f"group_kw_select_{kw}_{group_id}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([
                InlineKeyboardButton("提交", callback_data=f"group_kw_submit_del_{group_id}"),
                InlineKeyboardButton("取消", callback_data=f"group_kw_cancel_{group_id}")
            ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        selected_text = ", ".join([f"`{kw}`" for kw in context.user_data['to_delete']]) if context.user_data[
            'to_delete'] else "无"
        await query.message.edit_text(f"已选择删除的关键词：{selected_text}\r\n请选择更多要删除的关键词：",
                                      reply_markup=reply_markup, parse_mode='Markdown')


class GroupKeywordSubmitDeleteCallback(BaseCallback):
    meta = CallbackMeta(
        name='group_keyword_submit_delete',
        callback_type='group',
        trigger='group_kw_submit_del_',
        enabled=True,
        group_admin_required=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理关键词提交删除回调
        """
        query = update.callback_query
        await query.answer()
        group_id = int(data)
        if 'to_delete' in context.user_data and context.user_data.get('keyword_action') == 'delete':
            keywords = db.group_keyword_get(group_id)
            new_keywords = [kw for kw in keywords if kw not in context.user_data['to_delete']]
            db.group_keyword_set(group_id, new_keywords)
            await query.message.edit_text(f"已成功删除关键词：{', '.join(context.user_data['to_delete'])}")
        else:
            await query.message.edit_text("删除操作未完成或已取消。")
        context.user_data.clear()


class SettingsCallback(BaseCallback):
    meta = CallbackMeta(
        name='settings',
        callback_type='private',
        trigger='settings_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str = None) -> None:
        """
        处理设置菜单回调。
        """
        query = update.callback_query

        await query.answer()
        if data is None or data == 'main':
            # 主菜单
            keyboard = [
                [InlineKeyboardButton("对话管理", callback_data="settings_dialogue_main")],
                [InlineKeyboardButton("角色管理", callback_data="settings_character_main")],
                [InlineKeyboardButton("预设设置", callback_data="settings_preset_main")],
                [InlineKeyboardButton("状态查询", callback_data="settings_status_main")],
                [InlineKeyboardButton("我的信息", callback_data="settings_myinfo_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("请选择要管理的选项：", reply_markup=reply_markup)
        elif data == 'dialogue_main':
            # 对话管理子菜单
            keyboard = [
                [InlineKeyboardButton("创建新对话", callback_data="settings_dialogue_new")],
                [InlineKeyboardButton("加载对话", callback_data="settings_dialogue_load")],
                [InlineKeyboardButton("删除对话", callback_data="settings_dialogue_delete")],
                [InlineKeyboardButton("返回主菜单", callback_data="settings_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("请选择对话管理操作：", reply_markup=reply_markup)

        elif data == 'character_main':
            # 角色管理子菜单
            keyboard = [
                [InlineKeyboardButton("选择角色", callback_data="settings_character_select")],
                [InlineKeyboardButton("创建角色", callback_data="settings_character_new")],
                [InlineKeyboardButton("删除角色", callback_data="settings_character_delete")],
                [InlineKeyboardButton("返回主菜单", callback_data="settings_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("请选择角色管理操作：", reply_markup=reply_markup)
        elif data == 'preset_main':
            # 预设设置子菜单
            keyboard = [
                [InlineKeyboardButton("选择预设", callback_data="settings_preset_select")],
                [InlineKeyboardButton("返回主菜单", callback_data="settings_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("请选择预设设置操作：", reply_markup=reply_markup)
        elif data == 'status_main':
            # 状态查询
            info = public.update_info_get(update)
            result = f"当前角色：`{info['char']}`\r\n当前接口：`{info['api']}`\r\n当前预设：`{info['preset']}`\r\n流式传输：`{info['stream']}`\r\n"
            keyboard = [[InlineKeyboardButton("返回主菜单", callback_data="settings_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"当前状态：\n{result}", reply_markup=reply_markup, parse_mode='Markdown')
        elif data == 'myinfo_main':
            # 我的信息
            info = public.update_info_get(update)
            result = (
                f"您好，{info['first_name']} {info['last_name']}！\r\n"
                f"您的帐户等级是：`{info['tier']}`；\r\n"
                f"您剩余额度还有`{info['remain']}`条；\r\n"
                f"您的余额是`{info['balance']}`。\r\n"
                f"您的聊天昵称是`{info['user_nick']}`。"
            )
            keyboard = [[InlineKeyboardButton("返回主菜单", callback_data="settings_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"您的信息：\n{result}", reply_markup=reply_markup, parse_mode='Markdown')
        elif data == 'dialogue_new':
            info = public.update_info_get(update)
            conversation = Conversation(info)
            conversation.new('private')
            preset_markup = Inline.print_preset_list()
            char_markup = Inline.print_char_list('load', 'private', info['user_id'])

            if preset_markup == "没有可用的预设。":
                await query.edit_message_text(preset_markup)
            else:
                await query.edit_message_text("请为新对话选择一个预设：", reply_markup=preset_markup)

            if char_markup == "没有可操作的角色。":
                await query.message.reply_text(char_markup)
            else:
                await query.message.reply_text("请为新对话选择一个角色：", reply_markup=char_markup)

        elif data == 'dialogue_load':
            info = public.update_info_get(update)
            markup = Inline.print_conversations(info['user_id'])
            if markup == "没有可用的对话。":
                await query.edit_message_text(markup)
            else:
                await query.edit_message_text("请选择一个对话：", reply_markup=markup)

        elif data == 'dialogue_delete':
            info = public.update_info_get(update)
            markup = Inline.print_conversations(info['user_id'], 'delete')
            if markup == "没有可用的对话。":
                await query.edit_message_text(markup)
            else:
                await query.edit_message_text("请选择一个要删除的对话：", reply_markup=markup)

        elif data == 'character_select':
            info = public.update_info_get(update)
            markup = Inline.print_char_list('load', 'private', info['user_id'])
            if markup == "没有可操作的角色。":
                await query.edit_message_text(markup)
            else:
                await query.edit_message_text("请选择一个角色：", reply_markup=markup)

        elif data == 'character_new':
            info = public.update_info_get(update)
            await context.bot.send_message(info['user_id'], "请使用 /newchar char_name 的格式创建角色")

        elif data == 'character_delete':
            info = public.update_info_get(update)
            markup = Inline.print_char_list('del', 'private', info['user_id'])
            if markup == "没有可操作的角色。":
                await query.edit_message_text(markup)
            else:
                await query.edit_message_text("请选择一个要删除的角色：", reply_markup=markup)
        elif data == 'preset_select':
            markup = Inline.print_preset_list()
            if markup == "没有可用的预设。":
                await query.edit_message_text(markup)
            else:
                await query.edit_message_text("请选择一个预设：", reply_markup=markup)
        else:
            logger.warning(f"未知的设置回调数据: {data}")
            await query.edit_message_text("未知的设置操作。")


class DirectorCallback(BaseCallback):
    meta = CallbackMeta(
        name='director',
        callback_type='private',
        trigger='director_',  # 确保匹配回调数据的前缀
        enabled=True
    )

    def __init__(self):
        self.menu_manager = DirectorMenu()  # 初始化菜单管理器

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str = None) -> None:
        """
        处理导演模式菜单回调，解析回调数据并执行对应逻辑。
        """

        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        if data is None or data == "":
            # 如果没有数据，显示主菜单
            await self._send_menu(context, user_id, self.menu_manager.get_main_menu_id(), query=query)
        else:
            # 解析回调数据
            if data.startswith("nav_"):
                # 跳转到指定菜单
                menu_id = data.replace("nav_", "")
                await self._send_menu(context, user_id, menu_id, query=query)
            elif data.startswith("act_"):
                # 执行功能
                stime = time.time()
                action_data = data.replace("act_", "")
                await self._handle_action(action_data, context, user_id, query,update)
                etime = time.time()
                print(f'执行{data}耗时{etime - stime}秒')
            else:
                logger.warning(f"未知的导演模式回调数据: {data}, user_id: {user_id}")
                await context.bot.send_message(user_id, "未知的操作，请返回主菜单。")
                await self._send_menu(context, user_id, self.menu_manager.get_main_menu_id(), query=query)

    async def _send_menu(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, menu_id: str, query=None):
        """发送指定菜单"""
        menu_meta = self.menu_manager.get_menu_meta(menu_id)
        if not menu_meta:
            logger.warning(f"未知的菜单ID: {menu_id}, user_id: {user_id}")
            await context.bot.send_message(user_id, "菜单未找到，返回主菜单。")
            menu_id = self.menu_manager.get_main_menu_id()
            menu_meta = self.menu_manager.get_menu_meta(menu_id)

        reply_markup = self.menu_manager.get_menu_keyboard(menu_id)
        description_text = self.menu_manager.get_menu_description_text(menu_id)
        try:
            if query:
                await query.edit_message_text(description_text, reply_markup=reply_markup)
            else:
                await context.bot.send_message(user_id, description_text, reply_markup=reply_markup)

        except BadRequest as e:
            logger.warning(f"编辑消息失败: {str(e)}, user_id: {user_id}")
            await context.bot.send_message(user_id, description_text, reply_markup=reply_markup)

    async def _handle_action(self, action_data: str, context: ContextTypes.DEFAULT_TYPE, user_id: int, query,update = None):
        """处理功能按钮的逻辑"""
        # 获取按钮文本（从回调查询的消息中提取按钮文本可能不可靠，因此从菜单数据中查找）
        button_text = "未知按钮"
        info = update_info_get(update)
        conversation = Conversation(info)
        for menu in self.menu_manager.menus.values():
            for btn in menu.buttons:
                if btn.btn_type == "action" and btn.target == action_data:
                    button_text = btn.text
                    break
            if button_text != "未知按钮":
                break

        # 获取长字符串数据
        long_data = self.menu_manager.get_action_data(action_data)
        # 如果有特定逻辑，可以在这里处理
        if action_data == "undo":
            msg_list = db.conversation_latest_message_id_get(info['conv_id'])
            print(msg_list)
            await context.bot.delete_messages(info['user_id'], msg_list)
            db.conversation_delete_messages(info['conv_id'], msg_list[0])
            db.conversation_delete_messages(info['conv_id'], msg_list[1])

        elif action_data == "regen":
            _placeholder_message = await context.bot.send_message(user_id, "执行重新生成操作。")
            try:
                await context.bot.delete_message(info['user_id'], conversation.latest_message_id[0])
            except Exception as e:
                print(f"Failed to delete latest message: {e}")
                #raise e
            async def _regen(placeholder_message):
                try:
                    conversation.set_send_msg_id(placeholder_message.message_id)
                    await conversation.regenerate_response()
                    await placeholder_message.edit_text(conversation.cleared_response_text)
                    conversation.save_to_db('assistant')
                except Exception as e:
                    await placeholder_message.edit_text(f"重新生成失败！{e}")

            _task = asyncio.create_task(_regen(_placeholder_message))
        else:
            _placeholder_message = await context.bot.send_message(user_id, f"正在生成: {action_data}...")
            async def _gen(placeholder_message):
                try:
                    await conversation.set_director_control(long_data,True if not action_data.startswith('camera') else False)
                    await placeholder_message.edit_text(conversation.cleared_response_text)
                    conversation.set_send_msg_id(placeholder_message.message_id)
                    if not action_data.startswith('camera'):
                        conversation.save_to_db('assistant')
                except Exception as e:
                    await placeholder_message.edit_text(f"生成失败！{e}")

            _task = asyncio.create_task(_gen(_placeholder_message))

        # 执行完功能后，返回主菜单
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=query.message.message_id)
        except BadRequest as e:
            logger.warning(f"删除消息失败: {str(e)}, user_id: {user_id} - 可能消息已删除或不可删除。")
        await self._send_menu(context, user_id, self.menu_manager.get_main_menu_id())

class CallbackHandler:
    """
    回调处理类，负责根据回调数据分发给相应的处理器。
    """

    def __init__(self, callback_mapping: Dict[str, BaseCallback]):
        """
        初始化回调处理器。

        Args:
            callback_mapping (Dict[str, BaseCallback]): 回调前缀到处理函数的映射。
        """
        self.callback_mapping = callback_mapping

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理回调查询"""
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = query.from_user.id

        try:
            for prefix, callback in self.callback_mapping.items():
                if data.startswith(prefix):
                    print(f"匹配到回调处理器: {prefix}, data: {data}")  # 添加日志
                    await callback.handle_callback(update, context, data[len(prefix):])
                    return

            logger.warning(f"未知的回调数据: {data}, user_id: {user_id}")
            await query.message.reply_text("未知的回调操作。")

        except Exception as e:
            logger.error(f"处理回调查询失败, user_id: {user_id}, data: {data}, 错误: {str(e)}")
            raise BotError(f"处理回调{data} 失败: {str(e)}")


def create_callback_handler(module_names: list[str]) -> CallbackHandler:
    """
    创建 CallbackHandler 实例并注入依赖。
    """
    callback_mapping: Dict[str, BaseCallback] = {}
    for module_name in module_names:
        try:
            module = importlib.import_module(f'bot_core.callback_handlers.callback')  # 动态导入模块
        except ImportError as e:
            print(f"Error importing module {module_name}: {e}")  # 打印导入错误，方便调试
            continue

        for name, obj in inspect.getmembers(module):  # 扫描模块中的所有成员
            if inspect.isclass(obj) and issubclass(obj, BaseCallback) and obj != BaseCallback:  # 检查是否是BaseCallback的子类
                try:
                    instance = obj()  # 创建回调类实例
                    if hasattr(instance, 'meta') and hasattr(instance.meta, 'trigger'):  # 确保有meta和trigger属性
                        if instance.meta.enabled:  # 确保已激活
                            callback_mapping[instance.meta.trigger] = instance  # 使用预处理过的handler
                            print(f"注册回调处理器: {name}, trigger: {instance.meta.trigger}")  # 添加日志
                    else:
                        print(f"Callback {name} 缺少 meta 或 trigger 属性")
                except Exception as e:
                    print(f"Error creating CallbackHandler for {name}: {e}")  # 打印创建实例或CommandHandler错误，方便调试
                    continue
    return CallbackHandler(callback_mapping)
