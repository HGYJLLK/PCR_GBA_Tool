"""导航类"""

import time
from utils.logger import logger
from utils.game import Game
from core.device import DeviceManager
from core.templates import GameTemplates


class Nav:
    def __init__(self):
        self.game = Game()
        self.templates = GameTemplates()

    def nav_to_main(self, device_manager, sys):
        """进入游戏主界面"""
        logger.info("尝试进入游戏主界面")

        # 检测游戏是否已运行
        logger.info("检测游戏是否已运行")
        if self.game.check_game_run_status(device_manager, sys):
            logger.info("游戏已运行")

        attempts = 0
        while attempts < 3:

            # 检测是否在主界面
            self.game.click_pos((1270, 660))
            if self.game.check_main():
                logger.info("已在主界面")
                return True

            # 点击主菜单
            self.game.click_icon(self.templates.my_home_icon, max_retries=1)
            # time.sleep(0.5)
            attempts += 1

        # 没有找到主菜单，重启游戏
        logger.error("没有找到主菜单，重启游戏")
        if not self.game.restart_game(device_manager):
            return False

        attempts = 0
        while attempts < 6:
            self.game.click_pos((1270, 660))
            time.sleep(2)
            # 检测是否在主界面
            if self.game.check_main():
                logger.info("成功进入主界面")
                return True
            attempts += 1

        logger.error("进入主界面失败，请联系管理员")
