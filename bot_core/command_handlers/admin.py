from telegram import Update
from telegram.ext import ContextTypes

from utils import db_utils as db
from .base import BaseCommand, CommandMeta


class AddFrequencyCommand(BaseCommand):
    meta = CommandMeta(
        name='add_frequency',
        command_type='admin',
        trigger='addf',
        menu_text='增加用户额度',
        show_in_menu=False,
        menu_weight=20,
        bot_admin_required=True
    )
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = context.args if hasattr(context, 'args') else []
        if len(args) < 2:
            await update.message.reply_text("请以 /addf target_user_id value 的格式输入参数。")
            return
        target_user = args[0]
        value = int(args[1])
        if target_user == 'all':
            if db.user_frequency_free(value):
                await update.message.reply_text(f"已为所有用户添加{value}条额度")
        else:
            if db.user_info_update(target_user, 'remain_frequency', value, True):
                if not target_user.startswith('@'):
                    await update.message.reply_text(f"已为{str(db.user_info_get(target_user)['user_name'])}添加{value}条额度")
                else:
                    await update.message.reply_text(f"已为{target_user}添加{value}条额度")

class SetTierCommand(BaseCommand):
    meta = CommandMeta(
        name='set_tier',
        command_type='admin',
        trigger='sett',
        menu_text='修改用户账户等级',
        show_in_menu=False,
        menu_weight=20,
        bot_admin_required=True,
    )
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = context.args if hasattr(context, 'args') else []
        if len(args) < 2:
            await update.message.reply_text("请以 /sett target_user_id value 的格式输入参数。")
            return
        target_user_id = args[0]
        value = int(args[1])

        if db.user_info_update(target_user_id, 'account_tier', value, False):
            await update.message.reply_text(
                f"{str(db.user_info_get(target_user_id)['user_name'])}账户等级现在是{value}")