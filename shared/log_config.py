"""
探微 (Tanwei) - 统一日志配置模块

所有服务使用统一的日志格式和输出方式。

使用方法:
    from shared.log_config import get_logger
    logger = get_logger("service-name")
    logger.info("消息")
"""

import os
import sys
from loguru import logger

# 统一日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[service]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# JSON 格式日志（生产环境）
LOG_FORMAT_JSON = (
    '{"timestamp": "{time:YYYY-MM-DDTHH:mm:ss.SSSZ}", '
    '"level": "{level}", '
    '"service": "{extra[service]}", '
    '"function": "{function}", '
    '"line": {line}, '
    '"message": "{message}"}'
)


def get_logger(service_name: str):
    """
    获取配置好的 logger 实例

    Args:
        service_name: 服务名称，如 "agent-loop", "svm-filter", "edge-console"

    Returns:
        配置好的 logger 实例
    """
    # 移除默认 handler
    logger.remove()

    # 获取日志级别
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get("LOG_FORMAT", "console").lower()

    # 选择日志格式
    if log_format == "json":
        format_str = LOG_FORMAT_JSON
    else:
        format_str = LOG_FORMAT

    # 添加标准输出 handler
    logger.add(
        sink=sys.stdout,
        format=format_str,
        level=log_level,
        colorize=(log_format != "json"),
        enqueue=True,  # 线程安全
    )

    # 可选：添加文件日志
    log_file = os.environ.get("LOG_FILE")
    if log_file:
        logger.add(
            sink=log_file,
            format=LOG_FORMAT_JSON,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            compression="gz",
            enqueue=True,
        )

    # 绑定服务名称
    return logger.bind(service=service_name)


# 预定义的 logger 工厂函数
def get_agent_loop_logger():
    """获取 agent-loop 服务的 logger"""
    return get_logger("agent-loop")


def get_svm_filter_logger():
    """获取 svm-filter-service 服务的 logger"""
    return get_logger("svm-filter")


def get_llm_service_logger():
    """获取 llm-service 服务的 logger"""
    return get_logger("llm-service")


def get_edge_console_logger():
    """获取 edge-test-console 服务的 logger"""
    return get_logger("edge-console")
