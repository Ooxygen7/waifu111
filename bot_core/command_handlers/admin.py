from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
import logging
import os
import sys
from agent.llm_functions import run_agent_session
import bot_core.services.messages as messages
from agent.tools_registry import DatabaseSuperToolRegistry
from bot_core.data_repository import UsersRepository
from utils.config_utils import get_config
from utils.db_utils import manual_wal_checkpoint, close_all_connections
from bot_core.command_handlers.base import BaseCommand, CommandMeta
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


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
        args = context.args or []
        if not update.message:
            return
        if len(args) < 2:
            await update.message.reply_text("请以 /addf target_user_id value 的格式输入参数。")
            return

        try:
            target_user = args[0]
            value = int(args[1])
        except ValueError:
            await update.message.reply_text("参数格式错误，请确保额度值为有效数字。")
            return

        if target_user == 'all':
            result = UsersRepository.user_frequency_free(value)
            if result["success"]:
                await update.message.reply_text(f"已为所有用户添加{value}条额度")
            else:
                await update.message.reply_text("操作失败：无法为所有用户添加额度，请检查数据库连接。")
        else:
            result = UsersRepository.user_info_update(target_user, 'remain_frequency', value, True)
            if result["success"]:
                if not target_user.startswith('@'):
                    user_info_result = UsersRepository.user_info_get(int(target_user))
                    if user_info_result["success"] and user_info_result["data"]:
                        user_info = user_info_result["data"]
                        await update.message.reply_text(
                            f"已为{str(user_info['user_name'])}添加{value}条额度")
                    else:
                        await update.message.reply_text(f"已为用户ID {target_user}添加{value}条额度")
                else:
                    await update.message.reply_text(f"已为{target_user}添加{value}条额度")
            else:
                await update.message.reply_text(
                    f"操作失败：无法为用户 {target_user} 添加额度。可能原因：\n1. 用户不存在\n2. 数据库连接失败\n3. 参数格式错误")


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
        args = context.args or []
        if not update.message:
            return
        if len(args) < 2:
            await update.message.reply_text("请以 /sett target_user_id value 的格式输入参数。")
            return
        target_user_id = int(args[0])
        value = int(args[1])

        UsersRepository.user_info_update(target_user_id, 'account_tier', value, False)
        user_info_result = UsersRepository.user_info_get(target_user_id)
        if user_info_result["success"] and user_info_result["data"]:
            user_info = user_info_result["data"]
            await update.message.reply_text(
                f"{str(user_info['user_name'])}账户等级现在是{str(user_info['tier'])}")
        else:
            await update.message.reply_text("用户信息获取失败")


class DatabaseCommand(BaseCommand):
    meta = CommandMeta(
        name='database',
        command_type='admin',
        trigger='q',
        menu_text='',
        bot_admin_required=True,
        show_in_menu=False,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /q command to interact with LLM and invoke database analysis tools based on user input.
        """
        if not update.message:
            return

        # The 'q' command is defined in the meta, so we only need to handle the arguments.
        if not context.args:
            await update.message.reply_text(
                "请在 `/q` 命令后提供具体内容，例如：`/q 查看用户123的详情`",
                parse_mode="Markdown")
            return
        
        user_input = " ".join(context.args)

        # 将异步处理逻辑放入后台任务
        context.application.create_task(
            self.process_database_request(update, context, user_input),
            update=update
        )
        logger.debug("已创建后台任务处理 /database 请求")

    async def process_database_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str) -> None:
        """
        Process the database request in the background by creating and handling an agent session.
        """
        character_prompt = """你是一个专业的数据库管理助手，可以帮助用户查询和管理数据库。
                        你可以使用提供的工具来执行数据库操作，包括查询用户信息、会话记录、消息历史等。
                        请根据用户的需求，选择合适的工具来完成任务。
                        关于用户、群组信息、对话记录的关键字查询，尽量使用模糊匹配（如 LIKE '%keyword%'）
                        """
        prompt_text = DatabaseSuperToolRegistry.get_prompt_text()

        # 1. 创建 Agent 会话生成器
        q_command_api = get_config('q_command_api', 'gemini-2.5')
        # 生成会话ID（基于用户ID和时间戳）
        session_id = f"q_cmd_{update.effective_user.id}_{int(update.message.date.timestamp())}"
        
        agent_session = run_agent_session(
            user_input=user_input,
            prompt_text=prompt_text,
            character_prompt=character_prompt,
            llm_api=q_command_api,
            max_iterations=15,
            enable_memory=True,
            session_id=session_id
        )

        # 2. 将会话处理委托给消息函数
        await messages.handle_agent_session(
            update=update,
            agent_session=agent_session,
            character_name="cyberwaifu"
        )

class ForwardCommand(BaseCommand):
    meta = CommandMeta(
        name='forward',
        command_type='admin',
        trigger='fw',
        menu_text='转发消息',
        show_in_menu=False,
        menu_weight=20,
        bot_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理 /forward 或 /fw 命令，将指定消息转发到当前聊天。
        命令格式: /forward <源聊天ID> <消息ID>
        """
        # context.args 会自动解析命令后的参数列表
        # 例如，如果用户输入 "/fw -1001234567890 123"
        # context.args 将是 ['-1001234567890', '123']
        args = context.args
        # 1. 参数校验
        if not update.message:
            return
        if not args or len(args) != 2:
            await update.message.reply_text(
                "❌ 用法错误！请提供源聊天ID和消息ID。\n"
                "或简写：`/fw <源聊天ID> <消息ID>`\n\n"
                "💡 源聊天ID可以是用户ID、群组ID或频道ID（需要有访问权限）。\n"
                "注意：频道ID通常以 `-100` 开头。",
                parse_mode='Markdown'
            )
            return
        try:
            # 尝试将参数转换为整数
            source_chat_id = int(args[0])
            message_id = int(args[1])
        except ValueError:
            await update.message.reply_text(
                "❌ 无效的ID！源聊天ID和消息ID都必须是有效的数字。\n"
                "示例：`/forward -1001234567890 123`",
                parse_mode='Markdown'
            )
            return
        # 2. 获取目标聊天ID (通常是用户发起命令的聊天)
        if not update.effective_chat:
            return
        target_chat_id = update.effective_chat.id
        # 3. 执行消息转发操作
        try:
            await context.bot.forward_message(
                chat_id=target_chat_id,
                from_chat_id=source_chat_id,
                message_id=message_id
            )
            # await update.message.reply_text("✅ 消息已成功转发！")

        except Exception as e:
            # 捕获其他非 Telegram API 的意外错误
            await update.message.reply_text(
                f"❌ 发生错误：`{type(e).__name__}: {e}`",
                parse_mode='Markdown'
            )


class MessageCommand(BaseCommand):
    meta = CommandMeta(
        name='message',
        command_type='admin',
        trigger='msg',
        menu_text='向指定用户发送消息',
        show_in_menu=False,
        menu_weight=20,
        bot_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理 /msg 命令，向指定用户发送消息。
        命令格式: /msg <用户ID> <消息内容>
        """
        args = context.args
        if not update.message:
            return
        # 1. 参数校验
        if not args or len(args) < 2:
            await update.message.reply_text(
                "❌ 用法错误！请提供用户ID和消息内容。\n"
                "格式：`/msg <用户ID> <消息内容>`\n\n"
                "💡 用户ID必须是有效的数字。\n"
                "示例：`/msg 123456789 您好，这是一条通知消息。`",
                parse_mode='Markdown'
            )
            return

        try:
            # 尝试将第一个参数转换为整数（用户ID）
            target_user_id = int(args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ 无效的用户ID！用户ID必须是有效的数字。\n"
                "示例：`/msg 123456789 您好，这是一条通知消息。`",
                parse_mode='Markdown'
            )
            return

        # 2. 获取消息内容（从第二个参数开始的所有内容）
        message_content = ' '.join(args[1:])

        if not message_content.strip():
            await update.message.reply_text(
                "❌ 消息内容不能为空！\n"
                "请提供要发送的消息内容。",
                parse_mode='Markdown'
            )
            return

        # 3. 执行消息发送操作
        try:
            await messages.send_message(context, target_user_id, message_content)

            # 发送成功确认消息
            await update.message.reply_text(
                f"✅ 消息已成功发送给用户 {target_user_id}！\n\n"
                f"📝 发送内容：{message_content}",
                parse_mode='Markdown'
            )
            if update.effective_user:
            # 记录日志
                logger.info(f"管理员 {update.effective_user.id} 向用户 {target_user_id} 发送消息: {message_content}")

        except TelegramError as e:
            # 处理 Telegram API 相关错误
            error_msg = "❌ 发送消息失败！\n\n"

            if "chat not found" in str(e).lower():
                error_msg += "原因：找不到指定的用户或聊天。\n" \
                             "请确认用户ID是否正确，或用户是否已与机器人建立过对话。"
            elif "blocked" in str(e).lower():
                error_msg += "原因：用户已阻止机器人。\n" \
                             "无法向已阻止机器人的用户发送消息。"
            elif "forbidden" in str(e).lower():
                error_msg += "原因：没有权限向该用户发送消息。\n" \
                             "可能用户未启动与机器人的对话。"
            else:
                error_msg += f"原因：{str(e)}"

            await update.message.reply_text(error_msg, parse_mode='Markdown')
            logger.warning(f"向用户 {target_user_id} 发送消息失败: {str(e)}")

        except Exception as e:
            # 捕获其他意外错误
            await update.message.reply_text(
                f"❌ 发生未知错误：`{type(e).__name__}: {e}`",
                parse_mode='Markdown'
            )
            logger.error(f"发送消息时发生未知错误: {str(e)}", exc_info=True)


class CheckpointCommand(BaseCommand):
    meta = CommandMeta(
        name='checkpoint',
        command_type='admin',
        trigger='chkpt',
        menu_text='触发数据库检查点',
        show_in_menu=False,
        menu_weight=50,
        bot_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理 /checkpoint 命令，手动触发数据库 WAL 检查点。
        """
        if not update.message or  not update.effective_user:
            return
        await update.message.reply_text("正在尝试手动触发数据库 WAL 检查点...")
        
        try:
            success = manual_wal_checkpoint()
            if success:
                await update.message.reply_text("✅ 成功触发 WAL 检查点！WAL 文件已合并到主数据库并重置。")
                logger.info(f"管理员 {update.effective_user.id} 成功触发了 WAL 检查点。")
            else:
                await update.message.reply_text("❌ 触发 WAL 检查点失败，请查看机器人后台日志获取详细信息。")
                logger.error(f"管理员 {update.effective_user.id} 触发 WAL 检查点失败。")
        except Exception as e:
            await update.message.reply_text(f"❌ 执行检查点时发生意外错误：\n`{type(e).__name__}: {e}`", parse_mode='Markdown')
            logger.error(f"执行 WAL 检查点时发生意外错误: {e}", exc_info=True)


class RestartCommand(BaseCommand):
    meta = CommandMeta(
        name='restart',
        command_type='admin',
        trigger='restart',
        menu_text='重启机器人',
        show_in_menu=False,
        menu_weight=100,
        bot_admin_required=True,
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        处理 /restart 命令，安全地重启整个机器人应用。
        """
        if not update.message or not update.effective_user:
            return
        await update.message.reply_text("正在准备重启机器人...")
        logger.info(f"管理员 {update.effective_user.id} 触发了机器人重启。")

        try:
            # 1. 关闭数据库连接
            logger.info("正在关闭数据库连接...")
            close_all_connections()
            await update.message.reply_text("数据库连接已关闭。")

            # 2. 执行重启
            logger.info("正在执行重启...")
            await update.message.reply_text("机器人正在重启...请稍候。")

            # os.execv 会用新进程替换当前进程
            os.execv(sys.executable, ['python'] + sys.argv)

        except Exception as e:
            error_message = f"❌ 重启过程中发生错误：\n`{type(e).__name__}: {e}`"
            await update.message.reply_text(error_message, parse_mode='Markdown')
            logger.error(f"重启机器人时发生意外错误: {e}", exc_info=True)
