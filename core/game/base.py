"""基础游戏操作"""

from airtest.core.api import touch, exists, swipe
import time
from utils.logger import logger


class GameBase:
    @staticmethod
    def click_icon(icon, max_retries=10):
        """点击图标"""
        retry_count = 0
        while retry_count < max_retries:
            if exists(icon):
                pos = exists(icon)
                logger.info(f"找到图标，坐标：{pos}")
                touch(pos)
                return True
            retry_count += 1
            time.sleep(0.5)
        logger.error("未能找到图标")
        return False

    @staticmethod
    def swipe_screen(start_pos, end_pos):
        """滑动屏幕"""
        swipe(start_pos, end_pos)
        time.sleep(1)
