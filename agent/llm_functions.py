"""处理主要输入是str，经由LLM处理的函数。"""
import logging
from typing import AsyncGenerator, Dict, Any, Tuple, List

from utils.config_utils import get_config, DEFAULT_API
from agent.tools_handler import parse_and_invoke_tool
from utils.LLM_utils import LLM, llm_client_manager, PromptsBuilder
from utils.logging_utils import setup_logging
from utils import file_utils, LLM_utils
import utils.db_utils as db
import json
import re
setup_logging()
logger = logging.getLogger(__name__)


async def run_agent_session(
    user_input: str,
    prompt_text: str,
    character_prompt: str = "",
    bias_prompt: str = "",
    llm_api: str = 'gemini-2.5',
    max_iterations: int = 15
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    运行一个多轮 Agent 会话，在每一步中通过 yield 返回状态更新。
    此函数处理与 LLM 和工具交互的核心逻辑，但不处理向用户发送消息。

    Args:
        user_input: 用户的初始输入。
        prompt_text: 用于系统提示的文本，包括工具定义。
        character_prompt: LLM 的角色提示。
        bias_prompt: LLM 的偏向提示。
        llm_api: 要使用的 LLM API。
        max_iterations: 最大迭代次数。

    Yields:
        一个字典，表示 Agent 在每一步的状态。
        可能的状态: 'initializing', 'thinking', 'tool_call', 
                      'final_response', 'max_iterations_reached', 'error'。
    """
    try:
        yield {"status": "initializing", "message": "正在初始化 LLM 客户端..."}
        client = LLM(api=llm_api)

        system_prompt = f"{prompt_text}\n\n{character_prompt}{bias_prompt}"
        current_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户输入: {user_input}"}
        ]

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            yield {"status": "thinking", "iteration": iteration}

            client.set_messages(current_messages)
            logger.debug(f"已设置 messages (当前会话): {current_messages}")

            ai_response = await client.final_response()
            logger.info(f"LLM 原始响应: {ai_response}")

            llm_text_part, tool_results, had_tool_calls = await parse_and_invoke_tool(ai_response)

            if had_tool_calls:
                # 如果有工具调用，则 yield tool_call 状态并准备下一次迭代
                yield {
                    "status": "tool_call",
                    "iteration": iteration,
                    "llm_text": llm_text_part,
                    "tool_results": tool_results,
                    "had_tool_calls": True,
                    "raw_ai_response": ai_response
                }
                
                # 为下一次迭代更新消息历史
                current_messages.append({"role": "assistant", "content": ai_response})
                feedback_content_to_llm = "工具调用结果:\n" + "\n".join(
                    [f"{res.get('tool_name', '未知工具')} 执行结果: {res.get('result', '')}" for res in tool_results]
                )
                current_messages.append({"role": "user", "content": feedback_content_to_llm})
                logger.debug("已将原始LLM响应和完整工具调用结果反馈给 LLM")
            else:
                # 如果没有工具调用，这被视为最终回复
                logger.info(f"第{iteration}轮未调用工具，给出最终回复: {llm_text_part}")
                yield {"status": "final_response", "content": llm_text_part}
                return

        # 如果循环结束，说明已达到最大迭代次数
        logger.warning(f"分析轮次已达上限 ({max_iterations})")
        yield {"status": "max_iterations_reached", "max_iterations": max_iterations}

    except Exception as e:
        logger.error(f"处理 Agent 会话时发生错误: {str(e)}", exc_info=True)
        yield {"status": "error", "message": str(e)}

async def analyze_image_for_rating(
    base64_data: str,
    mime_type: str,
    hard_mode: bool = False,
    parse_mode: str = "markdown",
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    分析图像的base64数据，并返回分析结果和消息历史。

    Args:
        base64_data (str): 图像的base64编码数据。
        mime_type (str): 图像的MIME类型。
        hard_mode (bool): 是否启用更激进的评价模式。
        parse_mode (str): 输出格式，可以是 'markdown' 或 'html'。

    Returns:
        Tuple[str, List[Dict[str, Any]]]: 包含格式化响应和发送给LLM的消息列表的元组。

    Raises:
        ValueError: 如果缺少必要的 prompt 或数据。
    """


    prompt_name = "fuck_or_not_group" if parse_mode == "html" else "fuck_or_not"
    system_prompt = file_utils.load_single_prompt(prompt_name)
    if not system_prompt:
        raise ValueError(f"无法加载 '{prompt_name}' prompt。")

    if hard_mode:
        hard_supplement = file_utils.load_single_prompt("fuck_or_not_hard_mode_supplement")
        if hard_supplement:
            system_prompt += hard_supplement

    user_text = "兄弟看看这个，你想不想操？"
    if hard_mode:
        user_text += "（请使用最极端和粗俗的语言进行评价）"

    llm_messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_data}"},
                },
            ],
        },
    ]

    fuck_api = get_config("fuck_or_not_api", "gemini-2.5")
    llm = LLM_utils.LLM(api=fuck_api)
    llm.set_messages(llm_messages)
    response = await llm.final_response()

    try:
        match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
        json_str = match.group(1) if match else response
        data = json.loads(json_str)

        if parse_mode == "html":
            score = data.get("score", "N/A")
            reason_short = data.get("reason_short", "N/A")
            reason_detail = data.get("reason_detail", "N/A")
            fantasy_short = data.get("fantasy_short", "N/A")
            fantasy_detail = data.get("fantasy_detail", "N/A")
            formatted_response = (
                " <b>分析结果</b> \n\n"
                f"<b>评分</b>: {score}/10\n\n"
                f"<b>理由</b>: {reason_short}\n"
                f"<blockquote expandable>{reason_detail}</blockquote>\n\n"
                f"<b>评价</b>: {fantasy_short}\n"
                f"<blockquote expandable>{fantasy_detail}</blockquote>"
            )
        else:  # markdown
            score = data.get("score", "N/A")
            reason = data.get("reason", "N/A")
            fantasy = data.get("fantasy", "N/A")
            formatted_response = f"```\n分数：{score}\n```\n\n理由：{reason}\n\n评价：{fantasy}"
        
        return formatted_response, llm_messages
        
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"解析LLM JSON响应失败: {e}。将使用原始响应。")
        return response, llm_messages


async def generate_summary(conversation_id: int,summary_type:str = 'save',start:int=0,end:int=0) -> str:
        """
        生成对话总结

        Args:
            conversation_id: 对话ID
            summary_type: 总结类型，save:保存总结，zip:压缩总结
            start: 开始位置
            end: 结束位置

        Returns:
            str: 生成的总结文本

        Raises:
            ValueError: 总结生成失败时抛出
        """
        async with llm_client_manager.semaphore:
            try:
                # 构建对话历史
                client = LLM("gemini-2", "private")

                if summary_type == 'save':
                    turns = db.dialog_turn_get(conversation_id, 'private')
                    start = turns - 70 if turns > 70 else 0
                    messages = PromptsBuilder.build_conv_messages_for_summary(conversation_id, "private", start, turns)
                    user_prompt = file_utils.load_single_prompt("summary_save_user_prompt")
                    if not user_prompt:
                        raise ValueError("无法加载 'summary_save_user_prompt' prompt。")
                    messages.append({"role": "user", "content": user_prompt})
                    client.set_messages(messages)
                elif summary_type == 'zip':
                    messages = PromptsBuilder.build_conv_messages_for_summary(conversation_id, "private", start, end)
                    logger.debug(f"总结文本内容：\r\n{messages}")
                    user_prompt = file_utils.load_single_prompt("summary_zip_user_prompt")
                    if not user_prompt:
                        raise ValueError("无法加载 'summary_zip_user_prompt' prompt。")
                    messages.append({"role": "user", "content": user_prompt})
                    client.set_messages(messages)
                return await client.final_response()

            except Exception as e:
                raise ValueError(f"生成总结失败: {str(e)}")


async def generate_char(character_description: str) -> str:
        """
        根据用户输入生成角色描述文档

        Args:
            character_description: 用户提供的角色描述文本

        Returns:
            str: 生成的JSON格式角色描述文档

        Raises:
            ValueError: 角色生成失败时抛出
        """
        async with llm_client_manager.semaphore:
            try:
                # 构建系统提示词
                system_prompt = file_utils.load_single_prompt("generate_char_prompt")
                if not system_prompt:
                    raise ValueError("无法加载 'generate_char_prompt' prompt。")

                # 构建对话历史
                history = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": character_description},
                ]
                client = LLM(DEFAULT_API, "private")
                client.set_messages(history)
                client.set_default_client()
                result = await client.final_response()
                logger.debug(f"LLM输出角色\r\n{result}\r\n")
                return result

            except Exception as e:
                raise ValueError(f"生成角色失败: {str(e)}")
