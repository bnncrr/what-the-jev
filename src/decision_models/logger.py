"""命令行日志初始化；库调用沿用宿主程序的 logging 配置。"""

import logging
import sys

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'


def configure_logging(level: int = logging.INFO) -> None:
    """为独立运行配置控制台日志，保留已有 handler 和日志级别。"""
    logger = logging.getLogger('decision_models')
    if logger.hasHandlers():
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt='%H:%M:%S'))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
