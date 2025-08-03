# callback.py
import importlib
import inspect
import logging
import os
import time
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes

import bot_core.public_functions.messages
import bot_core.public_functions.update_parse as public
from bot_core.callback_handlers.base import BaseCallback, CallbackMeta
from bot_core.public_functions.error import BotError
from utils import db_utils as db
from utils.logging_utils import setup_logging
from .director_classes import DirectorMenu
from .inline import Inline
from ..public_functions.conversation import PrivateConv

setup_logging()
logger = logging.getLogger(__name__)

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
            if not info:
                return
            query = update.callback_query
            if not query or not query.message:
                return

            if db.user_config_arg_update(info['user_id'], 'char', character):
                import random
                while True:
                    new_conv_id = random.randint(10000000, 99999999)
                    if db.conversation_private_check(new_conv_id):
                        break
                
                preset = info.get('preset')
                user_id = info.get('user_id')

                if not preset or not user_id:
                    await query.message.edit_text("无法获取用户配置，创建新对话失败。")
                    return

                if db.conversation_private_create(new_conv_id, user_id, character, preset):
                    db.user_config_arg_update(user_id, "conv_id", new_conv_id)
                    await query.message.edit_text(
                        f"角色切换成功！会话已重开！当前角色: {character.split('_')[0]}。")
                else:
                    await query.message.edit_text("创建新对话失败，请联系管理员。")
                    return
                
                from utils import file_utils
                char_file_name_parts = character.split('_')
                actual_char_name = char_file_name_parts[0]
                possible_filenames = [
                    f"{character}.json",
                    f"{actual_char_name}.json"
                ]
                char_data = None
                for fname in possible_filenames:
                    char_data = file_utils.load_char(fname)
                    if char_data:
                        break

                if char_data and 'meeting' in char_data:
                    meeting_message = char_data['meeting']
                    await query.message.reply_text(meeting_message)
                    # 重新获取info以确保conv_id是新的
                    updated_info = public.update_info_get(update)
                    if updated_info and updated_info.get('conv_id'):
                        db.dialog_content_add(updated_info['conv_id'], 'assistant', 1, meeting_message,
                                              meeting_message, query.message.message_id, 'private')
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
        if not info:
            return
        query = update.callback_query
        if not query or not query.message:
            return

        db.user_config_arg_update(info['user_id'], 'char', default_char)
        if info.get('conv_id'):
            db.conversation_private_arg_update(info['conv_id'], 'character', default_char)
        
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
        await query.message.edit_text(
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
            query = update.callback_query
            if not query or not query.message:
                return
            info = public.update_info_get(update)
            if not info or not info.get('user_id'):
                await query.message.edit_text("无法获取用户信息。")
                return

            if db.user_config_arg_update(info['user_id'], 'api', data):
                await query.message.edit_text(f"api切换成功！当前api: {data}。")
            else:
                await query.message.edit_text("API切换失败。")
        except Exception as e:
            logger.error(f"设置api失败, 错误: {str(e)}")
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.edit_text("设置API时发生错误。")


class SetGroupApiCallback(BaseCallback):
    meta = CallbackMeta(
        name='set_group_api',
        callback_type='group',
        trigger='set_group_api_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理群组API设置回调。
        """
        try:
            query = update.callback_query
            if not query or not query.message:
                return

            # 解析回调数据：set_group_api_{api_name}_{group_id}
            parts = data.split('_')
            if len(parts) < 2:
                await query.message.edit_text("回调数据格式错误。")
                return
            
            api_name = parts[0]
            group_id = parts[1] if len(parts) > 1 else None
            
            if not group_id:
                await query.message.edit_text("群组ID缺失。")
                return
            
            # 更新群组配置
            if db.group_config_arg_update(int(group_id), 'api', api_name):
                await query.message.edit_text(f"群组API切换成功！当前API: {api_name}。")
            else:
                await query.message.edit_text("API切换失败，请稍后重试。")
        except Exception as e:
            logger.error(f"设置群组API失败, 错误: {str(e)}")
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.edit_text("设置失败，请稍后重试。")


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
            query = update.callback_query
            if not query or not query.message:
                return
            info = public.update_info_get(update)
            if not info or not info.get('user_id'):
                await query.message.edit_text("无法获取用户信息。")
                return
            
            conv_id = info.get('conv_id')
            if not conv_id:
                await query.message.edit_text("无法找到当前会话。")
                return

            if db.user_config_arg_update(info['user_id'], 'preset', data) and db.conversation_private_arg_update(conv_id, 'preset', data):
                await query.message.edit_text(f"预设切换成功！当前预设: {data}。")
            else:
                await query.message.edit_text("预设切换失败。")
        except Exception as e:
            logger.error(f"设置预设失败, 错误: {str(e)}")
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.edit_text("设置预设时发生错误。")


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
            query = update.callback_query
            if not query or not query.message:
                return
            info = public.update_info_get(update)
            if not info or not info.get('user_id'):
                await query.message.edit_text("无法获取用户信息。")
                return
            
            user_id = info['user_id']
            conv_id = int(data)

            if db.user_config_arg_update(user_id, 'conv_id', conv_id):
                conv_data = db.conversation_private_get(conv_id)
                if conv_data:
                    char, preset = conv_data
                    if db.user_config_arg_update(user_id, 'preset', preset) and db.user_config_arg_update(user_id, 'char', char):
                        await query.message.edit_text(f"加载对话成功！当前对话ID: {conv_id}。")
                    else:
                        await query.message.edit_text("更新用户配置失败。")
                else:
                    await query.message.edit_text("找不到对应的对话记录。")
            else:
                await query.message.edit_text("设置当前对话失败。")
        except Exception as e:
            logger.error(f"设置对话失败, 错误: {str(e)}")
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.edit_text("加载对话时发生错误。")


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
        query = update.callback_query
        if not query or not query.message:
            return

        try:
            conv_id = int(data)
            if db.conversation_private_delete(conv_id):
                await query.message.edit_text(f"删除对话成功！已删除对话: {conv_id}。")
            else:
                await query.message.edit_text("删除对话失败，可能对话不存在。")
        except (ValueError, TypeError) as e:
            logger.error(f"删除对话失败，无效数据: {data}, 错误: {str(e)}")
            await query.message.edit_text("删除对话失败，数据格式错误。")
        except Exception as e:
            logger.error(f"删除对话时发生未知错误, 错误: {str(e)}")
            await query.message.edit_text("删除对话时发生未知错误。")


class DialogShowCallback(BaseCallback):
    meta = CallbackMeta(
        name='dialog_show',
        callback_type='private',
        trigger='dialog_show_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理对话详情显示回调，显示summary并提供加载和删除按钮。
        """
        query = update.callback_query
        assert query is not None
        assert query.message is not None
        assert query.from_user is not None

        try:
            conv_id = int(data)
            conv_info = db.conversation_private_get(conv_id)
            if not conv_info:
                await query.message.edit_text("对话不存在或已被删除。")
                return
            
            conv_list = db.user_conversations_get_for_dialog(query.from_user.id)
            summary = "暂无摘要"
            for conv in conv_list or []:
                if conv[0] == conv_id:
                    summary = conv[4] if conv[4] else "暂无摘要"
                    break
            
            keyboard = [
                [InlineKeyboardButton("加载对话", callback_data=f"dialog_load_{conv_id}")],
                [InlineKeyboardButton("删除对话", callback_data=f"dialog_delete_{conv_id}")],
                [InlineKeyboardButton("返回列表", callback_data="dialog_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                f"对话摘要：\n{summary}",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"显示对话详情失败, 错误: {str(e)}")
            await query.message.edit_text("获取对话详情失败，请稍后重试。")


class DialogLoadCallback(BaseCallback):
    meta = CallbackMeta(
        name='dialog_load',
        callback_type='private',
        trigger='dialog_load_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理对话加载回调。
        """
        query = update.callback_query
        assert query is not None
        assert query.message is not None
        
        try:
            conv_id = int(data)
            info = public.update_info_get(update)
            assert info is not None

            conv_info = db.conversation_private_get(conv_id)
            if not conv_info:
                await query.message.edit_text("对话不存在或已被删除。")
                return
            
            character, preset = conv_info
            user_id = info['user_id']
            
            db.user_config_arg_update(user_id, 'conv_id', conv_id)
            db.user_config_arg_update(user_id, 'char', character)
            db.user_config_arg_update(user_id, 'preset', preset)
            
            await query.message.edit_text(
                f"对话加载成功！\n角色: {character.split('_')[0]}\n预设: {preset}"
            )
        except Exception as e:
            logger.error(f"加载对话失败, 错误: {str(e)}")
            await query.message.edit_text("加载对话失败，请稍后重试。")


class DialogDeleteCallback(BaseCallback):
    meta = CallbackMeta(
        name='dialog_delete',
        callback_type='private',
        trigger='dialog_delete_',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
        """
        处理对话删除回调。
        """
        query = update.callback_query
        assert query is not None
        assert query.message is not None

        try:
            conv_id = int(data)
            if db.conversation_private_delete(conv_id):
                await query.message.edit_text("对话删除成功！")
            else:
                await query.message.edit_text("对话删除失败，请稍后重试。")
        except Exception as e:
            logger.error(f"删除对话失败, 错误: {str(e)}")
            await query.message.edit_text("删除对话失败，请稍后重试。")


class DialogBackCallback(BaseCallback):
    meta = CallbackMeta(
        name='dialog_back',
        callback_type='private',
        trigger='dialog_back',
        enabled=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str = "") -> None:
        """
        处理返回对话列表回调。
        """
        query = update.callback_query
        assert query is not None
        assert query.message is not None

        try:
            from .inline import Inline
            info = public.update_info_get(update)
            assert info is not None
            markup = Inline.print_dialog_conversations(info['user_id'])
            
            if markup == "没有可用的对话。":
                await query.message.edit_text(markup)
            else:
                await query.message.edit_text(
                    "请选择一个对话：",
                    reply_markup=markup
                )
        except Exception as e:
            logger.error(f"返回对话列表失败, 错误: {str(e)}")
            await query.message.edit_text("返回列表失败，请稍后重试。")


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
        query = update.callback_query
        assert query is not None
        assert query.message is not None

        try:
            parts = data.split('_')
            char = f"{parts[0]}_{parts[1]}"
            group_id = int(parts[2])
            db.group_info_update(group_id, 'char', char)
            await query.message.edit_text(f"切换角色成功！当前角色: {char.split('_')[0]}。")
        except Exception as e:
            logger.error(f"设置群组角色失败, 错误: {str(e)}")
            await query.message.edit_text("设置群组角色失败。")


class GroupKeywordCancelCallback(BaseCallback):
    meta = CallbackMeta(
        name='group_keyword_cancel',
        callback_type='group',
        trigger='group_kw_cancel_',
        enabled=True,
        group_admin_required=True
    )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str = "") -> None:
        """
        处理关键词取消回调
        """
        query = update.callback_query
        assert query is not None
        assert query.message is not None
        
        await query.answer()
        original_message_id = context.user_data.get('original_message_id')
        if original_message_id:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=query.message.chat.id,
                    message_id=original_message_id,
                    reply_markup=None
                )
            except Exception as e:
                logger.warning(f"清除按钮失败: {e}")
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
        assert query is not None
        assert query.message is not None

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
        assert query is not None
        assert query.message is not None

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
        assert query is not None
        assert query.message is not None

        await query.answer()
        parts = data.rsplit('_', 1)
        keyword = parts[0]
        group_id = int(parts[1])
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
        selected_text = ", ".join([f"`{kw}`" for kw in context.user_data['to_delete']]) if context.user_data.get('to_delete') else "无"
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
        assert query is not None
        assert query.message is not None

        await query.answer()
        group_id = int(data)
        to_delete_list = context.user_data.get('to_delete', [])
        if to_delete_list and context.user_data.get('keyword_action') == 'delete':
            keywords = db.group_keyword_get(group_id)
            new_keywords = [kw for kw in keywords if kw not in to_delete_list]
            db.group_keyword_set(group_id, new_keywords)
            await query.message.edit_text(f"已成功删除关键词：{', '.join(to_delete_list)}")
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

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str = "") -> None:
        """
        处理设置菜单回调。
        """
        query = update.callback_query
        assert query is not None
        assert query.message is not None

        await query.answer()
        
        # 确保data不为None
        data = data or 'main'

        info = public.update_info_get(update)
        # 某些操作不需要info，所以只在使用前检查
        
        try:
            if data == 'main':
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
                keyboard = [
                    [InlineKeyboardButton("创建新对话", callback_data="settings_dialogue_new")],
                    [InlineKeyboardButton("加载对话", callback_data="settings_dialogue_load")],
                    [InlineKeyboardButton("删除对话", callback_data="settings_dialogue_delete")],
                    [InlineKeyboardButton("返回主菜单", callback_data="settings_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("请选择对话管理操作：", reply_markup=reply_markup)

            elif data == 'character_main':
                keyboard = [
                    [InlineKeyboardButton("选择角色", callback_data="settings_character_select")],
                    [InlineKeyboardButton("创建角色", callback_data="settings_character_new")],
                    [InlineKeyboardButton("删除角色", callback_data="settings_character_delete")],
                    [InlineKeyboardButton("返回主菜单", callback_data="settings_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("请选择角色管理操作：", reply_markup=reply_markup)

            elif data == 'preset_main':
                keyboard = [
                    [InlineKeyboardButton("选择预设", callback_data="settings_preset_select")],
                    [InlineKeyboardButton("返回主菜单", callback_data="settings_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("请选择预设设置操作：", reply_markup=reply_markup)

            elif data in ['status_main', 'myinfo_main', 'dialogue_new', 'dialogue_load', 'dialogue_delete', 'character_select', 'character_new', 'character_delete']:
                assert info is not None, "此操作需要用户信息。"
                user_id = info['user_id']

                if data == 'status_main':
                    result = f"当前角色：`{info.get('char', 'N/A')}`\r\n当前接口：`{info.get('api', 'N/A')}`\r\n当前预设：`{info.get('preset', 'N/A')}`\r\n流式传输：`{info.get('stream', 'N/A')}`\r\n"
                    keyboard = [[InlineKeyboardButton("返回主菜单", callback_data="settings_main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"当前状态：\n{result}", reply_markup=reply_markup, parse_mode='Markdown')
                
                elif data == 'myinfo_main':
                    result = (
                        f"您好，{info.get('first_name', '')} {info.get('last_name', '')}！\r\n"
                        f"您的帐户等级是：`{info.get('tier', 'N/A')}`；\r\n"
                        f"您剩余额度还有`{info.get('remain', 'N/A')}`条；\r\n"
                        f"您的余额是`{info.get('balance', 'N/A')}`。\r\n"
                        f"您的聊天昵称是`{info.get('user_nick', 'N/A')}`。"
                    )
                    keyboard = [[InlineKeyboardButton("返回主菜单", callback_data="settings_main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"您的信息：\n{result}", reply_markup=reply_markup, parse_mode='Markdown')

                elif data == 'dialogue_new':
                    import random
                    while True:
                        new_conv_id = random.randint(10000000, 99999999)
                        if db.conversation_private_check(new_conv_id):
                            break
                    
                    character = info.get('char')
                    preset = info.get('preset')

                    if not character or not preset:
                        await query.edit_message_text("无法获取角色或预设，创建新对话失败。")
                        return

                    if db.conversation_private_create(new_conv_id, user_id, character, preset):
                        db.user_config_arg_update(user_id, "conv_id", new_conv_id)
                        await query.edit_message_text("创建成功！")
                    else:
                        await query.edit_message_text("创建新对话失败，请联系管理员。")
                
                elif data == 'dialogue_load':
                    markup = Inline.print_conversations(user_id)
                    await query.edit_message_text("请选择一个对话：", reply_markup=markup) if not isinstance(markup, str) else await query.edit_message_text(markup)

                elif data == 'dialogue_delete':
                    markup = Inline.print_conversations(user_id, 'delete')
                    await query.edit_message_text("请选择一个要删除的对话：", reply_markup=markup) if not isinstance(markup, str) else await query.edit_message_text(markup)

                elif data == 'character_select':
                    markup = Inline.print_char_list('load', 'private', user_id)
                    await query.edit_message_text("请选择一个角色：", reply_markup=markup) if not isinstance(markup, str) else await query.edit_message_text(markup)

                elif data == 'character_new':
                    await bot_core.public_functions.messages.send_message(context, user_id, "请使用 /newchar char_name 的格式创建角色")

                elif data == 'character_delete':
                    markup = Inline.print_char_list('del', 'private', user_id)
                    await query.edit_message_text("请选择一个要删除的角色：", reply_markup=markup) if not isinstance(markup, str) else await query.edit_message_text(markup)

            elif data == 'preset_select':
                markup = Inline.print_preset_list()
                await query.edit_message_text("请选择一个预设：", reply_markup=markup) if not isinstance(markup, str) else await query.edit_message_text(markup)

            else:
                logger.warning(f"未知的设置回调数据: {data}")
                await query.edit_message_text("未知的设置操作。")
        except Exception as e:
            logger.error(f"处理设置回调失败, data: {data}, 错误: {str(e)}")
            await query.message.edit_text("处理设置时发生错误。")


class DirectorCallback(BaseCallback):
    meta = CallbackMeta(
        name='director',
        callback_type='private',
        trigger='director_',  # 确保匹配回调数据的前缀
        enabled=True
    )

    def __init__(self):
        super().__init__()
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
                await self._handle_action(action_data, context, user_id, query, update)
                etime = time.time()
                print(f'执行{data}耗时{etime - stime}秒')
            else:
                logger.warning(f"未知的导演模式回调数据: {data}, user_id: {user_id}")
                await bot_core.public_functions.messages.send_message(context, user_id, "未知的操作，请返回主菜单。")
                await self._send_menu(context, user_id, self.menu_manager.get_main_menu_id(), query=query)

    async def _send_menu(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, menu_id: str, query=None):
        """发送指定菜单"""
        menu_meta = self.menu_manager.get_menu_meta(menu_id)
        if not menu_meta:
            logger.warning(f"未知的菜单ID: {menu_id}, user_id: {user_id}")
            await bot_core.public_functions.messages.send_message(context, user_id, "菜单未找到，返回主菜单。")
            menu_id = self.menu_manager.get_main_menu_id()
            # menu_meta = self.menu_manager.get_menu_meta(menu_id)

        reply_markup = self.menu_manager.get_menu_keyboard(menu_id)
        description_text = self.menu_manager.get_menu_description_text(menu_id)
        try:
            if query:
                await query.edit_message_text(description_text, reply_markup=reply_markup)
            else:
                await context.bot.send_message(chat_id=user_id, text=description_text, reply_markup=reply_markup, parse_mode="markdown")

        except BadRequest as e:
            logger.warning(f"编辑消息失败: {str(e)}, user_id: {user_id}")
            await context.bot.send_message(chat_id=user_id, text=description_text, reply_markup=reply_markup, parse_mode="markdown")

    async def _handle_action(self, action_data: str, context: ContextTypes.DEFAULT_TYPE, user_id: int, query,
                             update=None):
        """处理功能按钮的逻辑"""
        # 获取按钮文本（从回调查询的消息中提取按钮文本可能不可靠，因此从菜单数据中查找）
        button_text = "未知按钮"
        conversation = PrivateConv(update, context)
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
            await conversation.undo()

        elif action_data == "regen":
            await conversation.regen()
        elif action_data.startswith('camera'):
            conversation.set_callback_data(long_data)
            await conversation.response(False)
        else:
            conversation.set_callback_data(long_data)
            await conversation.response()

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
                    logger.debug(f"匹配到回调处理器: {prefix}, data: {data}")  # 添加日志
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
            logger.warning(f"Error importing module {module_name}: {e}")  # 打印导入错误，方便调试
            continue

        for name, obj in inspect.getmembers(module):  # 扫描模块中的所有成员
            if inspect.isclass(obj) and issubclass(obj, BaseCallback) and obj != BaseCallback:  # 检查是否是BaseCallback的子类
                try:
                    instance = obj()  # 创建回调类实例
                    if hasattr(instance, 'meta') and hasattr(instance.meta, 'trigger'):  # 确保有meta和trigger属性
                        if instance.meta.enabled:  # 确保已激活
                            callback_mapping[instance.meta.trigger] = instance  # 使用预处理过的handler
                            logger.debug(f"注册回调处理器: {name}, trigger: {instance.meta.trigger}")  # 添加日志
                    else:
                        print(f"Callback {name} 缺少 meta 或 trigger 属性")
                except Exception as e:
                    logger.debug(f"Error creating CallbackHandler for {name}: {e}")  # 打印创建实例或CommandHandler错误，方便调试
                    continue
    return CallbackHandler(callback_mapping)
