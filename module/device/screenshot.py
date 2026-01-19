"""
截图模块
"""

import os
import numpy as np
import time

from module.base.decorator import cached_property
from module.base.utils import save_image
from module.device.method.adb import Adb
from module.device.method.droidcast import DroidCast
from module.exception import ScriptError
from module.logger import logger


class Screenshot(Adb):
    """
    截图类
    """

    image: np.ndarray
    _last_save_time = {}

    @cached_property
    def screenshot_methods(self):
        """
        截图方法映射表

        Returns:
            dict: 方法名 -> 方法函数的映射
        """
        return {
            "ADB": self.screenshot_adb,
            "DroidCast_raw": self.screenshot_droidcast_raw,
        }

    @cached_property
    def screenshot_method_override(self) -> str:
        """
        截图方法覆盖

        Returns:
            str: 空字符串表示使用配置文件中的方法
        """
        return ""

    def screenshot(self):
        """
        截图

        Returns:
            np.ndarray: RGB格式的图像数组

        Raises:
            GameStuckError: 界面卡住超过60秒
            GameNotRunningError: 应用已挂掉
        """
        # 检查是否卡住
        self.stuck_record_check()

        # 截图方法
        if self.screenshot_method_override:
            method_name = self.screenshot_method_override
        else:
            method_name = self.config.Emulator_ScreenshotMethod

        # 获取对应的截图方法
        method = self.screenshot_methods.get(method_name)
        if method is None:
            logger.warning(f"Unknown screenshot method: {method_name}, fallback to ADB")
            method = self.screenshot_adb

        # 执行截图
        self.image = method()

        return self.image

    def save_screenshot(self, genre="items", interval=None, to_base_folder=False):
        """
        保存截图
        使用毫秒时间戳作为文件名

        Args:
            genre (str, optional): 截图类型/文件夹名
            interval (int, float): 两次保存之间的间隔秒数。间隔内的保存会被丢弃
            to_base_folder (bool): 是否保存到基础文件夹

        Returns:
            bool: 保存成功返回 True
        """
        now = time.time()
        if interval is None:
            # 使用配置文件中的默认间隔，如果没有则使用 1 秒
            interval = getattr(self.config, "SCREEN_SHOT_SAVE_INTERVAL", 1)

        if now - self._last_save_time.get(genre, 0) > interval:
            fmt = "png"
            file = "%s.%s" % (int(now * 1000), fmt)

            # 获取保存文件夹路径
            if to_base_folder:
                folder = getattr(
                    self.config, "SCREEN_SHOT_SAVE_FOLDER_BASE", "./screenshot"
                )
            else:
                folder = getattr(self.config, "SCREEN_SHOT_SAVE_FOLDER", "./screenshot")

            folder = os.path.join(folder, genre)
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)

            file = os.path.join(folder, file)
            self.image_save(file)
            self._last_save_time[genre] = now
            return True
        else:
            self._last_save_time[genre] = now
            return False

    def image_save(self, file=None):
        """
        保存当前截图

        Args:
            file (str): 文件路径，如果为 None 则使用时间戳作为文件名
        """
        if file is None:
            file = f"{int(time.time() * 1000)}.png"
        save_image(self.image, file)

    @property
    def has_cached_image(self):
        """
        判断是否已经有缓存截图，用于后续skip_first_screenshot跳过第一次截图的时候能否使用缓存截图
        """
        return hasattr(self, "image") and self.image is not None
