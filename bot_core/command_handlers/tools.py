"""
toolsprivate.py - Private command tools for LLM interaction.

This module provides a set of tools that can be invoked by an LLM to interact with
the CyberWaifu bot system. Each tool corresponds to a private command that can be
executed in a user's private chat context.
"""

import datetime
import os
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

import bot_core.public_functions.update_parse as public
from bot_core.callback_handlers.inline import Inline
from bot_core.public_functions.conversation import PrivateConv
from utils import db_utils as db
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class PrivateTools:
    """A collection of tools for private commands that can be invoked by an LLM."""

    @staticmethod
    async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Toggle streaming mode for message delivery.

        Description: Switches between streaming and non-streaming mode for message delivery.
        Type: Operation
        Parameters: None
        Return Value: A string indicating whether streaming mode was toggled successfully.
        Invocation: {"tool_name": "stream", "parameters": {}}
        """
        info = public.update_info_get(update)
        if db.user_stream_switch(info['user_id']):
            await update.message.reply_text("切换成功！")
            return "Streaming mode toggled successfully."
        return "Failed to toggle streaming mode."

    @staticmethod
    async def me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Display the user's personal information, including account tier, quota, and balance.

        Description: Retrieves and returns user-specific information for analysis or display.
        Type: Query
        Parameters: None
        Return Value: A string containing user information.
        Invocation: {"tool_name": "me", "parameters": {}}
        """
        info = public.update_info_get(update)
        result = (
            f"用户名: {info['user_name']}, "
            f"账户等级: {info['tier']}, "
            f"剩余额度: {info['remain']}, "
            f"临时额度: {db.user_sign_info_get(info['user_id']).get('frequency')}, "
            f"余额: {info['balance']}, "
            f"对话昵称: {info['user_nick']}"
        )
        return result

    @staticmethod
    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Display the current settings, including character, API, preset, and streaming status.

        Description: Retrieves and returns the current configuration settings of the conversation.
        Type: Query
        Parameters: None
        Return Value: A string containing current settings.
        Invocation: {"tool_name": "status", "parameters": {}}
        """
        info = public.update_info_get(update)
        result = (
            f"当前角色: {info['char']}, "
            f"当前接口: {info['api']}, "
            f"当前预设: {info['preset']}, "
            f"流式传输: {info['stream']}"
        )
        return result

    @staticmethod
    async def newchar(update: Update, context: ContextTypes.DEFAULT_TYPE, char_name: Optional[str] = None) -> str:
        """
        Start the creation of a new character with a specified name.

        Description: Initiates the process of creating a new character with the provided name.
        Type: Operation
        Parameters:
            - char_name (string): The name of the new character to be created.
        Return Value: A string confirming the start of new character creation with the specified name.
        Invocation: {"tool_name": "newchar", "parameters": {"char_name": "Alice"}}
        """
        info = public.update_info_get(update)
        args = context.args if hasattr(context, 'args') else []
        if not char_name and (not args or len(args[0].strip()) == 0):
            await update.message.reply_text("请使用 /newchar char_name 的格式指定角色名。")
            return "Character name required."
        char_name = char_name or args[0].strip()
        if not hasattr(context.bot_data, 'newchar_state'):
            context.bot_data['newchar_state'] = {}
        context.bot_data['newchar_state'][info['user_id']] = {'char_name': char_name, 'desc_chunks': []}
        await update.message.reply_text(
            f"请上传角色描述文件（json/txt）或直接发送文本描述，完成后发送 /done 结束输入。\n如描述较长可分多条消息发送。")
        return f"New character creation started for {char_name}."

    @staticmethod
    async def nick(update: Update, context: ContextTypes.DEFAULT_TYPE, nickname: Optional[str] = None) -> str:
        """
        Set a nickname for the user in conversations.

        Description: Updates the user's nickname for use in conversations.
        Type: Operation
        Parameters:
            - nickname (string): The nickname to set for the user.
        Return Value: A string confirming the nickname update or indicating failure.
        Invocation: {"tool_name": "nick", "parameters": {"nickname": "CrispShark"}}
        """
        info = public.update_info_get(update)
        args = context.args if hasattr(context, 'args') else []
        if not nickname and (not args or len(args[0].strip()) == 0):
            await update.message.reply_text("请使用 /nick nickname 的格式指定昵称。如：/nick 脆脆鲨")
            return "Nickname required."
        nick_name = nickname or args[0].strip()
        if db.user_config_arg_update(info['user_id'], 'nick', nick_name):
            # await update.message.reply_text(f"昵称已更新为：{nick_name}")
            return f"Nickname updated to {nick_name}."
        else:
            # await update.message.reply_text(f"昵称更新失败")
            return "Failed to update nickname."

    @staticmethod
    async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Prompt the user to delete a saved conversation.

        Description: Displays a list of saved conversations for the user to delete.
        Type: Operation
        Parameters: None
        Return Value: A string confirming that conversation deletion selection has been prompted.
        Invocation: {"tool_name": "delete", "parameters": {}}
        """
        info = public.update_info_get(update)
        markup = Inline.print_conversations(info['user_id'], 'delete')
        if markup == "没有可用的对话。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个对话：", reply_markup=markup)
        await update.message.delete()
        return "Conversation deletion selection prompted."

    @staticmethod
    async def sign(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Perform a daily check-in to gain temporary quota (limited to once every 8 hours).

        Description: Allows the user to check in daily to increase temporary quota.
        Type: Operation
        Parameters: None
        Return Value: A string indicating the result of the check-in (success or time restriction).
        Invocation: {"tool_name": "sign", "parameters": {}}
        """
        user_id = update.message.from_user.id
        sign_info = db.user_sign_info_get(user_id)
        if sign_info.get('last_sign') == 0:
            db.user_sign_info_create(user_id)
            sign_info = db.user_sign_info_get(user_id)
            # await update.message.reply_text(
            # f"签到成功！临时额度+50！\r\n你的临时额度为: {sign_info.get('frequency')}条(上限100)")
            return "Check-in successful, temporary quota increased by 50."
        else:
            concurrent_time = datetime.datetime.now()
            last_sign_time = datetime.datetime.strptime(sign_info.get('last_sign'), '%Y-%m-%d %H:%M:%S.%f')
            time_delta = concurrent_time - last_sign_time
            total_seconds = time_delta.total_seconds()
            if total_seconds < 28800:  # 8 hours = 28800 seconds
                remaining_hours = (28800 - total_seconds) // 3600
                # await update.message.reply_text(
                # f"您8小时内已完成过签到，您可以在{str(remaining_hours)}小时后再次签到。")
                return f"Check-in already done within 8 hours, retry after {remaining_hours} hours."
            else:
                db.user_sign(user_id)
                sign_info = db.user_sign_info_get(user_id)
                # await update.message.reply_text(
                # f"签到成功！临时额度+50！\r\n你的临时额度为: {sign_info.get('frequency')}条(上限100)")
                return "Check-in successful, temporary quota increased by 50."

    @staticmethod
    async def conv_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        info = public.update_info_get(update)



# Tool mapping for LLM invocation
TOOLS_MAPPING = {
    "stream": PrivateTools.stream,
    "me": PrivateTools.me,
    "status": PrivateTools.status,
    "newchar": PrivateTools.newchar,
    "nick": PrivateTools.nick,
    "load": PrivateTools.load,
    "delete": PrivateTools.delete,
    "sign": PrivateTools.sign,
}
