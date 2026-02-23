"""
公会战任务处理模块
"""

from module.logger import logger
from module.ui.page import page_team_battle
from module.ui.scroll import Scroll
from module.train.train import TrainHandler
from module.train.assets import CHANGE, CANCEL
from module.character.selector import Selector
from module.character.assets import *
from module.ghz.assets import *

GHZ_SCROLL = Scroll(
    area=公会战滚动条轨道.area,
    color=(128, 172, 233),
    name="GHZ_SCROLL",
)


class GHZHandler(TrainHandler):
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

        # 公会战角色配置
        self.target_characters = {
            "涅妃·涅罗_S3": TEMPLATE_涅妃·涅罗_S3,
            "碧_工作服_S3": TEMPLATE_碧_工作服_S3,
            "吹雪_S3": TEMPLATE_吹雪_S3,
            "美美_万圣节_S3": TEMPLATE_美美_万圣节_S3,
            "涅娅_夏日_S3": TEMPLATE_涅娅_夏日_S3,
        }

        self.character_selector = Selector(
            main=self,
            target_characters=self.target_characters,
            clear_button_position=(706, 601),
        )

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

    def select_boss_1(self):
        """
        点击公会战BOSS_1，每隔1.5s点击一次，直到出现BOSS_1_选中
        """
        logger.hr("选择 BOSS_1", level=1)

        while True:
            self.device.screenshot()

            if self.appear(公会战BOSS_1_选中, offset=(10, 10)):
                logger.info(" BOSS_1 已选中")
                break

            self.device.click(公会战BOSS_1)
            self.device.sleep(1.5)

    def scroll_to_bottom(self):
        """
        将出战列表滚动条滑到底部
        """
        logger.hr("滚动到底部", level=1)
        GHZ_SCROLL.set_bottom(self)

    def click_challenge(self):
        """
        识别并点击挑战按钮
        """
        logger.hr("点击挑战", level=1)

        while True:
            self.device.screenshot()

            if self.appear_then_click(挑战, offset=(10, 10)):
                logger.info(" 已点击挑战")
                break

            self.device.sleep(0.5)

    def click_change(self):
        """
        点击 CHANGE 按钮，等待进入角色选择界面（CANCEL 出现）
        """
        logger.hr("点击 CHANGE", level=1)

        while True:
            self.device.screenshot()

            if self.appear(CANCEL, offset=(30, 30)):
                logger.info(" 已进入角色选择界面")
                break

            if self.appear_then_click(CHANGE, offset=(30, 30)):
                self.device.sleep(1.0)
                continue

            self.device.sleep(0.5)

    def run_ghz_task(self, use_droidcast=False, timeline=None):
        logger.hr("开始公会战任务", level=0)

        try:
            # 导航
            self.navigate_to_ghz()

            # 点击进入训练模式
            self.enter_battle_list()

            # 选择 BOSS_1
            self.select_boss_1()

            # 滚动到底部
            self.scroll_to_bottom()

            # 点击挑战
            self.click_challenge()

            # 点击 CHANGE 进入角色选择界面
            self.click_change()

            # 选择角色
            self.select_characters()

            # 开始战斗 + 监控
            self.start_battle_and_monitor(
                use_droidcast=use_droidcast,
                timeline=timeline,
            )

            logger.hr("公会战任务完成", level=0)
            return True

        except Exception as e:
            logger.exception(e)
            logger.error("公会战任务执行失败")
            return False
