# utils/logger.py
"""日志工具"""
import logging
from airtest.core.settings import Settings as ST


def setup_logger():
    """设置日志配置"""
    ST.LOG_FILE = "log.txt"
    logger = logging.getLogger("airtest")
    logger.setLevel(logging.ERROR)

    # 创建主程序logger
    app_logger = logging.getLogger("pcr_auto")
    handler = logging.FileHandler("log.txt")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)
    return app_logger


logger = setup_logger()