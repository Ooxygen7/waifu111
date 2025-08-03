import sys
import os

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# 模拟 Telegram 对象
# 这些辅助函数可以帮助我们快速创建测试所需的模拟对象

def create_mock_update(message_text, chat_type="private", user_id=123, chat_id=123):
    """创建一个模拟的 Update 对象"""
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = message_text
    update.message.from_user = MagicMock()
    update.message.from_user.id = user_id
    update.message.chat = MagicMock()
    update.message.chat.id = chat_id
    update.message.chat.type = chat_type
    update.message.reply_text = AsyncMock()
    # 为 date 提供一个真实的、带时区的 datetime 对象
    update.message.date = datetime.datetime.now(datetime.timezone.utc)
    return update

def create_mock_context(bot_username="TestBot", user_data=None):
    """创建一个模拟的 Context 对象"""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.username = bot_username
    # 确保 get_chat_administrators 是一个可等待的 AsyncMock
    context.bot.get_chat_administrators = AsyncMock(return_value=[])
    context.args = []
    # 如果需要，可以为每个测试自定义 user_data
    context.user_data = user_data if user_data is not None else {}
    return context

# --- 测试私聊命令 ---
@pytest.mark.asyncio
class TestPrivateCommands:
    """测试私聊命令处理器"""

    @patch('bot_core.command_handlers.private.public.update_info_get')
    async def test_start_command(self, mock_update_info_get):
        """测试 /start 命令"""
        from bot_core.command_handlers.private import StartCommand

        # 准备
        mock_update_info_get.return_value = {'first_name': 'Test', 'last_name': 'User'}
        update = create_mock_update("/start")
        context = create_mock_context()
        
        command = StartCommand()

        # 执行
        await command.handle(update, context)

        # 断言
        update.message.reply_text.assert_called_once()
        call_args, _ = update.message.reply_text.call_args
        assert "您好，Test User！" in call_args[0]

    @patch('bot_core.command_handlers.private.db')
    async def test_me_command(self, mock_db):
        """测试 /me 命令"""
        from bot_core.command_handlers.private import MeCommand

        # 准备
        # 模拟数据库返回的用户信息
        mock_db.user_sign_info_get.return_value = {'frequency': 50}
        
        # 模拟 update_info_get 的返回值
        with patch('bot_core.command_handlers.private.public.update_info_get') as mock_update_info:
            mock_update_info.return_value = {
                'user_id': 123,
                'user_name': 'testuser',
                'tier': 'free',
                'remain': 100,
                'balance': 10.5,
                'user_nick': 'Tester',
                'char': 'test_char',
                'api': 'test_api',
                'preset': 'test_preset',
                'stream': True
            }

            update = create_mock_update("/me", user_id=123)
            context = create_mock_context()
            command = MeCommand()

            # 执行
            await command.handle(update, context)

            # 断言
            update.message.reply_text.assert_called_once()
            call_args, _ = update.message.reply_text.call_args
            reply_text = call_args[0]
            
            assert "您的帐户等级是`free`" in reply_text
            assert "您的额度还有`100`条" in reply_text
            assert "您的临时额度还有`50`条" in reply_text
            assert "当前角色：`test_char`" in reply_text

# --- 可以在这里继续添加其他测试类，例如 TestGroupCommands ---

    async def test_help_command(self):
        """测试 /help 命令"""
        from bot_core.command_handlers.private import HelpCommand

        # 准备
        update = create_mock_update("/help")
        context = create_mock_context()
        command = HelpCommand()

        # 执行
        await command.handle(update, context)

        # 断言
        update.message.reply_text.assert_called_once()
        call_args, call_kwargs = update.message.reply_text.call_args
        assert "CyberWaifu Bot 使用指南" in call_args[0]
        assert call_kwargs['parse_mode'] == "Markdown"

    @patch('bot_core.command_handlers.private.PrivateConv')
    async def test_undo_command(self, MockPrivateConv):
        """测试 /undo 命令"""
        from bot_core.command_handlers.private import UndoCommand

        # 准备
        # 模拟 PrivateConv 实例和其方法
        mock_conversation = AsyncMock()
        mock_conversation.user.id = 123
        mock_conversation.input.id = 456
        MockPrivateConv.return_value = mock_conversation

        update = create_mock_update("/undo", user_id=123)
        context = create_mock_context()
        context.bot.delete_message = AsyncMock()
        
        command = UndoCommand()

        # 执行
        await command.handle(update, context)

        # 断言
        mock_conversation.undo.assert_called_once()
        context.bot.delete_message.assert_called_once_with(123, 456)

    @patch('bot_core.command_handlers.private.db')
    @patch('bot_core.command_handlers.private.public.update_info_get')
    async def test_stream_command(self, mock_update_info_get, mock_db):
        """测试 /stream 命令"""
        from bot_core.command_handlers.private import StreamCommand

        # 准备
        mock_update_info_get.return_value = {'user_id': 123}
        mock_db.user_stream_switch.return_value = True

        update = create_mock_update("/stream", user_id=123)
        context = create_mock_context()
        command = StreamCommand()

        # 执行
        await command.handle(update, context)

        # 断言
        mock_db.user_stream_switch.assert_called_once_with(123)
        update.message.reply_text.assert_called_once_with("切换成功！")


# --- 测试群聊命令 ---
@pytest.mark.asyncio
class TestGroupCommands:
    """测试群聊命令处理器"""

    @patch('bot_core.command_handlers.group.db')
    async def test_keyword_command(self, mock_db):
        """测试 /kw 命令"""
        from bot_core.command_handlers.group import KeywordCommand

        # 准备
        mock_db.group_keyword_get.return_value = ["你好", "再见"]
        update = create_mock_update("/kw", chat_type="group", chat_id=-1001)
        context = create_mock_context()
        command = KeywordCommand()

        # 执行
        await command.handle(update, context)

        # 断言
        update.message.reply_text.assert_called_once()
        call_args, call_kwargs = update.message.reply_text.call_args
        
        # 检查回复文本
        assert "当前群组的关键词列表" in call_args[0]
        assert "`你好`" in call_args[0]
        assert "`再见`" in call_args[0]
        
        # 检查内联键盘
        reply_markup = call_kwargs['reply_markup']
        assert reply_markup is not None
        button_add = reply_markup.inline_keyboard[0][0]
        button_del = reply_markup.inline_keyboard[0][1]
        assert button_add.text == "添加关键词"
        assert button_add.callback_data == "group_kw_add_-1001"
        assert button_del.text == "删除关键词"
        assert button_del.callback_data == "group_kw_del_-1001"

    @patch('bot_core.message_handlers.group.CommandHandlers.get_command_handler')
    async def test_group_msg_handler_correct_at_bot(self, mock_get_handler):
        """测试 group_msg_handler 是否正确处理了 @自己的命令"""
        from bot_core.message_handlers.group import group_msg_handler

        # 准备
        mock_handler = AsyncMock()
        mock_get_handler.return_value = mock_handler
        
        # 模拟 @自己的情况
        update = create_mock_update("/test@TestBot", chat_type="group")
        context = create_mock_context(bot_username="TestBot")
        context.args = [] # 模拟参数解析

        # 执行
        await group_msg_handler(update, context)

        # 断言
        mock_get_handler.assert_called_once_with("test", "group")
        mock_handler.assert_called_once_with(update, context)

    @patch('bot_core.message_handlers.group.CommandHandlers.get_command_handler')
    async def test_group_msg_handler_wrong_at_bot(self, mock_get_handler):
        """测试 group_msg_handler 是否忽略了 @其他人的命令"""
        from bot_core.message_handlers.group import group_msg_handler

        # 准备
        mock_handler = AsyncMock()
        mock_get_handler.return_value = mock_handler

        # 模拟 @别人的情况
        update = create_mock_update("/test@OtherBot", chat_type="group")
        context = create_mock_context(bot_username="TestBot")

        # 执行
        await group_msg_handler(update, context)

        # 断言
        mock_get_handler.assert_not_called()
        mock_handler.assert_not_called()
