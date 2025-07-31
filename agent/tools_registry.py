"""
toolsprivate_registry.py - Registry and parser for private tools in CyberWaifu bot.

This module provides a registry for private tools, including their descriptions and
output formats, and a parser to handle tool invocation requests from an LLM.
"""

import logging
from utils.logging_utils import setup_logging
from agent.tools import MARKETTOOLS
from agent.tools import DATABASE_SUPER_TOOLS
import json
from typing import Dict, Any, Callable, Optional

setup_logging()
logger = logging.getLogger(__name__)

# 导入之前定义的工具





class DatabaseSuperToolRegistry:
    """一个为数据库超级工具提供的注册表，包含直接SQL访问、工具描述和全面的数据库模式信息，专为LLM交互设计。"""

    TOOLS: Dict[str, Dict[str, Any]] = {
        "query_db": {
            "description": "直接在数据库上执行SQL SELECT查询，并返回格式化的结果。",
            "type": "query",
            "parameters": {
                "command": {
                    "type": "string",
                    "description": "要执行的SQL SELECT查询。请使用正确的SQL语法。",
                },
                "params": {
                    "type": "string",
                    "description": "用于查询的参数的JSON字符串（可选）。示例：'[123, \"value\"]' 用于参数化查询。",
                }
            },
            "output_format": "一个包含逐行数据或错误信息的查询结果字符串。",
            "example": {
                "tool_name": "query_db",
                "parameters": {"command": "SELECT uid, user_name, account_tier FROM users LIMIT 5", "params": ""}
            },
            "return_value": "包含格式化行或错误信息的查询结果摘要。",
        },
        "revise_db": {
            "description": "直接在数据库上执行SQL INSERT、UPDATE或DELETE操作。",
            "type": "update",
            "parameters": {
                "command": {
                    "type": "string",
                    "description": "要执行的SQL命令（INSERT、UPDATE、DELETE）。请使用带有 ? 占位符的正确SQL语法。",
                },
                "params": {
                    "type": "string",
                    "description": "用于命令的参数的JSON字符串（可选）。示例：'[100.0, 123]' 用于参数化查询。",
                }
            },
            "output_format": "一个指示受影响行数或错误信息的字符串。",
            "example": {
                "tool_name": "revise_db",
                "parameters": {"command": "UPDATE users SET balance = ? WHERE uid = ?", "params": "[100.0, 123]"}
            },
            "return_value": "包含受影响行数或错误信息的操作结果。",
        },
        "analyze_group_user_profiles": {
            "description": "分析指定群组的聊天记录，为最活跃的用户生成用户画像。此工具会调用LLM进行深度分析，可能需要一些时间。分析结果将以JSON字符串的形式返回，其中包含一个用户画像对象的列表。",
            "type": "analysis",
            "parameters": {
                "group_id": {
                    "type": "integer",
                    "description": "需要分析的目标群组的ID。",
                }
            },
            "output_format": "一个JSON格式的字符串，包含了识别出的活跃用户的画像列表。如果操作失败，将返回一个包含错误信息的JSON字符串。",
            "example": {
                "tool_name": "analyze_group_user_profiles",
                "parameters": {"group_id": -100123456789}
            },
            "return_value": "一个包含用户画像对象列表或错误信息的JSON字符串。",
        },
    }

    @staticmethod
    def get_tool(tool_name: str) -> Optional[Callable]:
        """通过名称从DATABASE_SUPER_TOOLS获取工具函数。"""
        return DATABASE_SUPER_TOOLS.get(tool_name)

    @staticmethod
    def get_prompt_text() -> str:
        """为嵌入LLM提示生成工具描述和全面数据库模式的格式化文本。"""
        prompt_lines = [
            "你是一个与 CyberWaifu 机器人系统集成的助手，拥有直接数据库访问权限。你可以对数据库执行原始的 SQL 查询和更新。以下是完整的数据库模式和可用的超级工具。",
            "",
            "=== 数据库模式 ===",
            "",
            "表: conversations (私人对话)",
            "- id: INTEGER PRIMARY KEY (auto-increment)",
            "- conv_id: TEXT NOT NULL (conversation ID)",
            "- user_id: INTEGER NOT NULL (user ID)",
            "- character: TEXT NOT NULL (character name)",
            "- preset: TEXT NOT NULL (preset name)",
            "- summary: TEXT (conversation summary)",
            "- create_at: TEXT (creation time)",
            "- update_at: TEXT (last update time)",
            "- delete_mark: INTEGER (deletion flag)",
            "- turns: INTEGER (number of conversation turns)",
            "",
            "表: dialog_summary (私人对话摘要)",
            "- conv_id: TEXT NOT NULL (对话ID)",
            "- summary_area: TEXT NOT NULL (已摘要的对话轮数)",
            "- content: TEXT NOT NULL (摘要文本)",
            "",
            "表: dialogs (私人对话消息)",
            "- id: INTEGER PRIMARY KEY (auto-increment)",
            "- conv_id: TEXT NOT NULL (conversation ID)",
            "- role: TEXT NOT NULL (role: 'assistant' or 'user')",
            "- raw_content: TEXT NOT NULL (original message content)",
            "- turn_order: INTEGER NOT NULL (turn number in conversation)",
            "- created_at: TEXT NOT NULL (creation time)",
            "- processed_content: TEXT (processed content)",
            "- msg_id: INTEGER (Telegram message ID)",
            "",
            "表: group_dialogs (群组对话消息)",
            "- group_id: INTEGER (群组ID)",
            "- msg_user: INTEGER (消息发送者用户ID)",
            "- trigger_type: TEXT (触发类型)",
            "- msg_text: TEXT (消息文本内容)",
            "- msg_user_name: TEXT (消息发送者用户名)",
            "- msg_id: INTEGER (Telegram消息ID)",
            "- raw_response: TEXT (原始AI响应)",
            "- processed_response: TEXT (处理后的AI响应)",
            "- delete_mark: TEXT (删除标记)",
            "- group_name: TEXT (群组名称)",
            "- create_at: TEXT (创建时间)",
            "",
            "表: group_user_conversations (群组用户对话跟踪)",
            "- user_id: INTEGER (user ID)",
            "- group_id: INTEGER (group ID)",
            "- user_name: TEXT (username)",
            "- conv_id: TEXT (conversation ID)",
            "- delete_mark: INTEGER (deletion flag)",
            "- create_at: TEXT (creation time)",
            "- update_at: TEXT (last update time)",
            "- turns: INTEGER (conversation turns)",
            "- group_name: TEXT (group name)",
            "",
            "表: group_user_dialogs (群组用户对话消息)",
            "- id: INTEGER PRIMARY KEY (自增)",
            "- conv_id: TEXT (对话ID)",
            "- role: TEXT (角色: 'assistant' 或 'user')",
            "- raw_content: TEXT (原始消息内容)",
            "- turn_order: INTEGER (轮次)",
            "- created_at: TEXT (创建时间)",
            "- processed_content: TEXT (处理后内容)",
            "",
            "表: groups (群组配置)",
            "- group_id: INTEGER (group ID)",
            "- members_list: TEXT (admin list in JSON format)",
            "- call_count: INTEGER (LLM call count)",
            "- keywords: TEXT (trigger keywords in JSON format)",
            "- active: INTEGER (active status)",
            "- api: TEXT (API configuration)",
            "- char: TEXT (character configuration)",
            "- preset: TEXT (preset configuration)",
            "- input_token: INTEGER (input token count)",
            "- group_name: TEXT (group name)",
            "- update_time: TEXT (last update time)",
            "- rate: REAL (trigger probability)",
            "- output_token: INTEGER (output token count)",
            "- disabled_topics: TEXT (disabled topics in JSON format)",
            "- allowed_topics: TEXT (allowed topics in JSON format)",
            "",
            "表: user_config (用户配置)",
            "- uid: INTEGER (用户ID)",
            "- char: TEXT (角色配置)",
            "- api: TEXT (API配置)",
            "- preset: TEXT (预设配置)",
            "- conv_id: TEXT (对话ID)",
            "- stream: TEXT (流式模式: 'yes'/'no')",
            "- nick: TEXT (昵称)",
            "",
            "表: user_sign (用户签到跟踪)",
            "- user_id: INTEGER (user ID)",
            "- last_sign: TEXT (last sign-in time)",
            "- sign_count: INTEGER (total sign-in count)",
            "- frequency: INTEGER (temporary quota)",
            "",
            "表: users (用户信息)",
            "- uid: INTEGER (用户ID)",
            "- first_name: TEXT (名字)",
            "- last_name: TEXT (姓氏)",
            "- user_name: TEXT (用户名)",
            "- create_at: TEXT (创建时间)",
            "- conversations: INTEGER (总对话数)",
            "- dialog_turns: INTEGER (总对话轮数)",
            "- update_at: TEXT (最后更新时间)",
            "- input_tokens: INTEGER (输入令牌数)",
            "- output_tokens: INTEGER (输出令牌数)",
            "- account_tier: INTEGER (账户等级)",
            "- remain_frequency: INTEGER (剩余配额)",
            "- balance: REAL (账户余额)",
            "",
            "表: user_profiles (由AI生成的用户画像数据)",
            "- user_id: INTEGER NOT NULL (用户ID, 复合主键的一部分)",
            "- group_id: INTEGER NOT NULL (群组ID, 复合主键的一部分)",
            "- profile_json: TEXT (包含用户画像的JSON字符串)",
            "- last_updated: TEXT (最后更新时间戳)",
            "- source_msg_count: INTEGER (为最新更新分析的消息数)",
            "",
            "=== 可用的超级工具 ===",
        ]
        
        for tool_name, tool_info in DatabaseSuperToolRegistry.TOOLS.items():
            params_str = "无"
            if tool_info["parameters"]:
                params_str = "\n    参数:"
                for param_name, param_info in tool_info["parameters"].items():
                    params_str += f"\n      - {param_name}: {param_info['type']} - {param_info['description']}"
            prompt_lines.append(f"- {tool_name}:")
            prompt_lines.append(f"  描述: {tool_info['description']}")
            prompt_lines.append(
                f"  类型: {tool_info['type'].capitalize()} (指示工具是查询数据还是执行更新)"
            )
            prompt_lines.append(f"  {params_str}")
            prompt_lines.append(f"  输出格式: {tool_info['output_format']}")
            prompt_lines.append(f"  返回值: {tool_info['return_value']}")
            prompt_lines.append(
                f"  调用示例: {json.dumps(tool_info['example'], ensure_ascii=False)}"
            )
        
        prompt_lines.extend([
            "",
            "=== 重要使用指南 ===",
            "1. 使用带 ? 占位符的参数化查询以防止SQL注入。",
            "2. 对于 params 字段，请提供一个JSON数​​组字符串，例如 '[123, \"value\"]'。",
            "3. 对于大的结果集，请始终使用LIMIT子句以避免输出过载。",
            "4. 小心使用UPDATE/DELETE操作 - 它们会直接修改数据库。",
            "5. 时间字段以各种格式的TEXT形式存储，请使用字符串比较。",
            "6. 如果要按内容筛选，需要解析JSON字段（如keywords, members_list）。",
            "7. dialogs中的'role'字段：'user' = 人类消息, 'assistant' = AI响应。",
            "8. 工具使用注意事项：关于对话记录的content详情，一次可以限制查询20条左右，如果有必要可以多次调用，防止一次性处理内容过多。",
            "9. 关于用户、群组信息、对话记录的关键字查询，尽量使用模糊匹配（如 LIKE '%keyword%'）。",
            "10. 如果输入中提到了具体的用户或群组，请先在users表单中搜索到用户的具体信息，再执行下一步。优先尝试把所有用户的用户first_name和last_name的拼接起来组合成全名，然后在所有用户的全名中模糊搜索内容，如果失败再尝试搜索用户id(应为纯数字，若输入不是纯数字则无需搜索)和用户名。",
            "",
            "指令：如果用户的请求涉及多个步骤或依赖项，请返回一个JSON格式的工具调用列表，以便按顺序执行。使用以下格式：",
            "```json",
            "{",
            '  "tool_calls": [',
            '    {"tool_name": "query_db", "parameters": {"command": "SELECT ...", "params": ""}},',
            '    {"tool_name": "revise_db", "parameters": {"command": "UPDATE ...", "params": "[value1, value2]"}}',
            "  ]",
            "}",
            "```",
            "或者如果是单个工具调用：",
            "```json",
            "{",
            '  "tool_name": "query_db", "parameters": {"command": "SELECT * FROM users LIMIT 10", "params": ""}',
            "}",
            "```",
            "",
            "工具调用结果将反馈给您进行分析或采取进一步行动。如果不需要任何工具，请以纯文本形式回应。"
        ])
        
        return "\n".join(prompt_lines)




class MarketToolRegistry:
    """A registry for market analysis tools with descriptions, output formats, and metadata for LLM interaction."""

    TOOLS: Dict[str, Dict[str, Any]] = {
        "get_coin_index": {
            "description": "Fetches multiple cryptocurrency indices (price, trends, volume, RSI, SMA, MACD) in a single call. Provides a comprehensive overview of a cryptocurrency pair.",
            "type": "analysis",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT).",
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for analysis (e.g., 1h, 1d).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of historical data points to analyze (default: 50).",
                },
                "period_rsi": {
                    "type": "integer",
                    "description": "Period for RSI calculation (default: 14).",
                },
                "period_sma": {
                    "type": "integer",
                    "description": "Period for SMA calculation (default: 20).",
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance).",
                },
            },
            "output_format": "A string summarizing the price, market trend, volume analysis, RSI, SMA and MACD.",
            "example": {
                "tool_name": "get_coin_index",
                "parameters": {
                    "symbol": "BTC/USDT",
                    "timeframe": "1h",
                    "limit": 50,
                    "period_rsi": 14,
                    "period_sma": 20,
                    "exchange": "binance",
                },
            },
            "return_value": "Comprehensive analysis of cryptocurrency indices including price, trend, volume, RSI, SMA, and MACD.",
        },
        "get_historical_data": {
            "description": "Fetch historical OHLCV (Open, High, Low, Close, Volume) data for a cryptocurrency pair.",
            "type": "query",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT).",
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for candles (e.g., 1m, 5m, 1h, 1d).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of candles to fetch (default: 100).",
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance).",
                },
            },
            "output_format": "A string summarizing the historical data with key statistics.",
            "example": {
                "tool_name": "get_historical_data",
                "parameters": {
                    "symbol": "BTC/USDT",
                    "timeframe": "1h",
                    "limit": 100,
                    "exchange": "binance",
                },
            },
            "return_value": "Historical data summary (e.g., 'Historical data for BTC/USDT on binance...')",
        },
        "get_market_depth": {
            "description": "Fetch the market depth data for a cryptocurrency pair showing buy/sell pressure at different price levels.",
            "type": "query",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT).",
                },
                "depth": {
                    "type": "integer",
                    "description": "Depth of order book to analyze (default: 10).",
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance).",
                },
            },
            "output_format": "A string summarizing the market depth with buy/sell pressure analysis and potential support/resistance levels.",
            "example": {
                "tool_name": "get_market_depth",
                "parameters": {
                    "symbol": "BTC/USDT",
                    "depth": 10,
                    "exchange": "binance",
                },
            },
            "return_value": "Market depth analysis (e.g., 'Market Depth Analysis for BTC/USDT on binance with buy/sell pressure and support/resistance levels')",
        },
        "get_top_movers": {
            "description": "Fetch the top movers (biggest price changes) on a specified exchange.",
            "type": "query",
            "parameters": {
                "limit": {
                    "type": "integer",
                    "description": "Number of top movers to fetch (default: 5).",
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance).",
                },
            },
            "output_format": "A string summarizing the top movers with their percentage changes.",
            "example": {
                "tool_name": "get_top_movers",
                "parameters": {"limit": 5, "exchange": "binance"},
            },
            "return_value": "Top movers summary (e.g., 'Top 5 movers on binance: BTC/USDT: +5.2%...')",
        },
        "get_candlestick_data": {
            "description": "Fetch raw candlestick (OHLCV) data for a cryptocurrency pair, suitable for charting or custom analysis.",
            "type": "query",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT).",
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for candles (e.g., 1m, 5m, 1h, 1d).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of candles to fetch (default: 50).",
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance).",
                },
            },
            "output_format": "A string summarizing the candlestick data in a structured format.",
            "example": {
                "tool_name": "get_candlestick_data",
                "parameters": {
                    "symbol": "BTC/USDT",
                    "timeframe": "1h",
                    "limit": 50,
                    "exchange": "binance",
                },
            },
            "return_value": "Candlestick data summary (e.g., 'Candlestick data for BTC/USDT on binance...')",
        },
    }

    @staticmethod
    def get_tool(tool_name: str) -> Optional[Callable]:
        """Get the tool function by name from MARKETTOOLS."""
        return MARKETTOOLS.get(tool_name)

    @staticmethod
    def get_prompt_text() -> str:
        """Generate a formatted text of tool descriptions and output formats for embedding in LLM prompts."""
        prompt_lines = [
            "You are an assistant integrated with the CyberWaifu bot system for cryptocurrency market analysis. You can invoke specific tools to fetch data and analyze markets. Below is a list of available market analysis tools with their descriptions, types, parameters, output formats, return values, and invocation examples. When invoking a tool, format your response as a JSON object with 'tool_name' and 'parameters'. If no tool is needed, respond with plain text.\n",
            "Available Market Analysis Tools:",
        ]
        for tool_name, tool_info in MarketToolRegistry.TOOLS.items():
            params_str = "None"
            if tool_info["parameters"]:
                params_str = "\n    Parameters:"
                for param_name, param_info in tool_info["parameters"].items():
                    params_str += f"\n      - {param_name}: {param_info['type']} - {param_info['description']}"
            prompt_lines.append(f"- {tool_name}:")
            prompt_lines.append(f"  Description: {tool_info['description']}")
            prompt_lines.append(
                f"  Type: {tool_info['type'].capitalize()} (indicates if the tool queries data or performs analysis)"
            )
            prompt_lines.append(f"  {params_str}")
            prompt_lines.append(f"  Output Format: {tool_info['output_format']}")
            prompt_lines.append(f"  Return Value: {tool_info['return_value']}")
            prompt_lines.append(
                f"  Example Invocation: {json.dumps(tool_info['example'], ensure_ascii=False)}"
            )
        prompt_lines.append("""\nImportant Analysis Guideline: For every market analysis request, you MUST include the 'get_candlestick_data' 
        tool as the foundation for visualizing or understanding price movements. Additionally, combine it with 2-3 other relevant tools 
        (e.g., 'get_coin_index', 'get_historical_data',  or 'get_order_book') to provide a comprehensive analysis. 
        Ensure that the tools selected are complementary and cover different aspects of the market (e.g., trend, momentum, volume).
        
        Data Source Recommendations:
        1. The system will automatically prioritize perpetual futures contracts (e.g., BTC/USDT:USDT) over spot markets when available.
        2. If data is not available on Binance, the system will try alternative exchanges like Bybit, OKX, or Gate.io.
        3. When analyzing specific coins, you can directly request the symbol in spot format (e.g., BTC/USDT), and the system will 
           automatically attempt to retrieve futures data first.
        4. The order book data now covers a wider price range (±10% of current price) with merged orders for better readability.
        5. All numerical data maintains the original precision from the exchange.
        
        If the user's request involves multiple steps or dependencies, return a JSON-formatted list of tool calls to be executed in sequence. 
        Use the following format:
         ```json
    {
      "tool_calls": [
        {"tool_name": "tool_A", "parameters": {"param1": "value1"}},
        {"tool_name": "tool_B", "parameters": {"param2": "value2"}}
      ]
    }
    ```
    或者如果是单个工具调用：
    ```json
    {
      "tool_name": "tool_A", "parameters": {"param1": "value1"}
    }
    ```

    Tool invocation results will be fed back to you for analysis or further actions. If no tool is required, respond with plain text.""")
        return "\n".join(prompt_lines)


ALL_TOOLS: Dict[str, Callable] = {}

# 从 MarketToolRegistry 添加工具
for tool_name in MarketToolRegistry.TOOLS.keys():
    tool_func = MarketToolRegistry.get_tool(tool_name)
    if tool_func:
        if tool_name in ALL_TOOLS:
            logger.warning(
                f"工具名称冲突: {tool_name} 已在 ALL_TOOLS 中存在，将被 MarketToolRegistry 覆盖"
            )
        ALL_TOOLS[tool_name] = tool_func

for tool_name in DatabaseSuperToolRegistry.TOOLS.keys():
    tool_func = DatabaseSuperToolRegistry.get_tool(tool_name)
    if tool_func:
        if tool_name in ALL_TOOLS:
            logger.warning(
                f"工具名称冲突: {tool_name} 已在 ALL_TOOLS 中存在，将被 DatabaseSuperToolRegistry 覆盖"
            )
        ALL_TOOLS[tool_name] = tool_func
logger.info(f"统一工具池初始化完成，包含工具: {list(ALL_TOOLS.keys())}")


