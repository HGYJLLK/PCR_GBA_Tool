"""
训练场任务处理模块
"""

from module.logger import logger
from module.base.timer import Timer
from module.ui.ui import UI
from module.ui.page import page_team_battle
from module.battle.monitor import BattleMonitor


class GHZHandler(UI, BattleMonitor):
    """
    训练场任务处理类
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

    def run_ghz_task(self, use_droidcast=False, timeline=None):
        logger.hr("开始公会战任务", level=0)

        try:
            # 导航
            self.navigate_to_ghz()

            logger.hr("公会战任务完成", level=0)
            return True

        except Exception as e:
            logger.exception(e)
            logger.error("公会战任务执行失败")
            return False
