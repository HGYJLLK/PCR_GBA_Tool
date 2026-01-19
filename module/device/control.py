"""
应用控制模块
"""

import time
import numpy as np

from module.base.decorator import cached_property
from module.base.timer import Timer
from module.base.utils import random_rectangle_point, ensure_int, ensure_time, point2str
from module.device.method.adb import retry
from module.device.method.droidcast import DroidCast
from module.device.method.maatouch import MaaTouch
from module.logger import logger


class Control(MaaTouch, DroidCast):
    """
    应用控制类
    """

    def handle_control_check(self, button):
        """
        Args:
            button: Button对象或操作名称
        """
        # Will be overridden in Device
        pass

    def app_current(self) -> str:
        """
        获取当前运行的应用包名
        Returns:
            str: 包名
        """
        package = self.app_current_adb()
        package = package.strip(" \t\r\n")
        return package

    def app_is_running(self) -> bool:
        """
        检查游戏是否正在运行
        Returns:
            bool: 是否运行
        """
        package = self.app_current()
        logger.attr("Current_package", package)
        return package == self.package

    def app_start(self):
        """
        启动应用
        """
        logger.info(f"App start: {self.package}")
        self.app_start_adb()

    def app_stop(self):
        """
        停止应用
        """
        logger.info(f"App stop: {self.package}")
        self.app_stop_adb()

    @cached_property
    def click_methods(self):
        """
        可用的点击方法映射
        根据配置 Emulator.ControlMethod 选择点击方式

        Returns:
            dict: {方法名: 方法函数}
        """
        return {
            "ADB": self.click_adb,
            "MaaTouch": self.click_maatouch,
        }

    @retry
    def click_adb(self, x, y):
        """
        ADB 方式点击

        Args:
            x (int): X坐标
            y (int): Y坐标
        """
        start = time.time()
        self.adb_shell(["input", "tap", str(x), str(y)])
        elapsed = time.time() - start
        if elapsed < 0.05:
            time.sleep(0.05 - elapsed)

    def click(self, button, control_check=True):
        """
        点击按钮

        Args:
            button (button.Button): Button 对象实例
            control_check (bool): 是否执行控制检查（默认 True）
        """
        if control_check:
            self.handle_control_check(button)
        x, y = random_rectangle_point(button.button)
        x, y = ensure_int(x, y)
        logger.info("Click %s @ %s" % (point2str(x, y), button))
        method = self.click_methods.get(
            self.config.Emulator_ControlMethod, self.click_adb # 默认使用 ADB
        )
        method(x, y)

    def multi_click(self, button, n, interval=(0.1, 0.2)):
        """
        多次点击同一按钮

        Args:
            button (button.Button): Button 对象实例
            n (int): 点击次数
            interval (float, tuple): 点击间隔（秒），可以是单个值或范围
        """
        # 先做一次检查，后续连续点击时不做检查（提高效率）
        self.handle_control_check(button)
        click_timer = Timer(0.1)
        for _ in range(n):
            remain = ensure_time(interval) - click_timer.current_time()
            if remain > 0:
                self.sleep(remain)
            click_timer.reset()

            self.click(button, control_check=False)

    def long_click(self, button, duration=(1, 1.2)):
        """
        长按按钮

        Args:
            button (button.Button): Button 对象实例
            duration (int, float, tuple): 长按持续时间（秒）
        """
        self.handle_control_check(button)
        x, y = random_rectangle_point(button.button)
        x, y = ensure_int(x, y)
        duration = ensure_time(duration)
        logger.info("Click %s @ %s, %s" % (point2str(x, y), button, duration))
        method = self.config.Emulator_ControlMethod
        if method == "MaaTouch":
            # 使用 MaaTouch 原生长按指令 (down -> wait -> up)
            self.long_click_maatouch(x, y, duration)
        else:
            # ADB 方式使用 swipe 实现长按
            self.swipe_adb((x, y), (x, y), duration) # 坐标是从 (x, y) 滑动到 (x, y)，“原地不动”

    def swipe(self, p1, p2, duration=(0.1, 0.2), name="SWIPE", distance_check=True):
        """
        滑动操作

        Args:
            p1 (tuple): 起点坐标 (x, y)
            p2 (tuple): 终点坐标 (x, y)
            duration (float, tuple): 滑动持续时间（秒），可以是单个值或范围
            name (str): 操作名称，用于日志
            distance_check (bool): 是否检查滑动距离

        Examples:
            # 基本滑动
            device.swipe((100, 100), (100, 500))

            # 指定持续时间范围
            device.swipe((100, 100), (100, 500), duration=(0.2, 0.3))
        """
        self.handle_control_check(name)
        p1, p2 = ensure_int(p1, p2)
        duration = ensure_time(duration)
        method = self.config.Emulator_ControlMethod

        # 日志输出
        if method == "MaaTouch":
            logger.info("Swipe %s -> %s" % (point2str(*p1), point2str(*p2)))
        else:
            logger.info(
                "Swipe %s -> %s, %s" % (point2str(*p1), point2str(*p2), duration)
            )

        # 距离检查
        if distance_check:
            if np.linalg.norm(np.subtract(p1, p2)) < 10:
                # 滑动距离太短会被识别为点击
                logger.info("Swipe distance < 10px, dropped")
                return

        # 根据控制方法选择滑动方式
        if method == "MaaTouch":
            self.swipe_maatouch(p1, p2)
        else:
            # ADB 方式需要更慢的速度
            duration *= 2.5
            self.swipe_adb(p1, p2, duration=duration)

    @retry
    def swipe_adb(self, p1, p2, duration=0.1):
        """
        ADB 方式滑动

        Args:
            p1 (tuple): 起点坐标 (x, y)
            p2 (tuple): 终点坐标 (x, y)
            duration (float): 持续时间（秒）
        """
        duration = int(duration * 1000)
        self.adb_shell(
            [
                "input",
                "swipe",
                str(p1[0]),
                str(p1[1]),
                str(p2[0]),
                str(p2[1]),
                str(duration),
            ]
        )
