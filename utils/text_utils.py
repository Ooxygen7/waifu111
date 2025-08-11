import re
import base64


def extract_tag_content(text, tag):
    """
    从文本中提取指定标签的内容。
    只提取最外层、完整闭合的标签对。
    如果找到多个匹配项，则返回最长的一个。
    返回前会移除所有HTML标签以提取纯文本。

    Args:
        text: 要提取内容的文本。
        tag: 要提取的标签名（例如 "content"）。

    Returns:
        匹配的标签内容（纯文本，最长的），如果没有匹配到，则返回原始文本。
    """
    # 匹配最外层的、完整闭合的标签
    pattern = re.compile(rf'<{tag}>(.*?)</{tag}>', re.DOTALL)
    matches = pattern.findall(text)

    if not matches:
        return text

    # 找到最长的匹配内容
    longest_match = max(matches, key=len)

    # 移除所有HTML标签，只返回纯文本
    # 移除 <tag>...</tag> 类型的标签
    plain_text = re.sub(r'<[^>]+>.*?</[^>]+>', '', longest_match, flags=re.DOTALL)
    # 移除 <tag/> 或 <tag> 类型的标签
    plain_text = re.sub(r'<[^>]+>', '', plain_text)
    
    return plain_text.strip()


async def convert_file_id_to_base64(file_id: str, context) -> dict:
        """
        将 Telegram file_id 转换为 Base64 编码的图片数据
        Args:
            file_id: Telegram 文件ID
            context: Telegram 上下文对象，用于获取文件
        Returns:
            dict: 包含 mime_type 和 data 的字典，如果失败则返回 None
        """
        try:
            # 获取文件对象
            cfg_file = await context.bot.get_file(file_id)
            # 下载文件数据
            file_data = await cfg_file.download_as_bytearray()
            # 确定 MIME 类型
            mime_type = "image/jpeg"  # 默认值
            if cfg_file.file_path:
                file_path_lower = cfg_file.file_path.lower()
                if file_path_lower.endswith(".png"):
                    mime_type = "image/png"
                elif file_path_lower.endswith(".gif"):
                    mime_type = "image/gif"
                elif file_path_lower.endswith(".jpg") or file_path_lower.endswith(
                    ".jpeg"
                ):
                    mime_type = "image/jpeg"
                elif file_path_lower.endswith(".webp"):
                    mime_type = "image/webp"
                else:
                    # 如果无法从扩展名确定 MIME 类型，可以使用文件头检测（可选）
                    from magic import from_buffer

                    mime_type = from_buffer(file_data, mime=True) or "image/jpeg"
            # 转换为 Base64
            base64_data = base64.b64encode(file_data).decode("utf-8")
            return {"mime_type": mime_type, "data": base64_data}
        except Exception as e:
            print(f"转换 file_id 到 Base64 失败: {str(e)}")
            return {}

def extract_special_control(input_text: str):
    """从用户输入中提取特殊控制标记，返回清理后的输入和控制内容。"""
    pattern = r'<([^>]+)>'  # 正则表达式：匹配 <something> 但不包括嵌套
    match = re.search(pattern, input_text)
    if not match:
        #print("extract_special_control: No match found") #添加
        return [input_text, None]
    special_str = match.group(1).strip()  # 提取标签名，并移除空白字符
    cleaned_input = re.sub(pattern, '', input_text, count=1)  # count=1 表示只替换第一个匹配
    #print(f"extract_special_control: input_text={input_text}, special_str={special_str}, cleaned_input={cleaned_input}") #添加
    return [cleaned_input, special_str]

def contains_nsfw(text: str) -> bool:
    """
    检查文本中是否包含NSFW关键词。
    Args:
        text: 要检查的文本。
    Returns:
        bool: 如果包含NSFW关键词则返回 True，否则返回 False。
    """
    nsfw_keywords = [
        "做爱", "自慰", "口交", "肛交","肛塞","震动棒","小穴","爱液",
        "肉穴", "肉棒", "乳房", "射精", "强奸", "乱伦", "兽交","阴道","淫荡","抽插","侵犯","后穴","肉壁"
        "乳房", "淫乳",
    ]
    text_lower = text.lower()
    for keyword in nsfw_keywords:
        if keyword in text_lower:
            return True
    return False