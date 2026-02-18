"""
训练场战斗模块
"""

from module.logger import logger
from module.base.timer import Timer
from module.train.assets import *
from module.character.assets import *


class TrainCombat:
    """
    训练场战斗处理类
    """

    def is_battle_executing(self):
        """
        检测是否已进入战斗

        通过检测战斗界面特有的UI元素来判断：
        - MENU: 暂停/菜单按钮
        - AUTO: 自动战斗按钮

        Returns:
            Button or False: 如果在战斗中返回检测到的按钮，否则返回 False
        """
        if self.appear(MENU, offset=(20, 20)):
            logger.attr("BattleUI", "MENU")
            return MENU
        if self.appear(AUTO, offset=(20, 20)):
            logger.attr("BattleUI", "AUTO")
            return AUTO

        return False

    def combat_preparation_with_ui_click(self):
        """
        战斗前
        """
        logger.hr("Combat preparation (ui_click)", level=1)

        # 点击开始战斗，等待战斗界面出现
        self.ui_click(
            click_button=BATTLE_START,
            check_button=self.is_battle_executing,
            appear_button=BATTLE_START,  # 点击前检查这个按钮
            confirm_wait=2,  # 确认等待2秒
            retry_wait=10,  # 最多重试10秒
        )

        logger.info(" 已确认进入战斗！")

    def wait_battle_loading(self, timeout=30):
        """
        等待战斗加载完成（可选）

        有些游戏在点击"开始战斗"后会有加载界面

        Args:
            timeout (int): 超时时间（秒）

        Returns:
            bool: 是否成功加载
        """
        logger.hr("Wait battle loading", level=2)

        timeout_timer = Timer(timeout).start()

        while 1:
            self.device.screenshot()

            # 检查是否加载完成（进入战斗）
            if self.is_battle_executing():
                logger.info(" 战斗加载完成")
                return True

            # 超时检查
            if timeout_timer.reached():
                logger.warning("✗ 战斗加载超时")
                return False
                
            self.device.sleep(0.5)

        return False
