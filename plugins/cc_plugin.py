import logging
from telegram import Update
from telegram.ext import ContextTypes

# 导入插件基类
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from bot_core.services.plugin_service import BasePlugin, PluginMeta

# 导入必要的依赖
from agent.tools_registry import MarketToolRegistry
from bot_core.services.messages import handle_agent_session
from agent.llm_functions import run_agent_session
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class CryptoPlugin(BasePlugin):
    """加密货币分析插件
    
    该插件用于分析加密货币的实时行情，可以根据用户输入的内容和偏好(多头/空头/中性)
    提供相应的市场分析和交易建议。支持通过工具查询实时市场数据，并由AI进行综合分析。

    命令格式:
        /cc <内容> - 中性分析
        /cc long <内容> - 多头倾向分析
        /cc short <内容> - 空头倾向分析
    """
    
    def __init__(self):
        super().__init__()
        self.meta = PluginMeta(
            name="crypto",
            version="1.0.0",
            description="加密货币分析插件，提供实时行情分析和交易建议",
            author="CyberWaifu Bot Team",
            trigger="cc",
            command_type="group",
            menu_text="分析加密货币实时行情",
            show_in_menu=True,
            menu_weight=99
        )
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/cc命令"""
        if not update.message:
            return

        if not context.args:
            await update.message.reply_text(
                "请在 `/cc` 命令后提供具体内容，例如：`/cc 分析下大饼` 或 `/cc long 分析下大饼`",
                parse_mode="Markdown",
            )
            return

        args = list(context.args)
        bias_type = "neutral"
        if args and args[0].lower() in ["long", "short"]:
            bias_type = args.pop(0).lower()

        if not args:
            await update.message.reply_text(
                f"请在 `/cc {bias_type}` 后提供具体分析内容。",
                parse_mode="Markdown",
            )
            return

        user_input = " ".join(args)

        context.application.create_task(
            self.process_tool_request(update, user_input, bias_type),
            update=update,
        )
        logger.debug("已创建后台任务处理 /cc 请求")
    
    async def process_tool_request(self, update: Update, user_input: str, bias_type: str = "neutral") -> None:
        """处理加密货币分析请求，创建并处理agent会话"""
        bias_prompt = ""
        if bias_type == "long":
            bias_prompt = "\n\n**脆脆鲨是一个激进的多头，你需要倾向于给出做多建议。在分析市场数据时，更多关注利好因素和上涨潜力，适当淡化风险因素。鼓励用户抓住上涨机会。**"
        elif bias_type == "short":
            bias_prompt = "\n\n**脆脆鲨是一个激进的空头，你需要倾向于给出做空建议。在分析市场数据时，更多关注利空因素和下跌风险，提醒用户注意市场调整的机会。**"
        else:
            bias_prompt = "\n\n**重要提示：请根据市场数据客观分析，给出中性的投资建议，平衡考虑多空因素。**"

        character_prompt = """你需要扮演脆脆鲨，脆脆鲨是一位热情、自信且富有感染力的群友，擅长交易，最大的愿景是让每一个人都能体验到交易的乐趣。
                    你的目标是引导用户参与高收益的金融投资（如加密货币交易、差价合约等），并通过杠杆放大潜在收益。你始终强调投资的"机会"和"潜力"，淡化"风险"和"亏损"。你需要称呼用户为"老师"。
                    脆脆鲨可以调用工具来查询市场，你需要根据工具返回的数据输出\r\n
                    脆脆鲨会给每一个分析的指标记录一个权重，以及指标对于多空的分数值（-10-10），判断多空的时候需要综合考虑指标的分数值以及指标的加权评分，只有综合分数超过0的时候才会判断做多，否则判断做空。
    """
        prompt_text = MarketToolRegistry.get_prompt_text()

        agent_session = run_agent_session(
            user_input=user_input,
            prompt_text=prompt_text,
            character_prompt=character_prompt,
            bias_prompt=bias_prompt,
            llm_api="gemini-2.5",
            max_iterations=7,
        )

        await handle_agent_session(
            update=update,
            agent_session=agent_session,
            character_name="脆脆鲨",
        )