from typing import Dict, Any

from bot_core.public_functions.error import ConfigError
from utils.config_utils import get_config, BOT_TOKEN, ADMIN_LIST, DEFAULT_CHAR, DEFAULT_PRESET, DEFAULT_API


def load_config() -> Dict[str, Any]:
    """加载并验证配置

    注意：此函数保留是为了向后兼容，新代码应直接使用 config_utils 模块

    Returns:
        Dict[str, Any]: 包含验证后的配置信息

    Raises:
        ConfigError: 配置验证失败时抛出
    """
    # 验证必要的配置项
    if not BOT_TOKEN:
        raise ConfigError("缺少必需的配置项: TG_TOKEN")

    # 返回配置字典
    return {
        'admin': ADMIN_LIST,
        'token': BOT_TOKEN,
        'api': get_config("api_list", [])
    }


# 为了向后兼容，保留这些变量
config = load_config()
ADMIN = ADMIN_LIST
