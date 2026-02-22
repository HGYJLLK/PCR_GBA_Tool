"""
公会战任务处理模块
"""

from module.logger import logger
from module.ui.ui import UI
from module.ui.page import page_team_battle
from module.battle.monitor import BattleMonitor
from module.ghz.assets import *


class GHZHandler(UI, BattleMonitor):
    """
    公会战任务处理类
    """

    def __init__(self, config, device=None):
        """
        Args:
            config: 配置对象
            device: 设备对象
        """
        super().__init__(config, device)

    def navigate_to_ghz(self):
        """
        导航到公会战页面
        """
        logger.hr("导航至公会战", level=1)
        self.ui_ensure(page_team_battle)
        logger.info(" 成功进入公会战")

    def click_at(self, x, y):
        """
        点击指定坐标
        """
        logger.info(f"Click @ ({x}, {y})")
        method = self.device.click_methods.get(
            self.config.Emulator_ControlMethod, self.device.click_adb
        )
        method(x, y)

    def enter_battle_list(self):
        """
        点击 (91, 549) 直到出现训练模式，每次间隔 1.5s
        """
        logger.hr("进入出战列表", level=1)

        while True:
            self.device.screenshot()

            if self.appear(训练模式, offset=(30, 30)):
                logger.info(" 检测到训练模式，停止点击")
                break

            self.click_at(91, 549)
            self.device.sleep(1.5)

    def run_ghz_task(self, use_droidcast=False, timeline=None):
        logger.hr("开始公会战任务", level=0)

        try:
            # 导航
            self.navigate_to_ghz()

            # 点击进入出战列表
            self.enter_battle_list()

            logger.hr("公会战任务完成", level=0)
            return True

        except Exception as e:
            logger.exception(e)
            logger.error("公会战任务执行失败")
            return False
