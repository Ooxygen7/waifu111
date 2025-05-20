

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot_core.callback_handlers.inline import Inline
from utils import db_utils as db
from .base import BaseCommand, CommandMeta

import logging
from utils.logging_utils import setup_logging
setup_logging()
logger = logging.getLogger(__name__)


class RemakeCommand(BaseCommand):
    meta = CommandMeta(
        name='remake',
        command_type='group',
        trigger='remake',
        menu_text='重开对话 (群组)',
        show_in_menu=True,
        menu_weight=17
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if db.conversation_group_delete(update.message.chat.id, update.message.from_user.id):
            logger.info(f"处理 /remake 命令，用户ID: {update.effective_user.id}")
            await update.message.reply_text("您已重开对话！")


class SwitchCommand(BaseCommand):
    meta = CommandMeta(
        name='switch',
        command_type='group',
        trigger='switch',
        menu_text='切换角色 (群组)',
        show_in_menu=True,
        menu_weight=18,
        group_admin_required=True
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        markup = Inline.print_char_list('load', 'group', update.message.chat.id)
        if markup == "没有可操作的角色。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个角色：", reply_markup=markup)


class RateCommand(BaseCommand):
    meta = CommandMeta(
        name='rate',
        command_type='group',
        trigger='rate',
        menu_text='设置回复频率 (群组)',
        show_in_menu=True,
        menu_weight=19,
        group_admin_required=True
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = context.args if hasattr(context, 'args') else []
        if len(args) < 1:
            await update.message.reply_text("请输入一个0-1的小数")
            return
        rate_value = float(args[0])
        if not 0 <= rate_value <= 1:
            await update.message.reply_text("请输入一个0-1的小数")
            return
        if db.group_info_update(update.message.chat.id, 'rate', rate_value):
            await update.message.reply_text(f"已设置触发频率: {rate_value}")


class KeywordCommand(BaseCommand):
    meta = CommandMeta(
        name='keyword',
        command_type='group',
        trigger='kw',
        menu_text='设置关键词',
        show_in_menu=True,
        menu_weight=0,
        group_admin_required=True
    )

    async def handle(self,update: Update, context: ContextTypes.DEFAULT_TYPE):
        keywords = db.group_keyword_get(update.message.chat.id)
        if not keywords:
            keywords_text = "当前群组没有设置关键词。"
        else:
            keywords_text = "当前群组的关键词列表：\r\n" + ", ".join([f"`{kw}`" for kw in keywords])
        keyboard = [
            [InlineKeyboardButton("添加关键词", callback_data=f"group_kw_add_{update.message.chat.id}"),
             InlineKeyboardButton("删除关键词", callback_data=f"group_kw_del_{update.message.chat.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(keywords_text, reply_markup=reply_markup, parse_mode='Markdown')
