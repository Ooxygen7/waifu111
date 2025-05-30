"""
toolsprivate_registry.py - Registry and parser for private tools in CyberWaifu bot.

This module provides a registry for private tools, including their descriptions and
output formats, and a parser to handle tool invocation requests from an LLM.
"""

from typing import Dict, Any, Optional, Callable
from telegram import Update
from telegram.ext import ContextTypes
import logging
from utils.logging_utils import setup_logging
import json
import re
import asyncio

setup_logging()
logger = logging.getLogger(__name__)

# 导入之前定义的工具

from LLM_tools.tools import MARKETTOOLS
from LLM_tools.tools import DATABASE_TOOLS

class DatabaseToolRegistry:
    """A registry for database analysis tools with descriptions, output formats, and metadata for LLM interaction."""
    TOOLS: Dict[str, Dict[str, Any]] = {
        "get_user_list": {
            "description": "Retrieve a list of all users with basic information.",
            "type": "query",
            "parameters": {},
            "output_format": "A string summarizing the list of users with their ID, username, and account tier.",
            "example": {"tool_name": "get_user_list", "parameters": {}},
            "return_value": "User list summary (e.g., 'User List:\nID: 123, Username: user123, Tier: 1\n...')"
        },
        "get_user_details": {
            "description": "Retrieve detailed information about a specific user.",
            "type": "query",
            "parameters": {
                "user_id": {
                    "type": "integer",
                    "description": "The ID of the user to query."
                }
            },
            "output_format": "A string with detailed user information including quotas, balance, and activity.",
            "example": {"tool_name": "get_user_details", "parameters": {"user_id": 123}},
            "return_value": "User details summary (e.g., 'User Details for ID 123:\nUsername: user123\n...')"
        },
        "get_user_conversations": {
            "description": "Retrieve a list of conversation IDs for a specific user.",
            "type": "query",
            "parameters": {
                "user_id": {
                    "type": "integer",
                    "description": "The ID of the user to query."
                }
            },
            "output_format": "A string listing the user's conversation IDs with associated metadata.",
            "example": {"tool_name": "get_user_conversations", "parameters": {"user_id": 123}},
            "return_value": "Conversation list summary (e.g., 'Conversations for User ID 123:\nID: 456, Conv ID: conv_456, ...')"
        },
        "get_conversation_dialog": {
            "description": "Retrieve the latest  detailed content messages of a specific conversation.The user is marked as 'user',and llm is marked as 'assistant'.Even the conversation is  marked as 'yes',you still have access to it.",
            "type": "query",
            "parameters": {
                "conv_id": {
                    "type": "integer",
                    "description": "The conversation ID to query."
                },
                "limit": {
                    "type": "integer",
                    "description": "Limit the number of messages to query."
                }
            },
            "output_format": "A string summarizing the conversation content with dialog entries.",
            "example": {"tool_name": "get_conversation_dialog", "parameters": {"conv_id": 456,"limit":10}},
            "return_value": "Conversation content summary (e.g., 'Conversation dialog for Conv ID 456:\nTurn 1: user: Hello\n...')"
        },
        "analyze_user_activity": {
            "description": "Analyze a user's activity over the past specified days.",
            "type": "analysis",
            "parameters": {
                "user_id": {
                    "type": "integer",
                    "description": "The ID of the user to analyze."
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default: 7)."
                }
            },
            "output_format": "A string summarizing the user's activity including conversation frequency and token usage.",
            "example": {"tool_name": "analyze_user_activity", "parameters": {"user_id": 123, "days": 7}},
            "return_value": "Activity analysis summary (e.g., 'Activity Analysis for User ID 123 (Last 7 Days):\nNew Conversations: 5\n...')"
        },
        "get_user_sign_history": {
            "description": "Retrieve the sign-in history and frequency for a specific user.",
            "type": "query",
            "parameters": {
                "user_id": {
                    "type": "integer",
                    "description": "The ID of the user to query."
                }
            },
            "output_format": "A string summarizing the user's sign-in history and temporary quota.",
            "example": {"tool_name": "get_user_sign_history", "parameters": {"user_id": 123}},
            "return_value": "Sign-in history summary (e.g., 'Sign-in History for User ID 123:\nLast Sign-in: 2023-10-01 10:00:00\n...')"
        },
        "get_top_active_users": {
            "description": "Retrieve the most active users based on conversation count or token usage.",
            "type": "analysis",
            "parameters": {
                "limit": {
                    "type": "integer",
                    "description": "Number of top users to return (default: 10)."
                }
            },
            "output_format": "A string summarizing the top active users with their activity metrics.",
            "example": {"tool_name": "get_top_active_users", "parameters": {"limit": 10}},
            "return_value": "Top active users summary (e.g., 'Top 10 Active Users:\nID: 123, Username: user123, Conversations: 50\n...')"
        },

        "get_group_activity": {
            "description": "Retrieve activity data for a specific group.",
            "type": "query",
            "parameters": {
                "group_id": {
                    "type": "integer",
                    "description": "The ID of the group to query."
                }
            },
            "output_format": "A string summarizing group activity including call count and token usage.",
            "example": {"tool_name": "get_group_activity", "parameters": {"group_id": 789}},
            "return_value": "Group activity summary (e.g., 'Group Activity for ID 789:\nGroup Name: group789\nCall Count: 100\n...')"
        },
        "get_system_stats": {
            "description": "Retrieve overall system statistics.",
            "type": "analysis",
            "parameters": {},
            "output_format": "A string summarizing system-wide metrics like total users and conversations.",
            "example": {"tool_name": "get_system_stats", "parameters": {}},
            "return_value": "System stats summary (e.g., 'System Statistics:\nTotal Users: 1000\nTotal Conversations: 5000\n...')"
        },
        "get_recent_user_conversation_summary": {
            "description": "Summarize the most recent conversation of a user for quick insight.",
            "type": "analysis",
            "parameters": {
                "user_id": {
                    "type": "integer",
                    "description": "The ID of the user to analyze."
                }
            },
            "output_format": "A string summarizing the latest conversation content for the user.",
            "example": {"tool_name": "get_recent_user_conversation_summary", "parameters": {"user_id": 123}},
            "return_value": "Recent conversation summary (e.g., 'Recent Conversation Summary for User ID 123 (Conv ID: 456):\nuser: Hello\n...')"
        },
        "get_user_config": {
            "description": "Retrieve the configuration settings for a specific user.",
            "type": "query",
            "parameters": {
                "user_id": {
                    "type": "integer",
                    "description": "The ID of the user to query."
                }
            },
            "output_format": "A string summarizing the user's configuration settings.",
            "example": {"tool_name": "get_user_config", "parameters": {"user_id": 123}},
            "return_value": "User configuration summary (e.g., 'Configuration for User ID 123:\nCharacter: char1\nAPI: api1\n...')"
        }
    }
    @staticmethod
    def get_tool(tool_name: str) -> Optional[Callable]:
        """Get the tool function by name from DATABASE_TOOLS."""
        return DATABASE_TOOLS.get(tool_name)
    @staticmethod
    def get_prompt_text() -> str:
        """Generate a formatted text of tool descriptions and output formats for embedding in LLM prompts."""
        prompt_lines = [
            "You are an assistant integrated with the CyberWaifu bot system for database analysis. You can invoke specific tools to fetch and analyze user data. Below is a list of available database analysis tools with their descriptions, types, parameters, output formats, return values, and invocation examples. When invoking a tool, format your response as a JSON object with 'tool_name' and 'parameters'. If no tool is needed, respond with plain text.\n",
            "Available Database Analysis Tools:"
        ]
        for tool_name, tool_info in DatabaseToolRegistry.TOOLS.items():
            params_str = "None"
            if tool_info["parameters"]:
                params_str = "\n    Parameters:"
                for param_name, param_info in tool_info["parameters"].items():
                    params_str += f"\n      - {param_name}: {param_info['type']} - {param_info['description']}"
            prompt_lines.append(f"- {tool_name}:")
            prompt_lines.append(f"  Description: {tool_info['description']}")
            prompt_lines.append(
                f"  Type: {tool_info['type'].capitalize()} (indicates if the tool queries data or performs analysis)")
            prompt_lines.append(f"  {params_str}")
            prompt_lines.append(f"  Output Format: {tool_info['output_format']}")
            prompt_lines.append(f"  Return Value: {tool_info['return_value']}")
            prompt_lines.append(f"  Example Invocation: {json.dumps(tool_info['example'], ensure_ascii=False)}")
        prompt_lines.append("""\nInstruction: If the user's request involves multiple steps or dependencies, return a JSON-formatted list of tool calls to be executed in sequence. Use the following format:
    {
      "tool_calls": [
        {
          "tool_name": "tool_name_1",
          "parameters": {
            "param1": "value1"
          }
        },
        {
          "tool_name": "tool_name_2",
          "parameters": {
            "param2": "value2"
          }
        }
      ]
    }
    For single tool invocation, use this format, ensuring parameters are nested under 'parameters':
    {
      "tool_name": "tool_name",
      "parameters": {
        "param1": "value1"
      }
    }
    Tool invocation results will be fed back to you for analysis or further actions. If no tool is required, respond with plain text.""")
        return "\n".join(prompt_lines)





class MarketToolRegistry:
    """A registry for market analysis tools with descriptions, output formats, and metadata for LLM interaction."""
    TOOLS: Dict[str, Dict[str, Any]] = {
        "get_price": {
            "description": "Fetch the current price of a cryptocurrency pair from a specified exchange.",
            "type": "query",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string containing the current price of the specified trading pair.",
            "example": {"tool_name": "get_price", "parameters": {"symbol": "BTC/USDT", "exchange": "binance"}},
            "return_value": "Price information string (e.g., 'Current price of BTC/USDT on binance: 50000 USDT.')"
        },
        "get_historical_data": {
            "description": "Fetch historical OHLCV (Open, High, Low, Close, Volume) data for a cryptocurrency pair.",
            "type": "query",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT)."
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for candles (e.g., 1m, 5m, 1h, 1d)."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of candles to fetch (default: 100)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string summarizing the historical data with key statistics.",
            "example": {"tool_name": "get_historical_data",
                        "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 100, "exchange": "binance"}},
            "return_value": "Historical data summary (e.g., 'Historical data for BTC/USDT on binance...')"
        },
        "get_order_book": {
            "description": "Fetch the current order book for a cryptocurrency pair.",
            "type": "query",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT)."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of bid/ask entries to fetch (default: 10)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string summarizing the top bids and asks from the order book.",
            "example": {"tool_name": "get_order_book",
                        "parameters": {"symbol": "BTC/USDT", "limit": 10, "exchange": "binance"}},
            "return_value": "Order book summary (e.g., 'Order book for BTC/USDT on binance...')"
        },
        "get_market_trends": {
            "description": "Analyze market trends for a cryptocurrency pair based on historical data.",
            "type": "analysis",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT)."
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for analysis (e.g., 1h, 1d)."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of historical data points to analyze (default: 30)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string summarizing the market trend analysis.",
            "example": {"tool_name": "get_market_trends",
                        "parameters": {"symbol": "BTC/USDT", "timeframe": "1d", "limit": 30, "exchange": "binance"}},
            "return_value": "Trend analysis summary (e.g., 'Market trend analysis for BTC/USDT on binance...')"
        },
        "get_volume_analysis": {
            "description": "Analyze trading volume for a cryptocurrency pair based on historical data.",
            "type": "analysis",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT)."
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for analysis (e.g., 1h, 1d)."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of historical data points to analyze (default: 50)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string summarizing the volume analysis.",
            "example": {"tool_name": "get_volume_analysis",
                        "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "exchange": "binance"}},
            "return_value": "Volume analysis summary (e.g., 'Volume analysis for BTC/USDT on binance...')"
        },
        "get_rsi": {
            "description": "Calculate the Relative Strength Index (RSI) for a cryptocurrency pair.",
            "type": "analysis",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT)."
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for analysis (e.g., 1h, 1d)."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of historical data points to analyze (default: 50)."
                },
                "period": {
                    "type": "integer",
                    "description": "Period for RSI calculation (default: 14)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string summarizing the RSI value and interpretation.",
            "example": {"tool_name": "get_rsi",
                        "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "period": 14,
                                       "exchange": "binance"}},
            "return_value": "RSI analysis result (e.g., 'RSI for BTC/USDT on binance: 65.32 (Neutral)')"
        },
        "get_moving_average": {
            "description": "Calculate the Simple Moving Average (SMA) for a cryptocurrency pair.",
            "type": "analysis",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT)."
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for analysis (e.g., 1h, 1d)."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of historical data points to analyze (default: 50)."
                },
                "period": {
                    "type": "integer",
                    "description": "Period for SMA calculation (default: 20)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string summarizing the SMA value and trend direction.",
            "example": {"tool_name": "get_moving_average",
                        "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "period": 20,
                                       "exchange": "binance"}},
            "return_value": "SMA analysis result (e.g., 'SMA (20) for BTC/USDT on binance: 48000.00 USDT, current price is above SMA (bullish signal)')"
        },
        "get_macd": {
            "description": "Calculate the Moving Average Convergence Divergence (MACD) for a cryptocurrency pair.",
            "type": "analysis",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT)."
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for analysis (e.g., 1h, 1d)."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of historical data points to analyze (default: 50)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string summarizing the MACD value and signal interpretation.",
            "example": {"tool_name": "get_macd",
                        "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "exchange": "binance"}},
            "return_value": "MACD analysis result (e.g., 'MACD for BTC/USDT on binance: MACD=120.45, Signal=100.32 (Bullish crossover)')"
        },
        "get_top_movers": {
            "description": "Fetch the top movers (biggest price changes) on a specified exchange.",
            "type": "query",
            "parameters": {
                "limit": {
                    "type": "integer",
                    "description": "Number of top movers to fetch (default: 5)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string summarizing the top movers with their percentage changes.",
            "example": {"tool_name": "get_top_movers", "parameters": {"limit": 5, "exchange": "binance"}},
            "return_value": "Top movers summary (e.g., 'Top 5 movers on binance: BTC/USDT: +5.2%...')"
        },
        "get_candlestick_data": {
            "description": "Fetch raw candlestick (OHLCV) data for a cryptocurrency pair, suitable for charting or custom analysis.",
            "type": "query",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The trading pair symbol (e.g., BTC/USDT)."
                },
                "timeframe": {
                    "type": "string",
                    "description": "The timeframe for candles (e.g., 1m, 5m, 1h, 1d)."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of candles to fetch (default: 50)."
                },
                "exchange": {
                    "type": "string",
                    "description": "The exchange to query (default: binance)."
                }
            },
            "output_format": "A string summarizing the candlestick data in a structured format.",
            "example": {"tool_name": "get_candlestick_data",
                        "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "exchange": "binance"}},
            "return_value": "Candlestick data summary (e.g., 'Candlestick data for BTC/USDT on binance...')"
        }
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
            "Available Market Analysis Tools:"
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
                f"  Type: {tool_info['type'].capitalize()} (indicates if the tool queries data or performs analysis)")
            prompt_lines.append(f"  {params_str}")
            prompt_lines.append(f"  Output Format: {tool_info['output_format']}")
            prompt_lines.append(f"  Return Value: {tool_info['return_value']}")
            prompt_lines.append(f"  Example Invocation: {json.dumps(tool_info['example'], ensure_ascii=False)}")
        prompt_lines.append("""\nImportant Analysis Guideline: For every market analysis request, you MUST include the 'get_candlestick_data' tool as the foundation for visualizing or understanding price movements. Additionally, combine it with 2-3 other relevant tools (e.g., 'get_rsi', 'get_moving_average', 'get_macd', 'get_market_trends', or 'get_volume_analysis') to provide a comprehensive analysis. Ensure that the tools selected are complementary and cover different aspects of the market (e.g., trend, momentum, volume). If the user's request involves multiple steps or dependencies, return a JSON-formatted list of tool calls to be executed in sequence. Use the following format:
    {
      "tool_calls": [
        {
          "tool_name": "tool_name_1",
          "parameters": {
            "param1": "value1"
          }
        },
        {
          "tool_name": "tool_name_2",
          "parameters": {
            "param2": "value2"
          }
        }
      ]
    }
    For single tool invocation, use this format, ensuring parameters are nested under 'parameters':
    {
      "tool_name": "tool_name",
      "parameters": {
        "param1": "value1"
      }
    }
    Tool invocation results will be fed back to you for analysis or further actions. If no tool is required, respond with plain text.""")
        return "\n".join(prompt_lines)


ALL_TOOLS: Dict[str, Callable] = {}

# 从 MarketToolRegistry 添加工具
for tool_name in MarketToolRegistry.TOOLS.keys():
    tool_func = MarketToolRegistry.get_tool(tool_name)
    if tool_func:
        if tool_name in ALL_TOOLS:
            logger.warning(f"工具名称冲突: {tool_name} 已在 ALL_TOOLS 中存在，将被 MarketToolRegistry 覆盖")
        ALL_TOOLS[tool_name] = tool_func

for tool_name in DatabaseToolRegistry.TOOLS.keys():
    tool_func = DatabaseToolRegistry.get_tool(tool_name)
    if tool_func:
        if tool_name in ALL_TOOLS:
            logger.warning(f"工具名称冲突: {tool_name} 已在 ALL_TOOLS 中存在，将被 DatabaseToolRegistry 覆盖")
        ALL_TOOLS[tool_name] = tool_func
logger.info(f"统一工具池初始化完成，包含工具: {list(ALL_TOOLS.keys())}")


async def parse_and_invoke_tool(ai_response: str) -> tuple[
    str, list, bool]:
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
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', ai_response)
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
            json_match = re.search(r'\{(?:[^\{\}]|\{(?:[^\{\}]|\{[^ \{\}]*\})*\})*\}', ai_response)
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
            logger.warning(f"无法解析提取的 JSON 内容: '{json_content_extracted}'. 错误: {jde}. 将其视为文本。")
            # 如果提取的 JSON 无效，则将其内容追加回文本输出
            llm_text_output = (llm_text_output + "\n" + json_content_extracted).strip()
            return llm_text_output, [], False
    if response_data:
        tool_calls = []
        # 检查是否为多工具调用格式 {"tool_calls": [...]}
        if "tool_calls" in response_data and isinstance(response_data["tool_calls"], list):
            tool_calls = response_data["tool_calls"]
        # 检查是否为单工具调用格式 {"tool_name": "..."}
        elif "tool_name" in response_data:
            parameters = response_data.get("parameters", {})
            tool_calls = [{"tool_name": response_data["tool_name"], "parameters": parameters}]
        if tool_calls:
            had_tool_calls = True
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                logger.info(f"解析到工具调用 {i + 1}/{len(tool_calls)}: {tool_name}，参数: {parameters}")
                tool_func = ALL_TOOLS.get(tool_name)
                if tool_func:
                    try:
                        # 确保只传递工具函数实际需要的参数
                        # 这是一个更健壮的参数传递方式，特别是当LLM可能生成多余参数时
                        import inspect
                        sig = inspect.signature(tool_func)
                        filtered_params = {k: v for k, v in parameters.items() if k in sig.parameters}
                        result = await tool_func(**filtered_params) if asyncio.iscoroutinefunction(
                            tool_func) else tool_func(**filtered_params)
                        tool_results_for_llm_feedback.append({
                            "tool_name": tool_name,
                            "parameters": parameters,  # 保持原始参数以便LLM理解
                            "result": result
                        })
                        logger.info(f"工具 {tool_name} 执行成功: {result}")
                    except Exception as e:
                        error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
                        tool_results_for_llm_feedback.append({
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "result": error_msg
                        })
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

