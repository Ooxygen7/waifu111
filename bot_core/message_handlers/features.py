from telegram import Update
from telegram.ext import ContextTypes

from utils import db_utils as db


async def private_newchar(update, newchar_state, user_id):
    """处理创建新角色时的文件和文本输入。

    Args:
        update: Telegram 更新对象。
        newchar_state (dict): 存储新角色创建状态的字典。
        user_id (int): 用户ID。
    """
    if update.message.document:
        file = update.message.document
        if file.mime_type in ['application/json', 'text/plain'] or file.file_name.endswith(('.json', '.txt')):
            file_obj = await file.get_file()
            import os
            save_dir = os.path.join(os.path.dirname(__file__), 'characters')
            os.makedirs(save_dir, exist_ok=True)
            char_name = newchar_state['char_name']
            target_ext = os.path.splitext(file.file_name)[1] if os.path.splitext(file.file_name)[1] else '.txt'
            save_path = os.path.join(save_dir, f"{char_name}_{user_id}{target_ext}")
            await file_obj.download_to_drive(save_path)
            newchar_state['file_saved'] = save_path
            await update.message.reply_text(f"文件已保存为 {save_path}，如需补充文本可继续发送，发送 /done 完成。")
        else:
            await update.message.reply_text("仅支持json或txt文件。")
        return
    # 文本输入
    if update.message.text:
        newchar_state['desc_chunks'].append(update.message.text)
        await update.message.reply_text("文本已接收，可继续发送文本或文件，发送 /done 完成。")
        return

async def group_keyword_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'keyword_action' not in context.user_data or context.user_data['keyword_action'] != 'add':
        return
    group_id = context.user_data.get('group_id')
    original_message_id = context.user_data.get('original_message_id')
    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
        input_text = update.message.text.strip()
        new_keywords = [kw.strip() for kw in input_text.split() if kw.strip()]
        if not new_keywords:
            await update.message.reply_text("未提供有效的关键词。")
            return
        current_keywords = db.group_keyword_get(group_id)
        updated_keywords = list(set(current_keywords + new_keywords))
        db.group_keyword_set(group_id, updated_keywords)
        try:
            await context.bot.delete_message(chat_id=update.message.chat.id, message_id=update.message.message_id)
        except Exception as e:
            print(f"删除用户回复消息失败: {e}")
        try:
            await context.bot.delete_message(chat_id=update.message.chat.id,
                                             message_id=update.message.reply_to_message.message_id)
        except Exception as e:
            print(f"删除提示消息失败: {e}")
        if original_message_id:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=update.message.chat.id,
                    message_id=original_message_id,
                    reply_markup=None
                )
            except Exception as e:
                print(f"清除按钮失败: {e}")
        await context.bot.send_message(
            chat_id=update.message.chat.id,
            text=f"已成功添加关键词：{', '.join(new_keywords)}"
        )
        context.user_data.clear()
    else:
        await update.message.reply_text("请回复 Bot 的消息来添加关键词。")
