"""
用于构建需要LLM参与的函数，输入的主要内容是字符串，由LLM处理后直接操作db或os，并返回结果
"""
import asyncio
import json
import re

from agent.tools_registry import logger, ALL_TOOLS


class ToolHandler:
    """
    处理来自LLM的响应，解析并执行其中包含的工具调用。

    该类封装了从原始文本中提取JSON、解析工具调用、执行工具以及处理结果和错误的完整逻辑。

    Attributes:
        ai_response (str): 来自LLM的原始响应字符串。
        llm_text_output (str): 从响应中分离出的纯文本部分。
        tool_results_for_llm (list): 工具执行结果的列表，用于反馈给LLM。
        had_tool_calls (bool): 标记是否成功解析并调用了任何工具。
    """

    def __init__(self, ai_response: str):
        """
        初始化ToolHandler。

        Args:
            ai_response (str): 来自LLM的原始响应。
        """
        self.ai_response = ai_response
        self.llm_text_output = ai_response.strip()
        self.tool_results_for_llm = []
        self.had_tool_calls = False

    def _attempt_json_repair(self, s: str) -> str | None:
        """
        尝试修复一个可能不完整或格式错误的JSON字符串。
        """
        try:
            # 简单的修复：确保括号和引号闭合
            s = s.strip()
            if not s.startswith('{'):
                s = '{' + s
            if not s.endswith('}'):
                s = s + '}'
            
            # 尝试替换单引号为双引号
            s = s.replace("'", '"')

            # 移除尾随逗号
            s = re.sub(r',\s*([\}\]])', r'\1', s)

            json.loads(s)
            return s
        except json.JSONDecodeError:
            return None

    def _extract_json(self) -> tuple[str | None, str]:
        """
        从AI响应中稳健地提取JSON内容。

        它会尝试多种策略来查找和解析JSON：
        1.  从Markdown代码块中提取。
        2.  查找响应中所有可能的JSON对象（包括不完整的）。
        3.  尝试将整个响应作为JSON解析。
        4.  对找到的潜在JSON字符串进行修复。

        在所有成功解析的JSON中，选择最长（信息量最大）的一个作为最终结果。

        Returns:
            tuple[str | None, str]: 一个元组，包含最佳的JSON字符串（如果找到）和响应中剩余的文本部分。
        """
        candidates = []

        # 策略 1: 从Markdown代码块中提取
        for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", self.ai_response):
            content = match.group(1).strip()
            try:
                json.loads(content)
                candidates.append((content, match.group(0)))
                logger.debug(f"从Markdown块中找到有效JSON候选: {content[:100]}...")
            except json.JSONDecodeError:
                repaired = self._attempt_json_repair(content)
                if repaired:
                    candidates.append((repaired, match.group(0)))
                    logger.debug(f"从Markdown块中修复并找到有效JSON候选: {repaired[:100]}...")

        # 策略 2: 查找所有独立的JSON对象
        # 这个正则表达式可以找到以'{'开头、以'}'结尾的平衡括号结构
        for match in re.finditer(r"\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}", self.ai_response):
            content = match.group(0).strip()
            try:
                json.loads(content)
                candidates.append((content, match.group(0)))
                logger.debug(f"从文本中找到有效JSON候选: {content[:100]}...")
            except json.JSONDecodeError:
                # 即使独立对象解析失败，也通常不进行修复，因为可能只是文本的一部分
                pass

        # 策略 3: 尝试将整个响应作为JSON
        try:
            json.loads(self.ai_response)
            candidates.append((self.ai_response, self.ai_response))
            logger.debug("整个响应是一个有效的JSON候选。")
        except json.JSONDecodeError:
            repaired = self._attempt_json_repair(self.ai_response)
            if repaired:
                candidates.append((repaired, self.ai_response))
                logger.debug(f"修复了整个响应并找到有效JSON候选: {repaired[:100]}...")

        if not candidates:
            logger.debug("在所有策略中均未找到有效的JSON内容。")
            return None, self.ai_response

        # 选择最长的有效JSON作为最佳候选
        best_json, source_text = max(candidates, key=lambda item: len(item[0]))
        
        remaining_text = self.ai_response.replace(source_text, "").strip()
        logger.info(f"最终选择的JSON内容 (长度 {len(best_json)}), 剩余文本: '{remaining_text}'")
        
        return best_json, remaining_text

    async def _invoke_tool(self, tool_call: dict) -> dict:
        """
        执行单个工具调用。

        Args:
            tool_call (dict): 包含'tool_name'和'parameters'的字典。

        Returns:
            dict: 包含工具名称、参数和执行结果的字典。
        """
        tool_name = tool_call.get("tool_name")
        parameters = tool_call.get("parameters", {})
        logger.info(f"准备执行工具: {tool_name}，参数: {parameters}")

        if not isinstance(tool_name, str):
            error_msg = f"工具名称无效或缺失: {tool_name}"
            logger.error(error_msg)
            return {"tool_name": "unknown", "parameters": parameters, "result": error_msg}

        tool_func = ALL_TOOLS.get(tool_name)
        if not tool_func:
            error_msg = f"未找到工具: {tool_name}"
            logger.warning(error_msg)
            return {"tool_name": tool_name, "parameters": parameters, "result": error_msg}

        try:
            import inspect
            sig = inspect.signature(tool_func)
            filtered_params = {k: v for k, v in parameters.items() if k in sig.parameters}

            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**filtered_params)
            else:
                result = tool_func(**filtered_params)
            
            logger.debug(f"工具 {tool_name} 执行成功: {result}")
            return {"tool_name": tool_name, "parameters": parameters, "result": result}
        except Exception as e:
            error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"tool_name": tool_name, "parameters": parameters, "result": error_msg}

    async def handle_response(self) -> tuple[str, list, bool]:
        """
        解析并处理LLM的响应，执行任何工具调用。

        这是该类的主要入口点。它协调JSON提取、工具调用和结果聚合。

        Returns:
            tuple[str, list, bool]:
                - llm_text_output (str): LLM响应的文本部分。
                - tool_results_for_llm (list): 工具调用的详细结果列表，用于反馈给LLM。
                - had_tool_calls (bool): 如果成功解析并调用了任何工具，则为True。
        """
        json_content, self.llm_text_output = self._extract_json()

        if not json_content:
            return self.llm_text_output, [], False

        try:
            response_data = json.loads(json_content)
        except json.JSONDecodeError as jde:
            logger.warning(f"无法解析提取的 JSON: '{json_content}'. 错误: {jde}. 将其视为文本。")
            self.llm_text_output = (self.llm_text_output + "\n" + json_content).strip()
            return self.llm_text_output, [], False

        tool_calls = response_data.get("tool_calls", [])
        if not isinstance(tool_calls, list):
            tool_calls = []

        # 兼容单工具调用格式
        if not tool_calls and "tool_name" in response_data:
            tool_calls = [{"tool_name": response_data["tool_name"], "parameters": response_data.get("parameters", {})}]

        if not tool_calls:
            return self.llm_text_output, [], False

        self.had_tool_calls = True
        tasks = [self._invoke_tool(call) for call in tool_calls]
        self.tool_results_for_llm = await asyncio.gather(*tasks)

        return self.llm_text_output, self.tool_results_for_llm, self.had_tool_calls


async def parse_and_invoke_tool(ai_response: str) -> tuple[str, list, bool]:
    """
    解析AI响应并根据需要调用工具。

    此函数作为 ToolHandler 类的便捷包装器。它会实例化处理器，执行响应处理，并返回结果。
    此函数提取响应中的JSON内容（忽略周围的文本）并处理工具调用。

    Args:
        ai_response (str): 来自LLM的原始响应。

    Returns:
        tuple[str, list, bool]:
            - llm_text_output (str): LLM响应的文本部分。
            - tool_results_for_llm_feedback (list): 工具调用的详细结果列表，用于反馈给LLM。
            - had_tool_calls (bool): 如果成功解析并调用了任何工具，则为True。
    """
    handler = ToolHandler(ai_response)
    return await handler.handle_response()
