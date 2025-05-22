import asyncio
import datetime
import json
import logging
import os
import re
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import bot_core.public_functions.update_parse as public
from bot_core.callback_handlers.inline import Inline
from bot_core.public_functions.conversation import PrivateConv
from utils import db_utils as db, LLM_utils as llm
from utils.logging_utils import setup_logging
from .base import BaseCommand, CommandMeta
from LLM_tools.tools_registry import parse_and_invoke_tool, PrivateToolRegistry
setup_logging()
logger = logging.getLogger(__name__)


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
                summary = await llm.generate_summary(conv_id)
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
        conversation.new()
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
                    generated_content = await llm.generate_char(char_description)
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
            last_sign_time = datetime.datetime.strptime(sign_info.get('last_sign'), '%Y-%m-%d %H:%M:%S.%f')
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


class ToolCommand(BaseCommand):
    meta = CommandMeta(
        name='tool',
        command_type='private',
        trigger='tool',
        menu_text='',
        show_in_menu=False,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /tool command to interact with LLM and invoke tools based on user input.

        Args:
            update: The Telegram Update object containing the user input.
            context: The Telegram ContextTypes object for bot interaction.
        """
        # 获取用户输入（去掉命令部分）
        user_input = update.message.text.strip()
        if len(user_input.split()) > 1:
            user_input = " ".join(user_input.split()[1:])  # 去掉 /tool 命令本身
        else:
            await update.message.reply_text("请在 /tool 命令后提供具体内容，例如：/tool 我想开始使用机器人",
                                            parse_mode="Markdown")
            return
        # 先发送占位消息
        placeholder_message = await update.message.reply_text("处理中...", parse_mode="Markdown")
        logger.debug("已发送占位消息 '处理中...'")
        # 将异步处理逻辑放入后台任务
        context.application.create_task(
            self.process_tool_request(update, context, user_input, placeholder_message),
            update=update
        )
        logger.debug("已创建后台任务处理 /tool 请求")

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
            # 初始化 LLM 客户端
            client = llm.LLM()
            logger.debug("LLM 客户端初始化完成")

            # 构建与 LLM 交互的 messages，包含系统提示和用户输入
            prompt_text = PrivateToolRegistry.get_prompt_text()
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"{prompt_text}\n\n"
                        "你是一个智能助手，根据用户输入判断是否需要调用工具。"
                        "如果需要调用工具，请以 JSON 格式返回工具调用信息；否则，直接用中文回复用户的请求。"
                        "如果用户请求涉及多个步骤，可以返回多个工具调用指令，格式为 {'tool_calls': [...]}。"
                        "工具调用结果会反馈给你，你可以基于结果进行分析或决定下一步操作。"
                    )
                },
                {
                    "role": "user",
                    "content": f"用户输入: {user_input}"
                }
            ]

            final_result = ""
            current_messages = messages.copy()
            max_iterations = 5  # 防止无限循环
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                # 直接设置 messages
                client.set_messages(current_messages)
                logger.debug(f"已设置 messages: {current_messages}")

                # 获取 LLM 响应
                ai_response = await client.final_response()
                logger.info(f"LLM 响应: {ai_response}")

                # 解析 LLM 响应并调用工具
                result, intermediate_results = await parse_and_invoke_tool(ai_response, update, context)
                if intermediate_results:  # 如果有工具调用
                    logger.info(f"工具调用结果: {result}")
                    # 使用 Markdown 代码块包裹工具调用结果
                    formatted_result = f"```\n{result}\n```"
                    final_result += formatted_result + "\n"
                    # 更新占位消息以显示当前进度
                    await placeholder_message.edit_text(f"处理中...\n当前结果:\n{formatted_result}",
                                                        parse_mode="Markdown")

                    # 将工具调用结果反馈给 LLM
                    feedback_content = "工具调用结果:\n" + "\n".join(
                        [f"{res['tool_name']} 执行结果: {res['result']}" for res in intermediate_results]
                    )
                    current_messages.append({
                        "role": "assistant",
                        "content": ai_response
                    })
                    current_messages.append({
                        "role": "user",
                        "content": feedback_content
                    })
                    logger.debug(f"已将工具调用结果反馈给 LLM: {feedback_content}")
                else:
                    logger.info(f"未调用工具，直接回复用户: {result}")
                    final_result += result
                    break  # 没有工具调用，结束循环

            # 编辑占位消息以显示最终结果，使用 Markdown 格式
            await placeholder_message.edit_text(final_result.strip(), parse_mode="Markdown")
            logger.debug("已编辑占位消息，显示最终结果")

        except Exception as e:
            logger.error(f"处理 /tool 命令时发生错误: {str(e)}")
            # 编辑占位消息以显示错误信息，使用 Markdown 格式
            error_message = f"处理请求时发生错误: `{str(e)}`"
            await placeholder_message.edit_text(error_message, parse_mode="Markdown")
            logger.debug("已编辑占位消息，显示错误信息")


