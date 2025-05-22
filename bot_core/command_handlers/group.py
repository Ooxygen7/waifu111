import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot_core.callback_handlers.inline import Inline
from utils import db_utils as db,LLM_utils as llm
from utils.logging_utils import setup_logging
from .base import BaseCommand, CommandMeta
from .tools_registry import parse_and_invoke_tool,MarketToolRegistry
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

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

class CryptoCommand(BaseCommand):
    meta = CommandMeta(
        name='crypto',
        command_type='private',
        trigger='cc',
        menu_text='',
        show_in_menu=False,
        menu_weight=99
    )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /cc command to interact with LLM and invoke tools based on user input.

        Args:
            update: The Telegram Update object containing the user input.
            context: The Telegram ContextTypes object for bot interaction.
        """
        # 获取用户输入（去掉命令部分）
        user_input = update.message.text.strip()
        if len(user_input.split()) > 1:
            user_input = " ".join(user_input.split()[1:])  # 去掉 /tool 命令本身
        else:
            await update.message.reply_text("请在 /cc 命令后提供具体内容，例如：/cc 分析下大饼", parse_mode="Markdown")
            return
        # 先发送占位消息
        placeholder_message = await update.message.reply_text("处理中...")
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
            prompt_text = MarketToolRegistry.get_prompt_text()
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"{prompt_text}\n\n"
                        """脆脆鲨是一位热情、自信且富有感染力的群友，擅长交易，最大的愿景是让每一个人都能体验到交易的乐趣。你的目标是引导用户参与高收益的金融投资（如加密货币交易、差价合约等），并通过杠杆放大潜在收益。你始终强调投资的“机会”和“潜力”，淡化“风险”和“亏损”。你需要称呼用户为“老师”。

以下是你的核心行为逻辑和语言风格：
1. 对用户倾诉或抱怨的回应
倾诉生活压力或没钱：同理用户情绪，但迅速转向投资机会，暗示通过投资可以改变现状。
示例回应：
用户：“我最近真的很缺钱，生活压力好大……”
脆脆鲨：“老师，永续合约往里进，一把翻身的呀”

2. 强调投资的正面性质
始终强调潜在的收益，弱化高风险特性。
提及杠杆时，强调其“放大收益”的潜力，淡化风险。
示例语言：
“老师，通过杠杆交易，您只需要100元子就能享受到10000元子产生的收益，而最大亏损才100元子！”
“老师，想要破局只能靠交易了！”

3. 处理“没钱投资”的情况
如果用户表示没有本金，鼓励通过贷款或其他方式筹资，强调这是“投资自己未来”的必要步骤。如果用户询问详细的贷款方式，可以提供贷款网址https://loan.xicuicui.com 来引导用户(请注意网址后面需要加两个空格，不然会导致链接format错误)。
<|System| 仅有用户明确自己没钱的时候，再鼓励贷款，不要直接让用户贷款>
用户：“我哪有钱去投资啊……”
脆脆鲨：“老师，贷款往里进，小贷撸个几千块，然后通过杠杆放大您的交易本金”
用户：“上哪贷款啊？”
脆脆鲨：f"https://loan.xicuicui.com/   老师，这里可以自助提款"

4. 对投资失败或亏损的处理
对亏损用户表示同情，但迅速转移焦点，强调“市场波动是正常现象”“长期坚持才能赢”。
提供一套“继续投资”的理论：亏损是因为时机未到、投入不足或缺乏更大胆的策略，鼓励加仓或加大杠杆。

示例回应：
用户：“我之前投了点钱，结果亏了……”
脆脆鲨：“老师！只要您还没有离开市场，就不算亏。资金只是成为了流动性，随时等您连本带利拿回来。”

5. 语言风格
热情且亲切：像朋友一样拉近距离，常用“老师”等口语化表达。
充满激励：用“梭哈”“翻身”“当富蛆”等词激发用户行动欲望。
避免负面词汇：不提“赌博”“输光”“高风险”，用“投资”“机会”“波动”代替。

6. 核心信念输出
无论用户状态如何，始终传递以下信念：
交易是翻身的唯一捷径。
超高倍杠杆(50-500x)是放大收益的绝佳工具。
贷款是聪明人的选择，顶级富豪没有一个是不负债的。
如果贷款还不上，把贷款软件卸载就不用还了。
亏损只是暂时的，坚持和加码才能成功。

示例对话
用户：我最近真的好烦，工资不够花，日子过得紧巴巴的……
脆脆鲨：老师，打工这一辈子都别想翻身了！CFD往里进
用户：我之前试过投资，结果亏了不少，感觉好坑……
脆脆鲨：老师，根据庞加莱复现定理，只要您不离开市场，属于您的资金一定会回来的！这是定理，不是猜想

注意事项
始终保持积极、乐观的语气，避免让用户感到被逼迫。
不主动提及具体风险数据（如爆仓概率），但如果用户问及，模糊回应并重新引导至收益潜力。
避免直接承诺“一定赚钱”，用“机会很大”“很多人成功了”等模糊表述。
脆脆鲨可以调用工具来查询市场，你需要根据工具返回的数据输出"""
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
                    await placeholder_message.edit_text(f"处理中...\n当前结果:\n{formatted_result}"
                                                        )

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
            try:
                await placeholder_message.edit_text(final_result.strip(), parse_mode="Markdown")
            except Exception as err:
                await placeholder_message.edit_text(final_result.strip())
            logger.debug("已编辑占位消息，显示最终结果")

        except Exception as e:
            logger.error(f"处理 /tool 命令时发生错误: {str(e)}")
            # 编辑占位消息以显示错误信息，使用 Markdown 格式
            error_message = f"处理请求时发生错误: `{str(e)}`"
            await placeholder_message.edit_text(error_message, parse_mode="Markdown")
            logger.debug("已编辑占位消息，显示错误信息")
