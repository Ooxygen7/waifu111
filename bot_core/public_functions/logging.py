import logging

# 初始化日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log",encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 获取全局 logger
logger = logging.getLogger(__name__)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)
httpx_logger.propagate = True