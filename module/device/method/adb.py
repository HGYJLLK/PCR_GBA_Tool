"""
ADB 设备控制方法
"""

import re
import time
from functools import wraps
import cv2
import numpy as np

from module.config.server import DICT_PACKAGE_TO_ACTIVITY
from module.device.method.utils import (
    ImageTruncated,
    PackageNotInstalled,
    RETRY_TRIES,
    handle_adb_error,
    handle_unknown_host_service,
    retry_sleep,
    remove_prefix,
)
from module.exception import RequestHumanTakeover
from module.logger import logger


def retry(func):
    """
    重试装饰器
    """

    @wraps(func)
    def retry_wrapper(self, *args, **kwargs):
        """
        Args:
            self (Adb):
        """
        init = None
        for i in range(RETRY_TRIES):
            try:
                if callable(init):
                    time.sleep(retry_sleep(i))
                    init()
                return func(self, *args, **kwargs)
            # 无法处理的错误
            except RequestHumanTakeover:
                break
            # 连接重置错误
            except ConnectionResetError as e:
                logger.error(e)

                def init():
                    self.adb_reconnect()

            # ADB错误
            except Exception as e:
                error_str = str(e)
                if "AdbError" in type(e).__name__:
                    if handle_adb_error(e):

                        def init():
                            self.adb_reconnect()

                    elif handle_unknown_host_service(e):

                        def init():
                            self.adb_start_server()
                            self.adb_reconnect()

                    else:
                        break
                # 包未安装
                elif isinstance(e, PackageNotInstalled):
                    logger.error(e)

                    def init():
                        self.detect_package()

                # 图像截断
                elif isinstance(e, ImageTruncated):
                    logger.error(e)

                    def init():
                        pass

                # 未知错误
                else:
                    logger.exception(e)

                    def init():
                        pass

        logger.critical(f"Retry {func.__name__}() failed")
        raise RequestHumanTakeover

    return retry_wrapper


class Adb:
    """
    ADB 设备控制类
    """

    def __init__(self):
        self.adb = None
        self.serial = None
        self.package = None

    def adb_shell(self, cmd):
        """
        执行 ADB shell 命令
        Args:
            cmd (list): 命令列表
        Returns:
            str: 命令输出
        """
        raise NotImplementedError

    def adb_reconnect(self):
        """重新连接 ADB"""
        raise NotImplementedError

    def adb_start_server(self):
        """启动 ADB 服务器"""
        raise NotImplementedError

    def detect_package(self):
        """检测游戏包名"""
        raise NotImplementedError

    @retry
    def _app_start_adb_am(self, package_name, activity_name, allow_failure=False):
        """
        使用 Activity Manager 启动应用
        Args:
            package_name (str): 包名
            activity_name (str): Activity 名称
            allow_failure (bool): 是否允许失败
        Returns:
            bool: 是否成功
        """
        if not package_name:
            package_name = self.package
        if not activity_name:
            activity_name = DICT_PACKAGE_TO_ACTIVITY.get(package_name)

        if not activity_name:
            # dumpsys 获取 Activity 名称
            logger.info("Activity name not found, trying to discover from dumpsys")
            try:
                result = self.adb_shell(["dumpsys", "package", package_name])
                # 匹配 MAIN/LAUNCHER activity
                match = re.search(
                    r'android\.intent\.action\.MAIN:\s+\w+ ([\w.\/]+) filter \w+\s+.*\s+Category: "android\.intent\.category\.LAUNCHER"',
                    result,
                    re.DOTALL,
                )
                if match:
                    activity_name = match.group(1)
                    logger.info(f"Discovered activity: {activity_name}")
                else:
                    logger.warning("Failed to discover activity name")
                    if not allow_failure:
                        raise PackageNotInstalled(
                            f"Package {package_name} not installed or no launcher activity found"
                        )
                    return False
            except Exception as e:
                logger.error(f"Failed to get activity name: {e}")
                if not allow_failure:
                    raise PackageNotInstalled(f"Package {package_name} not installed")
                return False

        # 启动应用
        logger.info(f"Starting app via AM: {package_name}/{activity_name}")
        result = self.adb_shell(
            [
                "am",
                "start",
                "-a",
                "android.intent.action.MAIN",
                "-c",
                "android.intent.category.LAUNCHER",
                "-n",
                f"{package_name}/{activity_name}",
            ]
        )

        # 检查启动结果
        if "Starting: Intent" in result:
            logger.info("App started successfully")
            return True
        elif "Warning: Activity not started" in result:
            logger.info("App already running")
            return True
        elif "Error: Activity class" in result and "does not exist" in result:
            logger.error("Activity does not exist")
            if not allow_failure:
                raise PackageNotInstalled(f"Activity {activity_name} not found")
            return False
        elif "Permission Denial" in result:
            logger.error("Permission denied")
            return False
        else:
            logger.warning(f"Unknown result: {result}")
            return False

    @retry
    def _app_start_adb_monkey(self, package_name, allow_failure=False):
        """
        Monkey 启动应用
        Args:
            package_name (str): 包名
            allow_failure (bool): 是否允许失败
        Returns:
            bool: 是否成功
        """
        if not package_name:
            package_name = self.package

        logger.info(f"Starting app via Monkey: {package_name}")
        result = self.adb_shell(
            [
                "monkey",
                "-p",
                package_name,
                "-c",
                "android.intent.category.LAUNCHER",
                "--pct-syskeys",
                "0",
                "1",
            ]
        )

        # 检查启动结果
        if "Events injected: 1" in result:
            logger.info("App started successfully via Monkey")
            return True
        elif "No activities found" in result:
            logger.error("No activities found")
            if not allow_failure:
                raise PackageNotInstalled(f"Package {package_name} not installed")
            return False
        elif "inaccessible" in result:
            logger.error("Monkey binary not accessible")
            return False
        else:
            logger.warning(f"Unknown result: {result}")
            return False

    def app_start_adb(self, package_name=None, activity_name=None, allow_failure=False):
        """
        启动应用（AM → Monkey → AM）
        Args:
            package_name (str): 包名，None 则使用 self.package
            activity_name (str): Activity 名称，None 则从 DICT_PACKAGE_TO_ACTIVITY 获取
            allow_failure (bool): 是否允许失败
        Returns:
            bool: 是否成功
        Raises:
            PackageNotInstalled: 包未安装
        """
        if not package_name:
            package_name = self.package
        if not activity_name:
            activity_name = DICT_PACKAGE_TO_ACTIVITY.get(package_name)

        # Activity Manager
        if activity_name:
            if self._app_start_adb_am(package_name, activity_name, allow_failure):
                return True

        # Monkey
        if self._app_start_adb_monkey(package_name, allow_failure):
            return True

        # Activity Manager
        if self._app_start_adb_am(package_name, activity_name, allow_failure):
            return True

        logger.error("app_start_adb: All trials failed")
        return False

    @retry
    def app_stop_adb(self, package_name=None):
        """
        停止应用
        Args:
            package_name (str): 包名
        """
        if not package_name:
            package_name = self.package
        logger.info(f"Stopping app: {package_name}")
        self.adb_shell(["am", "force-stop", package_name])

    @retry
    def app_current_adb(self) -> str:
        """
        获取当前运行的应用包名
        Returns:
            str: 包名
        """
        _focusedRE = re.compile(
            r"mCurrentFocus=Window{.*\s+(?P<package>[^\s]+)/(?P<activity>[^\s]+)\}"
        )
        result = self.adb_shell(["dumpsys", "window", "windows"])
        m = _focusedRE.search(result)
        if m:
            return m.group("package")

        _activityRE = re.compile(
            r"ACTIVITY (?P<package>[^\s]+)/(?P<activity>[^/\s]+) \w+ pid=(?P<pid>\d+)"
        )
        activity_output = self.adb_shell(["dumpsys", "activity", "top"])
        ms = _activityRE.finditer(activity_output)
        ret = None
        for m in ms:
            ret = m.group("package")
        if ret:
            return ret

        # 全失败
        raise OSError("Couldn't get focused app")

    # 换行符处理方式
    __screenshot_method = [0, 1, 2]
    __screenshot_method_fixed = [0, 1, 2]

    @staticmethod
    def __load_screenshot(screenshot, method):
        """
        加载并解码截图数据
        Args:
            screenshot (bytes): 截图原始数据
            method (int): 换行符处理方法
                0: 不处理
                1: 替换 \\r\\n 为 \\n
                2: 替换 \\r\\r\\n 为 \\n
        Returns:
            np.ndarray: RGB格式的图像数组
        """
        from module.exception import ScriptError

        if method == 0:
            pass
        elif method == 1:
            screenshot = screenshot.replace(b"\r\n", b"\n")
        elif method == 2:
            screenshot = screenshot.replace(b"\r\r\n", b"\n")
        else:
            raise ScriptError(f"Unknown method to load screenshots: {method}")

        # 处理 VMOS Pro 兼容性问题
        screenshot = remove_prefix(screenshot, b"long long=8 fun*=10\n")

        # 解码PNG数据
        image = np.frombuffer(screenshot, np.uint8)
        if image is None:
            raise ImageTruncated("Empty image after reading from buffer")

        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        if image is None:
            raise ImageTruncated("Empty image after cv2.imdecode")

        # 转换BGR到RGB
        cv2.cvtColor(image, cv2.COLOR_BGR2RGB, dst=image)
        if image is None:
            raise ImageTruncated("Empty image after cv2.cvtColor")

        return image

    def __process_screenshot(self, screenshot):
        """
        不同的换行符处理截图数据
        Args:
            screenshot (bytes): 截图原始数据
        Returns:
            np.ndarray: RGB格式的图像数组
        """
        for method in self.__screenshot_method_fixed:
            try:
                result = self.__load_screenshot(screenshot, method=method)
                self.__screenshot_method_fixed = [method] + self.__screenshot_method
                return result
            except (OSError, ImageTruncated):
                continue

        # 重置方法列表
        self.__screenshot_method_fixed = self.__screenshot_method
        if len(screenshot) < 500:
            logger.warning(f"Unexpected screenshot: {screenshot}")
        raise OSError(f"cannot load screenshot")

    @retry
    def screenshot_adb(self):
        """
        使用 ADB shell screencap -p 命令截图
        Returns:
            np.ndarray: RGB格式的图像数组
        """
        data = self.adb_shell(["screencap", "-p"], stream=True)

        if len(data) < 500:
            logger.warning(f"Unexpected screenshot: {data}")

        return self.__process_screenshot(data)
