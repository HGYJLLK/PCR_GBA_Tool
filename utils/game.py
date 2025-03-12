from utils.logger import logger
import time
from airtest.core.api import touch, exists, swipe


class Game:
    def __init__(self):
        self.GAME_PACKAGE = "com.bilibili.priconne"

    def restart_game(self, device_manager, templates):
        """重启游戏"""
        logger.info("准备重启游戏")
        try:
            device_manager.device.shell(f"am force-stop {self.GAME_PACKAGE}")
            logger.info("游戏已停止")
            time.sleep(5)
            if self.click_icon(icon=templates.app_icon):
                logger.info("游戏重启成功")
                time.sleep(15)
            else:
                logger.error("游戏启动失败")
        except Exception as e:
            logger.error(f"重启游戏失败: {str(e)}")

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
    def click_pos(pos):
        """点击坐标"""
        logger.info(f"点击坐标：{pos}")
        touch(pos)
        time.sleep(0.5)

    @staticmethod
    def swipe_screen(start_pos, end_pos):
        """滑动屏幕"""
        swipe(start_pos, end_pos)
        time.sleep(0.5)
