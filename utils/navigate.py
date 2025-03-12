"""导航类"""

import time
from utils.logger import logger
from utils.game import Game
from core.device import DeviceManager
from core.templates import GameTemplates


class Nav:
    def __init__(self):
        self.game = Game()
        self.device = DeviceManager()
        self.templates = GameTemplates()

    def nav_to_main(self):
        """进入游戏主界面"""
        logger.info("尝试进入游戏主界面")

        # 检测游戏是否已运行
        logger.info("检测游戏是否已运行")
        if self.game.check_game_run_status(self.device):
            logger.info("游戏已运行")

        attempts = 0
        while attempts < 10:

            # 检测是否在主界面
            if self.game.check_main():
                logger.info("已在主界面")
                return True

            # 点击主菜单
            self.game.click_icon(self.templates.my_home_icon)
            time.sleep(0.5)
            attempts += 1

        # 没有找到主菜单，重启游戏
        logger.error("没有找到主菜单，重启游戏")
        self.game.restart_game(self.device)

        attempts = 0
        while attempts < 10:
            # 检测是否在主界面
            if self.game.check_main():
                logger.info("成功进入主界面")
                return True

            self.game.click_pos((1270, 660))
            time.sleep(2)
            attempts += 1

        logger.error("进入主界面失败，请联系管理员")
