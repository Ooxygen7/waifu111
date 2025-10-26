"""
配置管理工具模块

该模块负责加载和管理应用程序的配置，提供统一的配置访问接口，
减少硬编码的默认值，并帮助解决模块间的循环依赖问题。
"""

import json
import logging
import os
from typing import Any, Dict, Optional

# 获取项目根目录的绝对路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 日志设置
logger = logging.getLogger(__name__)

# 配置文件路径
DEFAULT_CONFIG_PATH = os.path.join(project_root, "config", "default_config.json")
CONFIG_PATH = os.path.join(project_root, "config", "config.json")
CONFIG_LOCAL_PATH = os.path.join(project_root, "config", "config_local.json")

# 全局配置对象
_config: Dict[str, Any] = {}
_default_config: Dict[str, Any] = {}
_user_config: Dict[str, Any] = {}


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    从JSON文件加载配置

    Args:
        file_path: 配置文件路径

    Returns:
        Dict[str, Any]: 配置字典

    Raises:
        FileNotFoundError: 文件不存在时抛出
        json.JSONDecodeError: JSON解析错误时抛出
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件 {file_path} 不存在")

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"解析配置文件 {file_path} 失败: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"加载配置文件 {file_path} 时出错: {str(e)}")
        raise


def init_config() -> None:
    """
    初始化配置，优先从环境变量加载，然后回退到配置文件。
    """
    global _config, _default_config, _user_config

    # 1. 加载默认配置
    try:
        _default_config = load_json_file(DEFAULT_CONFIG_PATH)
        logger.info("默认配置加载成功")
    except Exception as e:
        logger.error(f"加载默认配置失败: {str(e)}")
        _default_config = {}

    # 2. 加载用户配置文件（如果存在）
    _user_config = {}
    try:
        if os.path.exists(CONFIG_LOCAL_PATH):
            _user_config = load_json_file(CONFIG_LOCAL_PATH)
            logger.info("本地 config_local.json 配置加载成功")
        elif os.path.exists(CONFIG_PATH):
            _user_config = load_json_file(CONFIG_PATH)
            logger.info("标准 config.json 配置加载成功")
    except Exception as e:
        logger.warning(f"加载用户配置文件失败: {str(e)}")

    # 3. 合并默认和用户配置
    _config = _default_config.copy()
    _deep_update(_config, _user_config)

    # 4. 从环境变量覆盖敏感信息 (Render部署的关键!)
    env_vars = {
        'TG_TOKEN': os.environ.get('TG_TOKEN'),
        'ADMIN': os.environ.get('ADMIN'),
        'WEB_PW': os.environ.get('WEB_PW'),
        'VIEWER_PW': os.environ.get('VIEWER_PW')
    }

    if env_vars['TG_TOKEN']:
        _config['TG_TOKEN'] = env_vars['TG_TOKEN']
        logger.info("从环境变量加载 TG_TOKEN")
    if env_vars['ADMIN']:
        # ADMIN 环境变量通常是逗号分隔的字符串，需要转换成列表
        try:
            _config['ADMIN'] = [int(admin_id.strip()) for admin_id in env_vars['ADMIN'].split(',')]
            logger.info("从环境变量加载 ADMIN IDs")
        except ValueError:
            logger.error("环境变量中的 ADMIN 格式不正确，应为逗号分隔的数字ID。")
    if env_vars['WEB_PW']:
        _config['WEB_PW'] = env_vars['WEB_PW']
        logger.info("从环境变量加载 WEB_PW")
    if env_vars['VIEWER_PW']:
        _config['VIEWER_PW'] = env_vars['VIEWER_PW']
        logger.info("从环境变量加载 VIEWER_PW")

    # 5. 验证必要的配置项
    if not _config.get("TG_TOKEN"):
        logger.warning("！！！警告：未找到 TG_TOKEN 配置。机器人将无法启动。")
    if not _config.get("ADMIN"):
        logger.warning("未找到 ADMIN 配置，将使用空列表。")
        _config["ADMIN"] = []


def _deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """
    递归更新字典，保留嵌套结构

    Args:
        target: 目标字典
        source: 源字典
    """
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def get_config(key: Optional[str] = None, default: Any = None) -> Any:
    """
    获取配置值

    Args:
        key: 配置键，支持点号分隔的嵌套键，如 'api.default_api'
             如果为None，则返回整个配置字典
        default: 默认值，当配置项不存在时返回

    Returns:
        Any: 配置值或默认值
    """
    if not _config:
        init_config()

    if key is None:
        return _config

    # 处理嵌套键
    keys = key.split(".")
    value = _config

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def get_path(path_key: str) -> str:
    """
    获取配置中定义的文件路径

    Args:
        path_key: 路径配置键名

    Returns:
        str: 绝对路径
    """
    path = get_config(f"paths.{path_key}")
    if path and path.startswith("./"):
        # 转换相对路径为绝对路径
        return os.path.join(project_root, path[2:])
    return path or ""


def get_api_config(api_name: Optional[str] = None) -> tuple:
    """
    获取API配置

    Args:
        api_name: API名称，如果为None则使用默认API

    Returns:
        tuple: (api_key, base_url, model)

    Raises:
        ValueError: 找不到对应API配置时抛出
    """
    if api_name is None:
        api_name = get_config("api.default_api")

    api_list = get_config("api_list", [])
    for api_config_item in api_list:
        if api_config_item.get("name") == api_name:
            return (
                api_config_item.get("key", ""),
                api_config_item.get("url", ""),
                api_config_item.get("model", ""),
            )

    raise ValueError(f"未找到名为 '{api_name}' 的API配置")


def get_api_multiple(api_name: Optional[str] = None) -> int:
    """
    获取API的multiple值

    Args:
        api_name: API名称，如果为None则使用默认API

    Returns:
        int: multiple值，默认为1
    """
    if api_name is None:
        api_name = get_config("api.default_api")

    api_list = get_config("api_list", [])
    for api in api_list:
        if api.get("name") == api_name:
            return api.get("multiple", 1)

    return 1


# 初始化配置
init_config()

# 导出常用配置常量，方便其他模块直接导入
BOT_TOKEN = get_config("TG_TOKEN", "")
ADMIN_LIST = get_config("ADMIN", [])
DEFAULT_API = get_config("api.default_api", "gemini-2.5")
DEFAULT_CHAR = get_config("user.default_char", "cuicuishark_public")
DEFAULT_PRESET = get_config("user.default_preset", "Default_meeting")
DEFAULT_STREAM = get_config("user.default_stream", "no")
DEFAULT_FREQUENCY = get_config("user.default_frequency", 200)
DEFAULT_BALANCE = get_config("user.default_balance", 1.5)
