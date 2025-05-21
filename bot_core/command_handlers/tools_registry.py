"""
toolsprivate_registry.py - Registry and parser for private tools in CyberWaifu bot.

This module provides a registry for private tools, including their descriptions and
output formats, and a parser to handle tool invocation requests from an LLM.
"""

from typing import Dict, Any, Optional, Callable
import json
from telegram import Update
from telegram.ext import ContextTypes
import logging
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# 导入之前定义的工具
from bot_core.command_handlers.tools import PrivateTools, TOOLS_MAPPING


class PrivateToolRegistry:
    """A registry for private tools with descriptions, output formats, and metadata for LLM interaction."""

    TOOLS: Dict[str, Dict[str, Any]] = {
        "stream": {
            "description": "Toggle streaming mode for message delivery.",
            "type": "operation",  # 操作类工具，执行动作
            "parameters": {},
            "output_format": "A string indicating whether streaming mode was toggled successfully.",
            "example": {"tool_name": "stream", "parameters": {}},
            "return_value": "Success or failure message (e.g., 'Streaming mode toggled successfully.')"
        },
        "me": {
            "description": "Display the user's personal information, including account tier, quota, and balance.",
            "type": "query",  # 查询类工具，返回信息
            "parameters": {},
            "output_format": "A string containing user information.",
            "example": {"tool_name": "me", "parameters": {}},
            "return_value": "User information string (e.g., '用户名: user, 账户等级: 1, ...')"
        },
        "new": {
            "description": "Create a new conversation and prompt the user to select a preset and character.",
            "type": "operation",
            "parameters": {},
            "output_format": "A string confirming that a new conversation has been created and selections prompted.",
            "example": {"tool_name": "new", "parameters": {}},
            "return_value": "Confirmation message (e.g., 'New conversation created, preset and character selection prompted.')"
        },
        "status": {
            "description": "Display the current settings, including character, API, preset, and streaming status.",
            "type": "query",
            "parameters": {},
            "output_format": "A string containing current settings.",
            "example": {"tool_name": "status", "parameters": {}},
            "return_value": "Settings information string (e.g., '当前角色: char, 当前接口: api, ...')"
        },
        "char": {
            "description": "Prompt the user to select a character for the conversation.",
            "type": "operation",
            "parameters": {},
            "output_format": "A string confirming that character selection has been prompted.",
            "example": {"tool_name": "char", "parameters": {}},
            "return_value": "Confirmation message (e.g., 'Character selection prompted.')"
        },
        "delchar": {
            "description": "Prompt the user to select a character to delete.",
            "type": "operation",
            "parameters": {},
            "output_format": "A string confirming that character deletion selection has been prompted.",
            "example": {"tool_name": "delchar", "parameters": {}},
            "return_value": "Confirmation message (e.g., 'Character deletion selection prompted.')"
        },
        "newchar": {
            "description": "Start the creation of a new character with a specified name.",
            "type": "operation",
            "parameters": {
                "char_name": {
                    "type": "string",
                    "description": "The name of the new character to be created."
                }
            },
            "output_format": "A string confirming the start of new character creation with the specified name.",
            "example": {"tool_name": "newchar", "parameters": {"char_name": "Alice"}},
            "return_value": "Confirmation message (e.g., 'New character creation started for Alice.')"
        },
        "nick": {
            "description": "Set a nickname for the user in conversations.",
            "type": "operation",
            "parameters": {
                "nickname": {
                    "type": "string",
                    "description": "The nickname to set for the user."
                }
            },
            "output_format": "A string confirming the nickname update or indicating failure.",
            "example": {"tool_name": "nick", "parameters": {"nickname": "CrispShark"}},
            "return_value": "Confirmation or error message (e.g., 'Nickname updated to CrispShark.')"
        },
        "api": {
            "description": "Prompt the user to select an API based on their account tier.",
            "type": "operation",
            "parameters": {},
            "output_format": "A string confirming that API selection has been prompted.",
            "example": {"tool_name": "api", "parameters": {}},
            "return_value": "Confirmation message (e.g., 'API selection prompted.')"
        },
        "preset": {
            "description": "Prompt the user to select a preset for the conversation.",
            "type": "operation",
            "parameters": {},
            "output_format": "A string confirming that preset selection has been prompted.",
            "example": {"tool_name": "preset", "parameters": {}},
            "return_value": "Confirmation message (e.g., 'Preset selection prompted.')"
        },
        "load": {
            "description": "Prompt the user to load a saved conversation.",
            "type": "operation",
            "parameters": {},
            "output_format": "A string confirming that conversation load selection has been prompted.",
            "example": {"tool_name": "load", "parameters": {}},
            "return_value": "Confirmation message (e.g., 'Conversation load selection prompted.')"
        },
        "delete": {
            "description": "Prompt the user to delete a saved conversation.",
            "type": "operation",
            "parameters": {},
            "output_format": "A string confirming that conversation deletion selection has been prompted.",
            "example": {"tool_name": "delete", "parameters": {}},
            "return_value": "Confirmation message (e.g., 'Conversation deletion selection prompted.')"
        },
        "sign": {
            "description": "Perform a daily check-in to gain temporary quota (limited to once every 8 hours).",
            "type": "operation",
            "parameters": {},
            "output_format": "A string indicating the result of the check-in (success or time restriction).",
            "example": {"tool_name": "sign", "parameters": {}},
            "return_value": "Result message (e.g., 'Check-in successful, temporary quota increased by 50.')"
        }
    }

    @staticmethod
    def get_tool(tool_name: str) -> Optional[Callable]:
        """Get the tool function by name from TOOLS_MAPPING."""
        return TOOLS_MAPPING.get(tool_name)

    @staticmethod
    def get_prompt_text() -> str:
        """Generate a formatted text of tool descriptions and output formats for embedding in LLM prompts."""
        prompt_lines = [
            "You are an assistant integrated with the CyberWaifu bot system. You can invoke specific tools to interact with users. Below is a list of available tools with their descriptions, types, parameters, output formats, return values, and invocation examples. When invoking a tool, format your response as a JSON object with 'tool_name' and 'parameters'. If no tool is needed, respond with plain text.\n",
            "Available Tools:"
        ]

        for tool_name, tool_info in PrivateToolRegistry.TOOLS.items():
            params_str = "None"
            if tool_info["parameters"]:
                params_str = "\n    Parameters:"
                for param_name, param_info in tool_info["parameters"].items():
                    params_str += f"\n      - {param_name}: {param_info['type']} - {param_info['description']}"
            prompt_lines.append(f"- {tool_name}:")
            prompt_lines.append(f"  Description: {tool_info['description']}")
            prompt_lines.append(f"  Type: {tool_info['type'].capitalize()} (indicates if the tool queries data or performs an action)")
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


import json
import re

async def parse_and_invoke_tool(ai_response: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[str, list]:
    """
    Parse the AI response and invoke tools if necessary. Returns the final response and intermediate results.
    Args:
        ai_response: The raw response from the LLM.
        update: The Telegram Update object.
        context: The Telegram ContextTypes object.
    Returns:
        tuple: (final_response, intermediate_results)
        - final_response: The response to send to the user.
        - intermediate_results: List of results from tool calls for feedback to LLM.
    """
    try:
        # 尝试提取 Markdown 代码块中的内容
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', ai_response)
        if code_block_match:
            ai_response = code_block_match.group(1).strip()
            logger.debug(f"从 Markdown 代码块中提取 JSON 内容: {ai_response}")

        # 尝试解析 JSON 响应
        response_data = json.loads(ai_response)
        tool_calls = []

        # 检查是否为多工具调用格式 {"tool_calls": [...]}
        if "tool_calls" in response_data and isinstance(response_data["tool_calls"], list):
            tool_calls = response_data["tool_calls"]
        # 检查是否为单工具调用格式 {"tool_name": "..."}
        elif "tool_name" in response_data:
            parameters = response_data.get("parameters", {})
            tool_calls = [{"tool_name": response_data["tool_name"], "parameters": parameters}]

        if tool_calls:
            results = []
            intermediate_results = []
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                logger.info(f"调用工具 {i + 1}/{len(tool_calls)}: {tool_name}，参数: {parameters}")
                # 获取并执行工具
                tool_func = PrivateToolRegistry.get_tool(tool_name)
                if tool_func:
                    try:
                        # 解包 parameters 字典，将其内容作为关键字参数传递给工具函数
                        result = await tool_func(update, context, **parameters)
                        results.append(f"工具 {tool_name} 执行结果: {result}")
                        intermediate_results.append({
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "result": result
                        })
                        logger.info(f"工具 {tool_name} 执行成功: {result}")
                    except Exception as e:
                        error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
                        results.append(error_msg)
                        intermediate_results.append({
                            "tool_name": tool_name,
                            "parameters": parameters,
                            "result": error_msg
                        })
                        logger.error(error_msg)
                else:
                    error_msg = f"未找到工具: {tool_name}"
                    results.append(error_msg)
                    intermediate_results.append({
                        "tool_name": tool_name,
                        "parameters": parameters,
                        "result": error_msg
                    })
                    logger.warning(error_msg)
            # 汇总所有工具调用的结果
            return "\n".join(results), intermediate_results
    except json.JSONDecodeError as jde:
        # 如果无法解析为 JSON，说明不是工具调用，直接返回原始响应
        logger.debug(f"AI 响应不是有效 JSON 格式，直接返回原始文本: {str(jde)}")
        return ai_response, []
    except Exception as e:
        logger.error(f"解析或调用工具时发生错误: {str(e)}")
        return f"处理工具调用时发生错误: {str(e)}", []
    # 如果没有工具调用，直接返回原始响应
    return ai_response, []
