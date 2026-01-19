<<<<<<< Updated upstream
<<<<<<< Updated upstream
import sys

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.base.timer import Timer
from module.logger import logger
from module.ui.ui import UI
from module.ui.page import page_train
from module.train.assets import *
from module.character.assets import *
from module.ui.scroll import Scroll
from module.base.mask import Mask
from module.train.character_selector import CharacterSelector
from module.train.combat import TrainCombat


class TrainTest(UI, TrainCombat):
    """
    训练场测试类
    """

    def __init__(self, config, device=None):
        """
        Args:
            config: 配置对象
            device: 设备对象
        """
        super().__init__(config, device)

        self.target_characters = {
            "CHUNJIAN": TEMPLATE_CHUNJIAN,
            "QINGBING": TEMPLATE_QINGBING,
            "SHUIMA": TEMPLATE_SHUIMA,
            "TIANJIE": TEMPLATE_TIANJIE,
            "SHUISHENGMU": TEMPLATE_SHUISHENGMU,
        }

        # 创建角色选择器
        self.character_selector = CharacterSelector(
            main=self,
            target_characters=self.target_characters,
            clear_button_position=(706, 601),  # 清空按钮坐标
        )

    def handle_train_interaction(self):
        """
        处理训练场界面交互流程
        """
        logger.hr("Handle train interaction", level=1)

        confirm_timer = Timer(1.5, count=4).start()
        interaction_success = False  # 标记是否检测到交互成功

        # 清空记录
        self.device.stuck_record_clear()
        self.device.click_record_clear()

        while 1:
            self.device.screenshot()

            if self._is_interaction_complete():
                if confirm_timer.reached():
                    logger.info("Train interaction completed")
                    break
            else:
                confirm_timer.reset()

            # 检测是否开启无敌
            if self.appear(SETTINGS, interval=5):
                logger.info("SETTINGS button detected - clicking")
                self.device.click(SETTINGS)
                continue

            # 检测并处理 CHANGE 按钮
            if self.appear(CHANGE, interval=5):
                logger.info("CHANGE button detected - clicking")
                self.device.click(CHANGE)
                if not interaction_success:
                    logger.info("Interaction success - button clicked")
                    interaction_success = True
                continue

            self.device.click_adb(922, 278)

        return True

    def _is_interaction_complete(self) -> bool:
        """
        检查训练场交互是否完成

        Returns:
            bool: 是否完成交互
        """
        return self.appear(CANCEL, offset=(30, 30))


def main():
    """
    主测试函数
    """
    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)
    # 禁用卡死检测
    device.disable_stuck_detection()
    # 实例化测试类
    train_test = TrainTest(config=config, device=device)

    # 从任意位置 → 训练场
    logger.hr("Navigate to train page", level=1)
    train_test.ui_ensure(page_train)  # 自动导航到训练场
    logger.info("成功进入训练场！")

    # 处理训练场界面交互
    logger.hr("Start train interaction", level=1)
    train_test.handle_train_interaction()
    logger.info("训练场交互处理完成！")

    # 滚动列表选择角色
    logger.hr("Select character", level=1)
    changed = train_test.character_selector.ensure_characters_selected()

    if changed:
        logger.info(" 角色选择已完成（进行了重选）")
    else:
        logger.info(" 角色选择已跳过（已正确）")

    # 开始战斗
    logger.hr("Start battle", level=1)
    train_test.combat_preparation_with_ui_click()

    # 


if __name__ == "__main__":
    main()
=======
import sys

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.base.timer import Timer
from module.logger import logger
from module.ui.ui import UI
from module.ui.page import page_train
from module.train.assets import *
from module.character.assets import *
from module.ui.scroll import Scroll
from module.base.mask import Mask
from module.train.character_selector import CharacterSelector
from module.train.combat import TrainCombat


class TrainTest(UI, TrainCombat):
    """
    训练场测试类
    """

    def __init__(self, config, device=None):
        """
        Args:
            config: 配置对象
            device: 设备对象
        """
        super().__init__(config, device)

        self.target_characters = {
            "CHUNJIAN": TEMPLATE_CHUNJIAN,
            "QINGBING": TEMPLATE_QINGBING,
            "SHUIMA": TEMPLATE_SHUIMA,
            "TIANJIE": TEMPLATE_TIANJIE,
            "SHUISHENGMU": TEMPLATE_SHUISHENGMU,
        }

        # 创建角色选择器
        self.character_selector = CharacterSelector(
            main=self,
            target_characters=self.target_characters,
            clear_button_position=(706, 601),  # 清空按钮坐标
        )

    def handle_train_interaction(self):
        """
        处理训练场界面交互流程
        """
        logger.hr("Handle train interaction", level=1)

        confirm_timer = Timer(1.5, count=4).start()
        interaction_success = False  # 标记是否检测到交互成功

        # 清空记录
        self.device.stuck_record_clear()
        self.device.click_record_clear()

        while 1:
            self.device.screenshot()

            if self._is_interaction_complete():
                if confirm_timer.reached():
                    logger.info("Train interaction completed")
                    break
            else:
                confirm_timer.reset()

            # 检测是否开启无敌
            if self.appear(SETTINGS, interval=5):
                logger.info("SETTINGS button detected - clicking")
                self.device.click(SETTINGS)
                continue

            # 检测并处理 CHANGE 按钮
            if self.appear(CHANGE, interval=5):
                logger.info("CHANGE button detected - clicking")
                self.device.click(CHANGE)
                if not interaction_success:
                    logger.info("Interaction success - button clicked")
                    interaction_success = True
                continue

            self.device.click_adb(922, 278)

        return True

    def _is_interaction_complete(self) -> bool:
        """
        检查训练场交互是否完成

        Returns:
            bool: 是否完成交互
        """
        return self.appear(CANCEL, offset=(30, 30))


def main():
    """
    主测试函数
    """
    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)
    # 禁用卡死检测
    device.disable_stuck_detection()
    # 实例化测试类
    train_test = TrainTest(config=config, device=device)

    # 从任意位置 → 训练场
    logger.hr("Navigate to train page", level=1)
    train_test.ui_ensure(page_train)  # 自动导航到训练场
    logger.info("成功进入训练场！")

    # 处理训练场界面交互
    logger.hr("Start train interaction", level=1)
    train_test.handle_train_interaction()
    logger.info("训练场交互处理完成！")

    # 滚动列表选择角色
    logger.hr("Select character", level=1)
    changed = train_test.character_selector.ensure_characters_selected()

    if changed:
        logger.info(" 角色选择已完成（进行了重选）")
    else:
        logger.info(" 角色选择已跳过（已正确）")

    # 开始战斗
    logger.hr("Start battle", level=1)
    train_test.combat_preparation_with_ui_click()

    # 


if __name__ == "__main__":
    main()
>>>>>>> Stashed changes
=======
import sys

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.base.timer import Timer
from module.logger import logger
from module.ui.ui import UI
from module.ui.page import page_train
from module.train.assets import *
from module.character.assets import *
from module.ui.scroll import Scroll
from module.base.mask import Mask
from module.train.character_selector import CharacterSelector
from module.train.combat import TrainCombat


class TrainTest(UI, TrainCombat):
    """
    训练场测试类
    """

    def __init__(self, config, device=None):
        """
        Args:
            config: 配置对象
            device: 设备对象
        """
        super().__init__(config, device)

        self.target_characters = {
            "CHUNJIAN": TEMPLATE_CHUNJIAN,
            "QINGBING": TEMPLATE_QINGBING,
            "SHUIMA": TEMPLATE_SHUIMA,
            "TIANJIE": TEMPLATE_TIANJIE,
            "SHUISHENGMU": TEMPLATE_SHUISHENGMU,
        }

        # 创建角色选择器
        self.character_selector = CharacterSelector(
            main=self,
            target_characters=self.target_characters,
            clear_button_position=(706, 601),  # 清空按钮坐标
        )

    def handle_train_interaction(self):
        """
        处理训练场界面交互流程
        """
        logger.hr("Handle train interaction", level=1)

        confirm_timer = Timer(1.5, count=4).start()
        interaction_success = False  # 标记是否检测到交互成功

        # 清空记录
        self.device.stuck_record_clear()
        self.device.click_record_clear()

        while 1:
            self.device.screenshot()

            if self._is_interaction_complete():
                if confirm_timer.reached():
                    logger.info("Train interaction completed")
                    break
            else:
                confirm_timer.reset()

            # 检测是否开启无敌
            if self.appear(SETTINGS, interval=5):
                logger.info("SETTINGS button detected - clicking")
                self.device.click(SETTINGS)
                continue

            # 检测并处理 CHANGE 按钮
            if self.appear(CHANGE, interval=5):
                logger.info("CHANGE button detected - clicking")
                self.device.click(CHANGE)
                if not interaction_success:
                    logger.info("Interaction success - button clicked")
                    interaction_success = True
                continue

            self.device.click_adb(922, 278)

        return True

    def _is_interaction_complete(self) -> bool:
        """
        检查训练场交互是否完成

        Returns:
            bool: 是否完成交互
        """
        return self.appear(CANCEL, offset=(30, 30))


def main():
    """
    主测试函数
    """
    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)
    # 禁用卡死检测
    device.disable_stuck_detection()
    # 实例化测试类
    train_test = TrainTest(config=config, device=device)

    # 从任意位置 → 训练场
    logger.hr("Navigate to train page", level=1)
    train_test.ui_ensure(page_train)  # 自动导航到训练场
    logger.info("成功进入训练场！")

    # 处理训练场界面交互
    logger.hr("Start train interaction", level=1)
    train_test.handle_train_interaction()
    logger.info("训练场交互处理完成！")

    # 滚动列表选择角色
    logger.hr("Select character", level=1)
    changed = train_test.character_selector.ensure_characters_selected()

    if changed:
        logger.info(" 角色选择已完成（进行了重选）")
    else:
        logger.info(" 角色选择已跳过（已正确）")

    # 开始战斗
    logger.hr("Start battle", level=1)
    train_test.combat_preparation_with_ui_click()

    # 


if __name__ == "__main__":
    main()
>>>>>>> Stashed changes
