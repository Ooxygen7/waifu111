from typing import Dict, Any

from bot_core.public_functions.error import ConfigError
from utils import file_utils


def load_config() -> Dict[str, Any]:
    """加载并验证配置

    Returns:
        Dict[str, Any]: 包含验证后的配置信息

    Raises:
        ConfigError: 配置验证失败时抛出
    """
    bot_config = file_utils.load_config()
    required_fields = ['admin', 'token']

    for field in required_fields:
        if field not in bot_config:
            bot_config = file_utils.load_config("./config/config_local.json")
            if field not in bot_config:
                raise ConfigError(f"缺少必需的配置项: {field}")
        if not bot_config[field]:
            raise ConfigError(f"配置项不能为空: {field}")

    return bot_config


config = load_config()
ADMIN = config['admin']
BOT_TOKEN = config['token']
DEFAULT_CHAR = 'cuicuishark_public'
DEFAULT_PRESET = 'Default_meeting'
DEFAULT_API = 'gemini-2'
