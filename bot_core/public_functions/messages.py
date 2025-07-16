from telegram.ext import ContextTypes
from utils.LLM_utils import LLM
import telegram
from telegram.error import BadRequest, TelegramError
import logging
from utils.logging_utils import setup_logging
from LLM_tools.tools_registry import parse_and_invoke_tool
setup_logging()
logger = logging.getLogger(__name__)

async def update_message(text:str, placeholder):
    try:
        # Telegram 单条消息最大长度限制4096字符，保险起见用4000
        max_len = 4000
        if len(text) > max_len:
            text = text[-max_len:]
        await placeholder.edit_text(text, parse_mode="markdown")
    except BadRequest as e:
        logger.warning(f"Markdown 解析错误: {str(e)}, 禁用 Markdown 重试")
        try:
            await placeholder.edit_text(text, parse_mode=None)
        except Exception as e2:
            logger.error(f"再次尝试发送消息失败: {e2}")
            placeholder.edit_text(f"Failed: {e2}")
    except TelegramError as e:
        if "Message is not modified" in str(e):
            logger.debug(f"消息内容未变化，跳过更新: {str(e)}")
            placeholder.edit_text(f"Failed: {e}")
        else:
            logger.error(f"更新消息时出错: {str(e)}")
            placeholder.edit_text(f"Failed: {e}")


async def finalize_message(sent_message, text: str, parse:str = "markdown") -> None:
    """
    最终更新消息内容，确保显示最终的处理后的响应。
    Args:
        sent_message: 已发送的消息对象。
        cleared_response (str): 处理后的最终响应内容。
    """
    max_len = 4000
    try:
        # Telegram 单条消息最大长度限制4096字符，保险起见用4000
        if len(text) <= max_len:
            await sent_message.edit_text(text, parse_mode=parse)
            logger.debug(f"使用了{parse}")
        else:
            # 超长时分两段发送，先发前半段，再发后半段
            await sent_message.edit_text(text[:max_len], parse_mode=parse)
            await sent_message.reply_text(text[max_len:], parse_mode=parse)
        logger.info(f"输出：\r\n{text}")
    except BadRequest as e:
        logger.warning(f"{parse} 解析错误: {str(e)}, 禁用 {parse} 重试")
        try:
            if len(text) <= max_len:
                await sent_message.edit_text(text, parse_mode=None)
            else:
                await sent_message.edit_text(text[:max_len], parse_mode=None)
                await sent_message.reply_text(text[max_len:], parse_mode=None)
            logger.info(f"输出：\r\n{text}")
        except Exception as e2:
            logger.error(f"再次尝试发送消息失败: {e2}")
            await sent_message.edit_text(f"Failed: {e2}")
    except TelegramError as e:
        if "Message is not modified" in str(e):
            logger.debug(f"最终更新时消息内容未变化，跳过更新: {str(e)}")
            await sent_message.edit_text(f"Failed: {e}")
        else:
            logger.error(f"最终更新消息时出错: {str(e)}")
            await sent_message.edit_text(f"Failed: {e}")


async def send_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_content: str, parse: str = "markdown", photo=None) -> None:
    """
    直接发送一条消息到指定的用户或群组。
    Args:
        context: Telegram bot context对象。
        chat_id (int): 用户或群组的ID。
        message_content (str): 要发送的消息内容。
        parse (str): 解析模式，默认为"markdown"。
        photo: 可选的图片文件，如果提供则以图片标题形式发送消息。
    """
    max_len = 4000
    try:
        if photo:
            # 如果有图片，以图片标题形式发送
            if len(message_content) <= max_len:
                await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=message_content, parse_mode=parse)
            else:
                # 超长时先发图片和前半段标题，再发后半段文本
                await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=message_content[:max_len], parse_mode=parse)
                await context.bot.send_message(chat_id=chat_id, text=message_content[max_len:], parse_mode=parse)
        else:
            # 纯文本消息
            if len(message_content) <= max_len:
                await context.bot.send_message(chat_id=chat_id, text=message_content, parse_mode=parse)
            else:
                # 超长时分两段发送
                await context.bot.send_message(chat_id=chat_id, text=message_content[:max_len], parse_mode=parse)
                await context.bot.send_message(chat_id=chat_id, text=message_content[max_len:], parse_mode=parse)
        logger.info(f"发送消息到 {chat_id}：\r\n{message_content}")
    except BadRequest as e:
        logger.warning(f"{parse} 解析错误: {str(e)}, 禁用 {parse} 重试")
        try:
            if photo:
                if len(message_content) <= max_len:
                    await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=message_content, parse_mode=None)
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=photo, caption=message_content[:max_len], parse_mode=None)
                    await context.bot.send_message(chat_id=chat_id, text=message_content[max_len:], parse_mode=None)
            else:
                if len(message_content) <= max_len:
                    await context.bot.send_message(chat_id=chat_id, text=message_content, parse_mode=None)
                else:
                    await context.bot.send_message(chat_id=chat_id, text=message_content[:max_len], parse_mode=None)
                    await context.bot.send_message(chat_id=chat_id, text=message_content[max_len:], parse_mode=None)
            logger.info(f"发送消息到 {chat_id}：\r\n{message_content}")
        except Exception as e2:
            logger.error(f"再次尝试发送消息失败: {e2}")
    except TelegramError as e:
        logger.error(f"发送消息时出错: {str(e)}")


async def send_split_message(update, message_text: str, placeholder_message=None, iteration: int = 1) -> None:
    """
    发送可能需要分割的长消息，支持HTML格式和错误处理。
    Args:
        update: Telegram Update对象
        message_text: 要发送的消息内容
        placeholder_message: 可选的占位消息，如果提供则更新该消息，否则发送新消息
        iteration: 当前迭代轮次，用于日志记录
    """
    TELEGRAM_MESSAGE_LIMIT = 4000
    
    if len(message_text) > TELEGRAM_MESSAGE_LIMIT:
        # 分割消息
        parts = []
        current_part = ""
        lines = message_text.split('\n')
        
        for line in lines:
            if len(current_part + line + '\n') > TELEGRAM_MESSAGE_LIMIT:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = line + '\n'
                else:
                    # 单行就超过限制，强制截断
                    parts.append(line[:TELEGRAM_MESSAGE_LIMIT-50] + "...")
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part.strip())
        
        # 发送分割后的消息
        for i, part in enumerate(parts):
            try:
                if i == 0 and placeholder_message:
                    # 更新占位消息
                    await placeholder_message.edit_text(part, parse_mode="HTML")
                else:
                    # 发送新消息
                    await update.message.reply_text(part, parse_mode="HTML")
                logger.debug(f"已发送第{iteration}轮消息部分 {i+1}/{len(parts)}")
            except telegram.error.BadRequest as e:
                logger.warning(f"HTML解析失败，尝试文本模式: {e}")
                try:
                    if i == 0 and placeholder_message:
                        await placeholder_message.edit_text(part, parse_mode=None)
                    else:
                        await update.message.reply_text(part, parse_mode=None)
                except Exception as inner_e:
                    logger.error(f"文本模式发送也失败: {inner_e}", exc_info=True)
                    error_msg = f"第{iteration}轮第{i+1}部分消息发送失败"
                    if i == 0 and placeholder_message:
                        await placeholder_message.edit_text(error_msg)
                    else:
                        await update.message.reply_text(error_msg)
    else:
        # 消息长度正常，直接发送或更新
        try:
            if placeholder_message:
                await placeholder_message.edit_text(message_text, parse_mode="HTML")
                logger.debug(f"已更新第{iteration}轮占位消息，显示结果")
            else:
                await update.message.reply_text(message_text, parse_mode="HTML")
                logger.debug(f"已发送第{iteration}轮消息")
        except telegram.error.BadRequest as e:
            logger.warning(f"HTML解析失败，尝试文本模式: {e}")
            try:
                if placeholder_message:
                    await placeholder_message.edit_text(message_text, parse_mode=None)
                    logger.debug(f"已成功使用文本模式更新第{iteration}轮占位消息")
                else:
                    await update.message.reply_text(message_text, parse_mode=None)
                    logger.debug(f"已成功使用文本模式发送第{iteration}轮消息")
            except Exception as inner_e:
                logger.error(f"文本模式发送也失败: {inner_e}", exc_info=True)
                error_msg = f"第{iteration}轮处理完成，但内容显示失败"
                if placeholder_message:
                    await placeholder_message.edit_text(error_msg)
                else:
                    await update.message.reply_text(error_msg)


async def send_error_message(update, error_message: str, placeholder_message=None) -> None:
    """
    发送错误消息，支持HTML格式和容错处理。
    Args:
        update: Telegram Update对象
        error_message: 错误消息内容
        placeholder_message: 可选的占位消息，如果提供则更新该消息，否则发送新消息
    """
    try:
        if placeholder_message:
            await placeholder_message.edit_text(error_message, parse_mode="HTML")
        else:
            await update.message.reply_text(error_message, parse_mode="HTML")
    except Exception as inner_e:
        logger.warning(f"发送错误消息时HTML解析失败，尝试禁用HTML: {inner_e}")
        try:
            if placeholder_message:
                await placeholder_message.edit_text(error_message, parse_mode=None)
            else:
                await update.message.reply_text(error_message, parse_mode=None)
        except Exception as deepest_e:
            logger.error(f"禁用HTML后发送错误消息也失败: {deepest_e}")
            fallback_msg = "处理请求时发生未知错误，且无法格式化错误信息。"
            if placeholder_message:
                await placeholder_message.edit_text(fallback_msg)
            else:
                await update.message.reply_text(fallback_msg)


class LLMToolHandler:
    """
    通用的LLM工具调用处理类，抽象了LLM调用、工具解析、消息发送等共同逻辑。
    """
    
    def __init__(self, llm_api: str = 'gemini-2.5', max_iterations: int = 7):
        """
        初始化LLM工具处理器。
        Args:
            llm_api: LLM API类型，默认为'gemini-2.5'
            max_iterations: 最大迭代次数，默认为7
        """
        self.llm_api = llm_api
        self.max_iterations = max_iterations
        self.client = None
        
    async def initialize_client(self):
        """初始化LLM客户端"""
        self.client = LLM(api=self.llm_api)
        logger.debug("LLM 客户端初始化完成")
        
    def build_system_prompt(self, prompt_text: str, character_prompt: str = "", bias_prompt: str = "") -> str:
        """
        构建系统提示。
        Args:
            prompt_text: 工具注册表的提示文本
            character_prompt: 角色设定提示
            bias_prompt: 偏向性提示
        Returns:
            完整的系统提示
        """
        return f"{prompt_text}\n\n{character_prompt}{bias_prompt}"
        
    def build_initial_messages(self, system_prompt: str, user_input: str) -> list:
        """
        构建初始消息列表。
        Args:
            system_prompt: 系统提示
            user_input: 用户输入
        Returns:
            消息列表
        """
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户输入: {user_input}"}
        ]
        
    async def process_llm_iteration(self, current_messages: list, iteration: int, update, character_name: str = "脆脆鲨"):
        """
        处理单次LLM迭代。
        Args:
            current_messages: 当前消息历史
            iteration: 当前迭代次数
            update: Telegram Update对象
            character_name: 角色名称，默认为"脆脆鲨"
        Returns:
            tuple: (llm_text_part, tool_results_for_llm_feedback, had_tool_calls, placeholder_message, ai_response)
        """
        # 发送占位消息
        placeholder_message = await update.message.reply_text(
            f"🔄 第 {iteration} 轮分析中...",
            parse_mode="HTML"
        )
        
        # 设置消息并获取LLM响应
        self.client.set_messages(current_messages)
        logger.debug(f"已设置 messages (当前会话): {current_messages}")
        ai_response = await self.client.final_response()
        logger.info(f"LLM 原始响应: {ai_response}")
        
        # 解析工具调用
        
        llm_text_part, tool_results_for_llm_feedback, had_tool_calls = \
            await parse_and_invoke_tool(ai_response)
            
        # 构建迭代消息
        iteration_message_text = f"<b>🤖 第 {iteration} 轮分析结果</b>\n\n"
        
        # 添加LLM文本部分
        if llm_text_part:
            if "<" in llm_text_part and ">" in llm_text_part:
                iteration_message_text += f"{llm_text_part.strip()}\n\n"
            else:
                iteration_message_text += f"<b>{character_name}:</b> {llm_text_part.strip()}\n\n"
            logger.debug(f"{character_name}文本部分: {llm_text_part.strip()}")
            
        # 添加工具调用结果
        if had_tool_calls:
            logger.info(f"工具调用结果（供LLM反馈）: {tool_results_for_llm_feedback}")
            
            # 处理工具结果，使用HTML格式
            tool_results_html = []
            for res in tool_results_for_llm_feedback:
                tool_name = res.get('tool_name', '未知工具')
                tool_result = str(res.get('result', ''))
                if len(tool_result) > 2000:  # 截断限制2000字符
                    trimmed_result = tool_result[:2000] + "..."
                else:
                    trimmed_result = tool_result
                    
                # 使用可展开引用块创建折叠的工具结果
                tool_html = f"<b>🔧 {tool_name} 执行结果:</b>\n<blockquote expandable>{trimmed_result}</blockquote>"
                tool_results_html.append(tool_html)
                
            if tool_results_html:
                iteration_message_text += "\n".join(tool_results_html)
                logger.debug(f"已添加工具结果到当前轮次消息")
                
        # 发送分段消息
        await send_split_message(update, iteration_message_text, placeholder_message, iteration)
        
        return llm_text_part, tool_results_for_llm_feedback, had_tool_calls, placeholder_message, ai_response
        
    def update_message_history(self, current_messages: list, ai_response: str, tool_results_for_llm_feedback: list):
        """
        更新消息历史。
        Args:
            current_messages: 当前消息列表
            ai_response: AI响应
            tool_results_for_llm_feedback: 工具调用结果
        """
        current_messages.append({
            "role": "assistant",
            "content": ai_response
        })
        feedback_content_to_llm = "工具调用结果:\n" + "\n".join(
            [f"{res.get('tool_name', '未知工具')} 执行结果: {res.get('result', '')}" for res in
             tool_results_for_llm_feedback]
        )
        current_messages.append({
            "role": "user",
            "content": feedback_content_to_llm
        })
        logger.debug(f"已将原始LLM响应和完整工具调用结果反馈给 LLM")
        
    async def process_tool_request(self, update, user_input: str, prompt_text: str, 
                                 character_prompt: str = "", bias_prompt: str = "", 
                                 character_name: str = "脆脆鲨") -> None:
        """
        处理工具请求的主要方法。
        Args:
            update: Telegram Update对象
            user_input: 用户输入
            prompt_text: 工具注册表的提示文本
            character_prompt: 角色设定提示
            bias_prompt: 偏向性提示
            character_name: 角色名称
        """
        try:
            # 初始化客户端
            await self.initialize_client()
            
            # 构建系统提示和初始消息
            system_prompt = self.build_system_prompt(prompt_text, character_prompt, bias_prompt)
            current_messages = self.build_initial_messages(system_prompt, user_input)
            
            iteration = 0
            
            while iteration < self.max_iterations:
                iteration += 1
                
                # 处理单次迭代
                llm_text_part, tool_results_for_llm_feedback, had_tool_calls, placeholder_message, ai_response = \
                    await self.process_llm_iteration(current_messages, iteration, update, character_name)
                    
                if had_tool_calls:
                    # 更新消息历史
                    self.update_message_history(current_messages, ai_response, tool_results_for_llm_feedback)
                else:
                    # 没有工具调用，这是最终回复，结束循环
                    logger.info(f"第{iteration}轮未调用工具，{character_name}给出最终回复: {llm_text_part}")
                    break
                    
            # 如果循环结束但仍有工具调用，说明达到最大迭代次数
            if iteration >= self.max_iterations:
                max_iteration_msg = f"<b>⚠️ {character_name}提醒</b>\n\n老师，分析轮次已达上限，如需继续分析请重新发起请求哦！"
                await send_split_message(update, max_iteration_msg)
                
        except Exception as e:
            logger.error(f"处理工具请求时发生错误: {str(e)}", exc_info=True)
            error_message = str(e)
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
            error_message = f"处理请求时发生错误: <code>{error_message}</code>"
            await send_error_message(update, error_message)
            logger.debug("已发送错误消息")
