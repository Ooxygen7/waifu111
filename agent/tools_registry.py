"""
toolsprivate_registry.py - Registry and parser for private tools in CyberWaifu bot.

This module provides a registry for private tools, including their descriptions and
output formats, and a parser to handle tool invocation requests from an LLM.
"""

import logging
from utils.logging_utils import setup_logging
import re
import asyncio
from agent.tools import MARKETTOOLS
from agent.tools import DATABASE_SUPER_TOOLS
import json
from typing import Dict, Any, Callable, Optional

setup_logging()
logger = logging.getLogger(__name__)

# 导入之前定义的工具





class DatabaseSuperToolRegistry:
    """A registry for database super tools with direct SQL access, descriptions, and comprehensive database schema information for LLM interaction."""

    TOOLS: Dict[str, Dict[str, Any]] = {
        "query_db": {
            "description": "Execute a direct SQL SELECT query on the database and return formatted results.",
            "type": "query",
            "parameters": {
                "command": {
                    "type": "string",
                    "description": "The SQL SELECT query to execute. Use proper SQL syntax.",
                },
                "params": {
                    "type": "string",
                    "description": "JSON string of parameters for the query (optional). Example: '[123, \"value\"]' for parameterized queries.",
                }
            },
            "output_format": "A string containing the query results with row-by-row data or error message.",
            "example": {
                "tool_name": "query_db",
                "parameters": {"command": "SELECT uid, user_name, account_tier FROM users LIMIT 5", "params": ""}
            },
            "return_value": "Query results summary with formatted rows or error message.",
        },
        "revise_db": {
            "description": "Execute a direct SQL INSERT, UPDATE, or DELETE operation on the database.",
            "type": "update",
            "parameters": {
                "command": {
                    "type": "string",
                    "description": "The SQL command to execute (INSERT, UPDATE, DELETE). Use proper SQL syntax with ? placeholders for parameters.",
                },
                "params": {
                    "type": "string",
                    "description": "JSON string of parameters for the command (optional). Example: '[100.0, 123]' for parameterized queries.",
                }
            },
            "output_format": "A string indicating the number of affected rows or error message.",
            "example": {
                "tool_name": "revise_db",
                "parameters": {"command": "UPDATE users SET balance = ? WHERE uid = ?", "params": "[100.0, 123]"}
            },
            "return_value": "Operation result with affected row count or error message.",
        },
    }

    @staticmethod
    def get_tool(tool_name: str) -> Optional[Callable]:
        """Get the tool function by name from DATABASE_SUPER_TOOLS."""
        return DATABASE_SUPER_TOOLS.get(tool_name)

    @staticmethod
    def get_prompt_text() -> str:
        """Generate a formatted text of tool descriptions and comprehensive database schema for embedding in LLM prompts."""
        prompt_lines = [
            "You are an assistant integrated with the CyberWaifu bot system with DIRECT DATABASE ACCESS. You can execute raw SQL queries and updates on the database. Below is the complete database schema and available super tools.",
            "",
            "=== DATABASE SCHEMA ===",
            "",
            "Table: conversations (Private conversations)",
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
            "Table: dialogs (Private conversation messages)",
            "- id: INTEGER PRIMARY KEY (auto-increment)",
            "- conv_id: TEXT NOT NULL (conversation ID)",
            "- role: TEXT NOT NULL (role: 'assistant' or 'user')",
            "- raw_content: TEXT NOT NULL (original message content)",
            "- turn_order: INTEGER NOT NULL (turn number in conversation)",
            "- created_at: TEXT NOT NULL (creation time)",
            "- processed_content: TEXT (processed content)",
            "- msg_id: INTEGER (Telegram message ID)",
            "",
            "Table: group_dialogs (Group conversation messages)",
            "- group_id: INTEGER (group ID)",
            "- msg_user: INTEGER (message sender user ID)",
            "- trigger_type: TEXT (trigger type)",
            "- msg_text: TEXT (message text content)",
            "- msg_user_name: TEXT (message sender username)",
            "- msg_id: INTEGER (Telegram message ID)",
            "- raw_response: TEXT (original AI response)",
            "- processed_response: TEXT (processed AI response)",
            "- delete_mark: TEXT (deletion flag)",
            "- group_name: TEXT (group name)",
            "- create_at: TEXT (creation time)",
            "",
            "Table: group_user_conversations (Group user conversation tracking)",
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
            "Table: group_user_dialogs (Group user conversation messages)",
            "- id: INTEGER PRIMARY KEY (auto-increment)",
            "- conv_id: TEXT (conversation ID)",
            "- role: TEXT (role: 'assistant' or 'user')",
            "- raw_content: TEXT (original message content)",
            "- turn_order: INTEGER (turn number)",
            "- created_at: TEXT (creation time)",
            "- processed_content: TEXT (processed content)",
            "",
            "Table: groups (Group configurations)",
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
            "Table: user_config (User configurations)",
            "- uid: INTEGER (user ID)",
            "- char: TEXT (character configuration)",
            "- api: TEXT (API configuration)",
            "- preset: TEXT (preset configuration)",
            "- conv_id: TEXT (conversation ID)",
            "- stream: TEXT (streaming mode: 'yes'/'no')",
            "- nick: TEXT (nickname)",
            "",
            "Table: user_sign (User sign-in tracking)",
            "- user_id: INTEGER (user ID)",
            "- last_sign: TEXT (last sign-in time)",
            "- sign_count: INTEGER (total sign-in count)",
            "- frequency: INTEGER (temporary quota)",
            "",
            "Table: users (User information)",
            "- uid: INTEGER (user ID)",
            "- first_name: TEXT (first name)",
            "- last_name: TEXT (last name)",
            "- user_name: TEXT (username)",
            "- create_at: TEXT (creation time)",
            "- conversations: INTEGER (total conversations)",
            "- dialog_turns: INTEGER (total dialog turns)",
            "- update_at: TEXT (last update time)",
            "- input_tokens: INTEGER (input token count)",
            "- output_tokens: INTEGER (output token count)",
            "- account_tier: INTEGER (account tier level)",
            "- remain_frequency: INTEGER (remaining quota)",
            "- balance: REAL (account balance)",
            "",
            "=== AVAILABLE SUPER TOOLS ===",
        ]
        
        for tool_name, tool_info in DatabaseSuperToolRegistry.TOOLS.items():
            params_str = "None"
            if tool_info["parameters"]:
                params_str = "\n    Parameters:"
                for param_name, param_info in tool_info["parameters"].items():
                    params_str += f"\n      - {param_name}: {param_info['type']} - {param_info['description']}"
            prompt_lines.append(f"- {tool_name}:")
            prompt_lines.append(f"  Description: {tool_info['description']}")
            prompt_lines.append(
                f"  Type: {tool_info['type'].capitalize()} (indicates if the tool queries data or performs updates)"
            )
            prompt_lines.append(f"  {params_str}")
            prompt_lines.append(f"  Output Format: {tool_info['output_format']}")
            prompt_lines.append(f"  Return Value: {tool_info['return_value']}")
            prompt_lines.append(
                f"  Example Invocation: {json.dumps(tool_info['example'], ensure_ascii=False)}"
            )
        
        prompt_lines.extend([
            "",
            "=== IMPORTANT USAGE GUIDELINES ===",
            "1. Use parameterized queries with ? placeholders to prevent SQL injection",
            "2. For params field, provide a JSON array string like '[123, \"value\"]'",
            "3. Always use LIMIT clauses for large result sets to avoid overwhelming output",
            "4. Be careful with UPDATE/DELETE operations - they directly modify the database",
            "5. Time fields are stored as TEXT in various formats, use string comparisons",
            "6. JSON fields (like keywords, members_list) need to be parsed if you want to filter by content",
            "7. The 'role' field in dialogs: 'user' = human messages, 'assistant' = AI responses",
            "8. delete_mark fields: check for 'no' or 0 to get non-deleted records",
            "9. 工具使用注意事项：关于对话记录的content详情，一次可以限制查询20条左右，如果有必要可以多次调用，防止一次性处理内容过多",
            "10. 关于用户、群组信息、对话记录的关键字查询，尽量使用模糊匹配（如 LIKE '%keyword%'）",
            "12. 如果输入中提到了具体的用户，请先在users表单中搜索到用户的具体信息，再执行下一步。优先尝试把所有用户的用户first_name和last_name的拼接起来组合成全名，然后在所有用户的全名中模糊搜索内容，如果失败再尝试搜索用户id(应为纯数字，若输入不是纯数字则无需搜索)和用户名。",
            "",
            "Instruction: If the user's request involves multiple steps or dependencies, return a JSON-formatted list of tool calls to be executed in sequence. Use the following format:",
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
            "Tool invocation results will be fed back to you for analysis or further actions. If no tool is required, respond with plain text."
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


async def parse_and_invoke_tool(ai_response: str) -> tuple[str, list, bool]:
    """
    Parse the AI response and invoke tools if necessary. Returns the LLM's text output,
    list of full tool results for LLM feedback, and a boolean indicating if tools were called.
    This function extracts JSON content from the response (ignoring surrounding text) and processes tool calls.
    Args:
        ai_response: The raw response from the LLM.
        update: The Telegram Update object.
        context: The Telegram ContextTypes object.
    Returns:
        tuple: (llm_text_output, tool_results_for_llm_feedback, had_tool_calls)
        - llm_text_output: The textual part of the LLM's response.
        - tool_results_for_llm_feedback: List of detailed results from tool calls for feedback to LLM.
        - had_tool_calls: Boolean, True if any tool calls were successfully parsed and invoked.
    """
    llm_text_output = ai_response.strip()  # 默认整个响应都是文本
    tool_results_for_llm_feedback = []
    had_tool_calls = False
    response_data = None
    json_content_extracted = ""
    # 尝试提取 Markdown 代码块中的 JSON
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", ai_response)
    if code_block_match:
        json_content_extracted = code_block_match.group(1).strip()
        # 从原始响应中移除 JSON 代码块，得到 LLM 的文本部分
        llm_text_output = ai_response.replace(code_block_match.group(0), "").strip()
        logger.debug(f"从 Markdown 代码块中提取 JSON，剩余文本: '{llm_text_output}'")
    else:
        # 如果没有代码块，尝试将整个响应解析为 JSON (仅当它是纯JSON时)
        try:
            parsed_full_response = json.loads(ai_response)
            # 如果整个响应是有效 JSON，则文本部分为空
            response_data = parsed_full_response
            json_content_extracted = ai_response
            llm_text_output = ""  # 整个响应都是 JSON
            logger.debug("整个响应是纯 JSON 格式")
        except json.JSONDecodeError:
            # 如果整个响应不是纯 JSON，则尝试在文本中查找独立的 JSON 对象 (通常不是 LLM 返回的首选格式)
            # 这个正则比较通用，但对于复杂的嵌套或多JSON对象可能不完美
            json_match = re.search(
                r"\{(?:[^\{\}]|\{(?:[^\{\}]|\{[^ \{\}]*\})*\})*\}", ai_response
            )
            if json_match:
                json_content_extracted = json_match.group(0).strip()
                llm_text_output = ai_response.replace(json_match.group(0), "").strip()
                logger.debug(f"从纯文本中提取 JSON，剩余文本: '{llm_text_output}'")
            else:
                logger.debug("未找到 JSON 内容，整个响应作为文本返回")
                return llm_text_output, [], False  # 没有工具调用，直接返回文本
    if json_content_extracted and not response_data:  # 如果通过正则提取了JSON但还没解析
        try:
            response_data = json.loads(json_content_extracted)
        except json.JSONDecodeError as jde:
            logger.warning(
                f"无法解析提取的 JSON 内容: '{json_content_extracted}'. 错误: {jde}. 将其视为文本。"
            )
            # 如果提取的 JSON 无效，则将其内容追加回文本输出
            llm_text_output = (llm_text_output + "\n" + json_content_extracted).strip()
            return llm_text_output, [], False
    if response_data:
        tool_calls = []
        # 检查是否为多工具调用格式 {"tool_calls": [...]}
        if "tool_calls" in response_data and isinstance(
            response_data["tool_calls"], list
        ):
            tool_calls = response_data["tool_calls"]
        # 检查是否为单工具调用格式 {"tool_name": "..."}
        elif "tool_name" in response_data:
            parameters = response_data.get("parameters", {})
            tool_calls = [
                {"tool_name": response_data["tool_name"], "parameters": parameters}
            ]
        if tool_calls:
            had_tool_calls = True
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                logger.info(
                    f"解析到工具调用 {i + 1}/{len(tool_calls)}: {tool_name}，参数: {parameters}"
                )
                tool_func = ALL_TOOLS.get(tool_name)
                if tool_func:
                    try:
                        # 确保只传递工具函数实际需要的参数
                        # 这是一个更健壮的参数传递方式，特别是当LLM可能生成多余参数时
                        import inspect

                        sig = inspect.signature(tool_func)
                        filtered_params = {
                            k: v for k, v in parameters.items() if k in sig.parameters
                        }
                        result = (
                            await tool_func(**filtered_params)
                            if asyncio.iscoroutinefunction(tool_func)
                            else tool_func(**filtered_params)
                        )
                        tool_results_for_llm_feedback.append(
                            {
                                "tool_name": tool_name,
                                "parameters": parameters,  # 保持原始参数以便LLM理解
                                "result": result,
                            }
                        )
                        logger.debug(f"工具 {tool_name} 执行成功: {result}")
                    except Exception as e:
                        error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
                        tool_results_for_llm_feedback.append(
                            {
                                "tool_name": tool_name,
                                "parameters": parameters,
                                "result": error_msg,
                            }
                        )
                        logger.error(error_msg, exc_info=True)
                else:
                    error_msg = f"未找到工具: {tool_name}"
                    tool_results_for_llm_feedback.append({
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "result": error_msg
                    })
                    logger.warning(error_msg)

    return llm_text_output, tool_results_for_llm_feedback, had_tool_calls

