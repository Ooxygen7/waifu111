import re
import base64


def extract_tag_content(text, tag):
    """
    增强版：从文本中提取指定标签的内容，兼容LLM生成的各种格式错误（如标签未闭合、闭合标签缺失、重复标签等）。
    1. 支持嵌套和多次出现的标签，提取所有内容，返回最长的一个。
    2. 如果没有闭合标签，尝试提取最后一个开始标签到文本结尾的内容。
    3. 如果标签多次出现，提取所有，返回最长的。
    4. 返回前会移除所有html标签及其内容，确保返回纯文本。
    Args:
        text: 要提取内容的文本。
        tag: 要提取的标签名（例如 "content"）。
    Returns:
        匹配的标签内容（最长的一个），如果没有匹配到，则返回原始文本。
    """
    import re

    # 1. 正常情况：<tag>内容</tag>，支持多次出现
    pattern_normal = re.compile(rf'<{tag}>(.*?)</{tag}>', re.DOTALL)
    matches = pattern_normal.findall(text)

    # 2. 异常情况1：只有开始标签，没有闭合标签，如 <tag>内容
    pattern_start_only = re.compile(rf'<{tag}>(.*?)(?=<[a-zA-Z0-9]+>|$)', re.DOTALL)
    # 只考虑没有正常闭合的部分
    # 先找所有开始标签的位置
    start_positions = [m.start() for m in re.finditer(rf'<{tag}>', text)]
    # 找所有正常闭合的区间，避免重复
    closed_spans = [m.span() for m in pattern_normal.finditer(text)]
    closed_ranges = []
    for s, e in closed_spans:
        closed_ranges.append((s, e))
    # 检查每个开始标签是否在已闭合区间内
    for pos in start_positions:
        in_closed = False
        for s, e in closed_ranges:
            if s <= pos < e:
                in_closed = True
                break
        if not in_closed:
            # 从该开始标签到下一个标签或文本结尾
            after = text[pos + len(f'<{tag}>'):]
            # 到下一个标签或结尾
            next_tag = re.search(r'<[a-zA-Z0-9]+>', after)
            if next_tag:
                content = after[:next_tag.start()]
            else:
                content = after
            matches.append(content)

    # 3. 异常情况2：标签嵌套或连续写错，如 <tag><tag>内容
    # 处理连续开始标签但无闭合的情况
    # 例如 <tag><tag>内容
    pattern_nested = re.compile(rf'((?:<{tag}>)+)(.*?)(?=<[a-zA-Z0-9]+>|$)', re.DOTALL)
    for m in pattern_nested.finditer(text):
        # 只处理没有正常闭合的部分
        # 如果该段没有被正常闭合匹配覆盖，则加入
        span = m.span()
        in_closed = False
        for s, e in closed_ranges:
            if s <= span[0] < e:
                in_closed = True
                break
        if not in_closed:
            matches.append(m.group(2))

    # 4. 取最长的一个
    matches = [m.strip() for m in matches if m and m.strip()]
    if not matches:
        result = text
    else:
        result = max(matches, key=len)

    # 5. 移除所有html标签及其内容
    # 先移除所有形如 <xxx>...</xxx> 的标签及其内容（非贪婪匹配，支持嵌套外层）
    result = re.sub(r'<[^>/]+>.*?</[^>]+>', '', result, flags=re.DOTALL)
    # 再移除所有单独的标签 <xxx ...> 或 </xxx>
    result = re.sub(r'<[^>]+>', '', result)
    return result


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