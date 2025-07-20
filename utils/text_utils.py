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
        如果没有找到结束标签，则找最后一个开始标签，返回开始标签到结束的内容
        返回前会移除所有html标签及其内容，确保返回纯文本。
    """
    import re

    end_tag = f"</{tag}>"
    start_tag = f"<{tag}>"

    # 查找最后一个结束标签的位置
    last_end_tag_index = text.rfind(end_tag)

    if last_end_tag_index == -1:  # 没有找到结束标签
        # 查找最后一个开始标签的位置
        last_start_tag_index = text.rfind(start_tag)
        if last_start_tag_index == -1:
            result = text  # 没有找到起始标签，返回原始文本
        else:
            # 返回从最后一个开始标签到文本结束的内容
            content_start = last_start_tag_index + len(start_tag)
            result = text[content_start:]
    else:  # 找到结束标签
        # 从最后一个结束标签往前查找起始标签
        remaining_text = text[:last_end_tag_index]
        first_start_tag_index = remaining_text.rfind(start_tag)

        if first_start_tag_index == -1:
            result = text  # 没有找到起始标签，返回原始文本
        else:
            # 提取标签内容
            content_start = first_start_tag_index + len(start_tag)
            content_end = last_end_tag_index
            result = text[content_start:content_end]

    # 移除所有html标签及其内容
    # 先移除所有形如 <xxx>...</xxx> 的标签及其内容（非贪婪匹配，支持嵌套外层）
    result = re.sub(r'<[^>/]+>.*?</[^>]+>', '', result, flags=re.DOTALL)
    # 再移除所有单独的标签 <xxx ...> 或 </xxx>
    result = re.sub(r'<[^>]+>', '', result)
    return result




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