"""
设备类
"""

import collections
from datetime import datetime

from module.base.timer import Timer
from module.device.control import Control
from module.device.screenshot import Screenshot
from module.exception import (
    EmulatorNotRunningError,
    RequestHumanTakeover,
    GameStuckError,
    GameTooManyClickError,
    GameNotRunningError,
)
from module.logger import logger


class Device(Control, Screenshot):
    """
    设备类
    """

    _screen_size_checked = False
    detect_record = set()
    click_record = collections.deque(maxlen=15) # 记录最近的 15 次点击

    # 超时定时器
    stuck_timer = Timer(60, count=60)  # 60秒超时
    stuck_timer_long = Timer(300, count=300)  # 300秒长超时
    stuck_long_wait_list = []  # 需要长时间等待的按钮列表

    def __init__(self, config):
        """
        Args:
            config: 配置对象
        """
        # 连接设备
        for trial in range(4):
            try:
                # 按照 MRO 列表，调用下一个拥有 __init__ 方法的类的 __init__
                super().__init__(config)
                break
            except EmulatorNotRunningError:
                if trial >= 3:
                    logger.critical("Failed to start emulator after 3 trials")
                    raise RequestHumanTakeover("模拟器启动失败，请手动启动模拟器")
                else:
                    logger.warning(f"Emulator not running, trial {trial + 1}/4")

        logger.info("Device initialized successfully")

        # Early init for MaaTouch
        if (
            hasattr(config, "Emulator_ControlMethod")
            and config.Emulator_ControlMethod == "MaaTouch"
        ):
            logger.info("Early initializing MaaTouch")
            self.early_maatouch_init()

    def stuck_record_add(self, button):
        """
        添加防卡死检测记录

        Args:
            button: 按钮对象
        """
        self.detect_record.add(str(button))

    def stuck_record_clear(self):
        """
        清空卡死记录
        """
        self.detect_record = set()
        self.stuck_timer.reset()
        self.stuck_timer_long.reset()

    def stuck_record_check(self):
        """
        检查是否卡住超过60秒

        Raises:
            GameStuckError: 界面卡住超过60秒
            GameNotRunningError: 应用已挂掉
        """
        reached = self.stuck_timer.reached()
        reached_long = self.stuck_timer_long.reached()

        if not reached:
            return False

        # 检查是否有需要长时间等待的按钮
        if not reached_long:
            for button in self.stuck_long_wait_list:
                if button in self.detect_record:
                    return False

        logger.warning("Wait too long")
        logger.warning(f"Waiting for {self.detect_record}")
        self.stuck_record_clear()

        # 检查应用是否还在运行
        if self.app_is_running():
            raise GameStuckError(f"Wait too long")
        else:
            raise GameNotRunningError("Game died")

    def click_record_add(self, button):
        """
        添加点击记录

        Args:
            button: 按钮对象
        """
        self.click_record.append(str(button))

    def click_record_clear(self):
        """
        清空点击记录
        """
        self.click_record.clear()

    def click_record_check(self):
        """
        检查是否陷入无限点击循环

        Raises:
            GameTooManyClickError: 点击同一按钮12次或两按钮互点6次
        """
        count = collections.Counter(self.click_record).most_common(2)

        # 点击同一按钮12次
        if count and count[0][1] >= 12:
            logger.warning(f"Too many click for a button: {count[0][0]}")
            logger.warning(
                f"History click: {[str(prev) for prev in self.click_record]}"
            )
            self.click_record_clear()
            raise GameTooManyClickError(f"Too many click for a button: {count[0][0]}")

        # 两按钮互相点击各6次
        if len(count) >= 2 and count[0][1] >= 6 and count[1][1] >= 6:
            logger.warning(
                f"Too many click between 2 buttons: {count[0][0]}, {count[1][0]}"
            )
            logger.warning(
                f"History click: {[str(prev) for prev in self.click_record]}"
            )
            self.click_record_clear()
            raise GameTooManyClickError(
                f"Too many click between 2 buttons: {count[0][0]}, {count[1][0]}"
            )

    def disable_stuck_detection(self):
        """
        Disable stuck detection and its handler. Usually uses in semi auto and debugging.
        """
        logger.info('Disable stuck detection')

        def empty_function(*arg, **kwargs):
            return False

        self.click_record_check = empty_function
        self.stuck_record_check = empty_function

    def handle_control_check(self, button):
        self.stuck_record_clear()
        self.click_record_add(button)
        self.click_record_check()