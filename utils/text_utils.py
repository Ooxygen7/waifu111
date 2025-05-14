import re



def extract_tag_content(text, tag):
    """
    从文本中提取指定标签的内容，从最后一个结束标签开始往前匹配。
    适用于嵌套标签的情况。
    Args:
        text: 要提取内容的文本。
        tag: 要提取的标签名（例如 "content"）。
    Returns:
        匹配的标签内容，如果没有匹配到，则返回原始文本。
    """
    end_tag = f"</{tag}>"
    start_tag = f"<{tag}>"
    # 查找最后一个结束标签的位置
    last_end_tag_index = text.rfind(end_tag)
    if last_end_tag_index == -1:
        return text  # 没有找到结束标签，返回原始文本
    # 从最后一个结束标签往前查找起始标签
    remaining_text = text[:last_end_tag_index]
    first_start_tag_index = remaining_text.rfind(start_tag)
    if first_start_tag_index == -1:
        return text  # 没有找到起始标签，返回原始文本
    # 提取标签内容
    content_start = first_start_tag_index + len(start_tag)
    content_end = last_end_tag_index
    extracted_content = text[content_start:content_end]
    return extracted_content



def extract_special_control(input_text: str):
    """从用户输入中提取特殊控制标记，返回清理后的输入和控制内容。"""
    pattern = r'<[^>]+>'  # 正则表达式：匹配 <something> 但不包括嵌套
    match = re.search(pattern, input_text)

    if not match:
        return [input_text, None]

    special_str = match.group(0)[1:-1].strip()  # 提取匹配的子字符串，例如 "<example>" -> "example"
    cleaned_input = re.sub(pattern, '', input_text, count=1)  # count=1 表示只替换第一个匹配

    return [cleaned_input, special_str] if special_str else [input_text]
