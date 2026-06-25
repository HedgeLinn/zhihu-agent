"""结构化日志，支持分级输出。"""

import logging
import sys
from src.config.settings import settings


def setup_logger(name: str = "zhihu_agent") -> logging.Logger:
    """创建并配置 logger 实例。

    Args:
        name: logger 名称，默认 "zhihu_agent"

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-7s] %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


# 全局默认 logger
log = setup_logger()
