import json
import os
from typing import Dict, Optional

from utils.config_utils import ADMIN_LIST, BOT_TOKEN, get_config, get_path

# 获取项目根目录的绝对路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    """
    从配置系统获取配置
    返回：包含 token, api, admin 的字典，或在出错时返回 None

    注意：此函数保留是为了向后兼容，新代码应直接使用 config_utils 模块
    """
    try:
        # 使用新的配置系统

        # 获取API列表
        API_LIST = get_config("api_list", [])
        if not API_LIST:
            raise ValueError("配置中未找到 api_list")

        # 返回与旧版相同格式的配置字典
        return {"token": BOT_TOKEN, "api": API_LIST, "admin": ADMIN_LIST}
    except Exception as e:
        print(f"加载配置时出错: {str(e)}")
        return None


def list_all_characters(char_dir: Optional[str] = None) -> list[str]:
    """
    列出所有可用角色
    :param char_dir: 角色文件目录，如果为None则使用配置中的路径
    :return: 角色名称列表
    """
    if char_dir is None:
        char_dir = get_path("characters_path")

    result = []
    for f in os.listdir(char_dir):
        name, ext = os.path.splitext(f)
        if ext not in (".txt", ".json"):
            continue
        result.append(name)
    return result


def load_char(char_file_name: str, char_dir: Optional[str] = None):
    """
    加载指定的角色文件。
    :param char_file_name: 角色文件名 (例如 'my_character.json')
    :param char_dir: 角色文件所在的目录，如果为None则使用配置中的路径
    :return: 角色文件的JSON内容，如果文件不存在或解析失败则返回None
    """
    if char_dir is None:
        char_dir = get_path("characters_path")

    file_path = os.path.join(char_dir, char_file_name)
    try:
        if not os.path.exists(file_path):
            print(f"错误: 角色文件 {file_path} 不存在。")
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            char_data = json.load(f)
            return char_data
    except json.JSONDecodeError as e:
        print(f"错误: 解析角色文件 {file_path} 失败 - {str(e)}")
        return None
    except Exception as e:
        print(f"加载角色文件 {file_path} 时发生未知错误: {str(e)}")
        return None


def load_prompts(prompt_file: Optional[str] = None):
    """
    加载预设文件

    Args:
        prompt_file: 预设文件路径，如果为None则使用配置中的路径

    Returns:
        预设列表或 None
    """
    if prompt_file is None:
        prompt_file = get_path("prompt_path")

    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_data = json.load(f)
            return prompt_data.get("prompt_set_list", [])
    except Exception as e:
        print(f"读取预设文件失败: {str(e)}")
        return None



def load_data_from_file(file_path: str) -> Optional[Dict]:
    """直接从文件加载JSON数据，返回字典或None（处理文件不存在或解析错误）。"""
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在。")
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)  # 加载并返回数据
    except json.JSONDecodeError as e:
        print(f"错误: JSON 文件格式错误 - {e}")
        return None
    except Exception as e:
        print(f"错误: 读取文件时发生意外错误 - {e}")
        return None


def load_character_from_file(filename: str) -> str:
    """
    直接从文件加载角色JSON文件，返回格式化字符串或错误消息。

    Args:
        filename: 角色文件名（不含扩展名）

    Returns:
        str: 格式化的JSON字符串或错误消息
    """
    char_dir = get_path("characters_path")
    file_path = os.path.join(char_dir, filename + ".json")

    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, ensure_ascii=False, indent=4)
    except json.JSONDecodeError:
        return f"Error: File '{file_path}' is not a valid JSON file."
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}"
