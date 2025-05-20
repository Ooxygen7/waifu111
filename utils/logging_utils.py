import logging

class ThirdPartyFilter(logging.Filter):
    """
    自定义过滤器，用于抑制第三方库的 DEBUG 和 INFO 日志。
    如果 logger 名称在第三方库列表中，则只允许 WARNING 及以上级别的日志通过。
    """
    third_party_libs = {
        "telegram", "httpcore", "httpx", "asyncio", "urllib3", "requests",
        "aiohttp", "websocket", "pydantic", "json", "sqlite3", "PIL"
    }

    def filter(self, record):
        # 检查 logger 名称是否属于第三方库
        logger_name = record.name.split('.')[0]  # 获取根模块名
        if logger_name in self.third_party_libs:
            # 对于第三方库，只允许 WARNING 及以上级别的日志
            return record.levelno >= logging.WARNING
        # 对于非第三方库（即你的代码），允许所有级别
        return True

def setup_logging():
    """
    设置日志配置，确保控制台显示所有模块的 DEBUG 日志，文件只保存 INFO 日志。
    使用过滤器抑制第三方库的低级别日志。
    """
    # 设置根 logger 级别为 DEBUG，覆盖所有模块
    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.DEBUG)

    # 创建两个 handler：一个用于文件，一个用于控制台
    file_handler = logging.FileHandler("bot.log", encoding='utf-8')
    stream_handler = logging.StreamHandler()

    # 设置文件 handler 的级别为 INFO 或以上（不记录 DEBUG）
    file_handler.setLevel(logging.INFO)
    # 设置控制台 handler 的级别为 DEBUG（允许显示 DEBUG 日志）
    stream_handler.setLevel(logging.DEBUG)

    # 设置日志格式
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(log_format)
    stream_handler.setFormatter(log_format)

    # 清除默认 handler（避免重复添加）
    root_logger.handlers = []

    # 添加 handler 到根 logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    # 添加自定义过滤器到控制台 handler，抑制第三方库的低级别日志
    stream_handler.addFilter(ThirdPartyFilter())
    file_handler.addFilter(ThirdPartyFilter())

# 调用配置函数（在主程序入口处调用）
if __name__ == "__main__":
    setup_logging()
