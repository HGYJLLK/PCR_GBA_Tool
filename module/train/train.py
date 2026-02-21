"""
训练场任务处理模块
"""

from module.logger import logger
from module.base.timer import Timer
from module.ui.ui import UI
from module.ui.page import page_train
from module.train.combat import TrainCombat
from module.train.battle_monitor import BattleMonitor
from module.character.selector import Selector
from module.train.assets import *
from module.character.assets import *


class TrainHandler(UI, TrainCombat, BattleMonitor):
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

        # 目标角色配置
        self.target_characters = {
            "水NNK": TEMPLATE_水NNK,
            "AMS": TEMPLATE_AMS,
            "梦狐": TEMPLATE_梦狐,
            "水AMS": TEMPLATE_水AMS,
            "莱莱": TEMPLATE_莱莱,
        }

        # 创建角色选择器
        self.character_selector = Selector(
            main=self,
            target_characters=self.target_characters,
            clear_button_position=(706, 601),
        )

    def navigate_to_train(self):
        """
        导航到训练场页面
        """
        logger.hr("导航至训练场", level=1)
        self.ui_ensure(page_train)
        logger.info(" 成功进入训练场")

    def handle_train_interaction(self):
        """
        处理训练场界面交互流程
        包括：选择关卡、选择难度等
        """
        logger.hr("处理训练场交互", level=1)

        confirm_timer = Timer(1.5, count=4).start()
        interaction_success = False

        # 清空记录
        self.device.stuck_record_clear()
        self.device.click_record_clear()

        while 1:
            self.device.screenshot()

            if self._is_interaction_complete():
                if confirm_timer.reached():
                    logger.info(" 训练场交互完成")
                    break
            else:
                confirm_timer.reset()

            if self.appear(WULI_TEST, interval=5, offset=(30, 30)):
                self.device.click(WULI_TEST)
                continue

            if self.appear(EZ_BUTTON, interval=1.5, offset=(30, 30)):
                self.device.click(EZ_BUTTON)
                continue

            if self.appear(SETTINGS, interval=5, offset=(30, 30)):
                self.device.click(SETTINGS)
                continue

            if self.appear(CHANGE, interval=1.5, offset=(30, 30)):
                self.device.click(CHANGE)
                if not interaction_success:
                    interaction_success = True
                continue

            self.device.sleep(0.3)

        return True

    def _is_interaction_complete(self) -> bool:
        """
        检查训练场交互是否完成

        Returns:
            bool: 是否完成交互（进入角色选择界面）
        """
        return self.appear(CANCEL, offset=(30, 30))

    def select_characters(self):
        """
        选择角色
        """
        logger.hr("选择角色", level=1)
        changed = self.character_selector.ensure_characters_selected()

        if changed:
            logger.info(" 角色选择已完成（进行了重选）")
        else:
            logger.info(" 角色选择已跳过（已正确）")

        return changed

    def start_battle(self):
        """
        开始战斗
        """
        logger.hr("开始战斗", level=1)
        self.combat_preparation_with_ui_click()
        logger.info(" 已进入战斗")

    def start_battle_and_monitor(self, use_droidcast=False, timeline=None):
        """
        开始战斗并完成完整战斗流程：
        1. 点击开始战斗并进入
        2. 开启全set（立即发动 ON）
        3. 监控倒计时，战斗结束后点击伤害报告

        Args:
            use_droidcast: 是否使用 DroidCast 截图（默认 NemuIpc）
            timeline: Timeline 对象（可选）
        """
        logger.hr("开始战斗并监控", level=1)
        self.combat_preparation_with_ui_click()
        logger.info(" 已进入战斗")

        # 等待战斗界面稳定
        import time
        time.sleep(2.0)

        # 开启全set（立即发动）
        self.enable_full_set()

        # 监控倒计时 + 结束后点击报告
        self.monitor_until_end(use_droidcast=use_droidcast, timeline=timeline)

    def run_train_task(self, use_droidcast=False, timeline=None):
        """
        完整训练场任务流程：
        1. 导航到训练场
        2. 选择关卡和难度
        3. 选择角色
        4. 开始战斗
        5. 开启全set（立即发动 ON）
        6. 监控倒计时，战斗结束后点击伤害报告

        Args:
            use_droidcast: 是否使用 DroidCast 截图（默认 NemuIpc）
            timeline: Timeline 对象（可选）
        """
        logger.hr("开始训练场任务", level=0)

        try:
            # 导航
            self.navigate_to_train()

            # 处理交互
            self.handle_train_interaction()

            # 选择角色
            self.select_characters()

            # 开始战斗 + 开启全set + 监控倒计时 + 点击报告
            self.start_battle_and_monitor(
                use_droidcast=use_droidcast,
                timeline=timeline,
            )

            logger.hr("训练场任务完成", level=0)
            return True

        except Exception as e:
            logger.exception(e)
            logger.error("训练场任务执行失败")
            return False
