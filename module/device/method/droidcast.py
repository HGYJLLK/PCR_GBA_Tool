"""
DroidCast 截图方法
"""

import time
import typing as t
from functools import wraps

import cv2
import numpy as np
import requests
from adbutils.errors import AdbError

from module.base.decorator import cached_property, del_cached_property
from module.base.timer import Timer
from module.device.method.uiautomator_2 import ProcessInfo, Uiautomator2
from module.device.method.utils import (
    ImageTruncated,
    PackageNotInstalled,
    RETRY_TRIES,
    handle_adb_error,
    handle_unknown_host_service,
    retry_sleep,
)
from module.exception import RequestHumanTakeover
from module.logger import logger


class DroidCastVersionIncompatible(Exception):
    """DroidCast版本不兼容异常"""

    pass


def retry(func):
    """重试装饰器"""

    @wraps(func)
    def retry_wrapper(self, *args, **kwargs):
        """
        Args:
            self (DroidCast):
        """
        init = None
        for _ in range(RETRY_TRIES):
            try:
                if callable(init):
                    time.sleep(retry_sleep(_))
                    init()
                return func(self, *args, **kwargs)
            # Can't handle
            except RequestHumanTakeover:
                break
            # When adb server was killed
            except ConnectionResetError as e:
                logger.error(e)

                def init():
                    self.adb_reconnect()

            # AdbError
            except AdbError as e:
                if handle_adb_error(e):

                    def init():
                        self.adb_reconnect()

                elif handle_unknown_host_service(e):

                    def init():
                        self.adb_start_server()
                        self.adb_reconnect()

                else:
                    break
            # Package not installed
            except PackageNotInstalled as e:
                logger.error(e)

                def init():
                    self.detect_package()

            # DroidCast not running
            # requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
            # ReadTimeout: HTTPConnectionPool(host='127.0.0.1', port=20482): Read timed out. (read timeout=3)
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
            ) as e:
                logger.error(e)

                def init():
                    self.droidcast_init()

            # DroidCastVersionIncompatible
            except DroidCastVersionIncompatible as e:
                logger.error(e)

                def init():
                    self.droidcast_init()

            # ImageTruncated
            except ImageTruncated as e:
                logger.error(e)

                def init():
                    pass

            # Unknown
            except Exception as e:
                logger.exception(e)

                def init():
                    pass

        logger.critical(f"Retry {func.__name__}() failed")
        raise RequestHumanTakeover

    return retry_wrapper


class DroidCast(Uiautomator2):
    """
    DroidCast截图实现
    - DroidCast: 标准版本，返回PNG图片 (https://github.com/rayworks/DroidCast)
    - DroidCast_raw: 优化版本，返回RGB565原始数据 (https://github.com/Torther/DroidCastS)
    """

    _droidcast_port: int = 0
    droidcast_width: int = 0
    droidcast_height: int = 0

    @cached_property
    def droidcast_session(self):
        """创建HTTP会话并设置ADB端口转发"""
        session = requests.Session()
        session.trust_env = False  # 忽略系统代理
        self._droidcast_port = self.adb_forward("tcp:53516")
        return session

    def droidcast_url(self, url="/preview"):
        """
        生成DroidCast URL (PNG版本)

        MuMu12 >= 3.5.6 支持自定义分辨率参数
        """
        if self.is_mumu_over_version_356:
            w, h = self.droidcast_width, self.droidcast_height
            if self.orientation == 0:
                return (
                    f"http://127.0.0.1:{self._droidcast_port}{url}?width={w}&height={h}"
                )
            elif self.orientation == 1:
                return (
                    f"http://127.0.0.1:{self._droidcast_port}{url}?width={h}&height={w}"
                )

        return f"http://127.0.0.1:{self._droidcast_port}{url}"

    def droidcast_raw_url(self, url="/screenshot"):
        """
        生成DroidCast_raw URL (RGB565版本)

        MuMu12 >= 3.5.6 支持自定义分辨率参数
        """
        if self.is_mumu_over_version_356:
            w, h = self.droidcast_width, self.droidcast_height
            if self.orientation == 0:
                return (
                    f"http://127.0.0.1:{self._droidcast_port}{url}?width={w}&height={h}"
                )
            elif self.orientation == 1:
                return (
                    f"http://127.0.0.1:{self._droidcast_port}{url}?width={h}&height={w}"
                )

        return f"http://127.0.0.1:{self._droidcast_port}{url}"

    def droidcast_init(self):
        """初始化DroidCast服务"""
        logger.hr("DroidCast init")
        self.droidcast_stop()
        self._droidcast_update_resolution()

        logger.info("Pushing DroidCast apk")
        self.adb_push(
            self.config.DROIDCAST_FILEPATH_LOCAL, self.config.DROIDCAST_FILEPATH_REMOTE
        )

        logger.info("Starting DroidCast apk")
        # DroidCast_raw-release-1.0.apk
        # CLASSPATH=/data/local/tmp/DroidCast_raw.apk app_process / ink.mol.droidcast_raw.Main > /dev/null
        resp = self.u2_shell_background(
            [
                "CLASSPATH=/data/local/tmp/DroidCast_raw.apk",
                "app_process",
                "/",
                "ink.mol.droidcast_raw.Main",
                ">",
                "/dev/null",
            ]
        )
        logger.info(resp)
        del_cached_property(self, "droidcast_session")
        _ = self.droidcast_session

        if self.config.DROIDCAST_VERSION == "DroidCast":
            logger.attr("DroidCast", self.droidcast_url())
            self.droidcast_wait_startup()
        elif self.config.DROIDCAST_VERSION == "DroidCast_raw":
            logger.attr("DroidCast_raw", self.droidcast_raw_url())
            self.droidcast_wait_startup()
        else:
            logger.error(f"Unknown DROIDCAST_VERSION: {self.config.DROIDCAST_VERSION}")

    def _droidcast_update_resolution(self):
        """更新DroidCast分辨率 (MuMu12 >= 3.5.6 专用)"""
        if self.is_mumu_over_version_356:
            logger.info("Update droidcast resolution")
            w, h = self.resolution_uiautomator2(cal_rotation=False)
            self.get_orientation()
            # 720, 1280
            # mumu12 > 3.5.6 is always a vertical device
            self.droidcast_width, self.droidcast_height = w, h
            logger.info(f"Droidcast resolution: {(w, h)}")

    @retry
    def screenshot_droidcast_raw(self):
        """使用DroidCast_raw获取RGB565格式截图"""
        self.config.DROIDCAST_VERSION = "DroidCast_raw"
        shape = (720, 1280)

        if self.is_mumu_over_version_356:
            if not self.droidcast_width or not self.droidcast_height:
                self._droidcast_update_resolution()
            if self.droidcast_height and self.droidcast_width:
                shape = (self.droidcast_height, self.droidcast_width)

        rotate = self.is_mumu_over_version_356 and self.orientation == 1

        image = self.droidcast_session.get(self.droidcast_raw_url(), timeout=3).content
        # DroidCast_raw returns a RGB565 bitmap

        try:
            arr = np.frombuffer(image, dtype=np.uint16)
            if rotate:
                arr = arr.reshape(shape)
                # arr = cv2.rotate(arr, cv2.ROTATE_90_CLOCKWISE)
                # A little bit faster?
                arr = cv2.transpose(arr)
                cv2.flip(arr, 1, dst=arr)
            else:
                arr = arr.reshape(shape)
        except ValueError as e:
            if len(image) < 500:
                logger.warning(f"Unexpected screenshot: {image}")
            # Try to load as `DroidCast`
            image_test = np.frombuffer(image, np.uint8)
            if image_test is not None:
                image_test = cv2.imdecode(image_test, cv2.IMREAD_COLOR)
                if image_test is not None:
                    raise DroidCastVersionIncompatible(
                        "Requesting screenshots from `DroidCast_raw` but server is `DroidCast`"
                    )
            # ValueError: cannot reshape array of size 0 into shape (720,1280)
            raise ImageTruncated(str(e))

        # Convert RGB565 to RGB888
        # https://blog.csdn.net/happy08god/article/details/10516871

        # The same as the code above but costs about 3~4ms instead of 10ms.
        # Note that cv2.convertScaleAbs is 5x fast as cv2.multiply, cv2.add is 8x fast as cv2.convertScaleAbs
        # Note that cv2.convertScaleAbs includes rounding
        r = cv2.bitwise_and(arr, 0b1111100000000000)
        r = cv2.convertScaleAbs(r, alpha=0.00390625)
        m = cv2.convertScaleAbs(r, alpha=0.03125)
        cv2.add(r, m, dst=r)

        g = cv2.bitwise_and(arr, 0b0000011111100000)
        g = cv2.convertScaleAbs(g, alpha=0.125)
        m = cv2.convertScaleAbs(g, alpha=0.015625, dst=m)
        cv2.add(g, m, dst=g)

        b = cv2.bitwise_and(arr, 0b0000000000011111)
        b = cv2.convertScaleAbs(b, alpha=8)
        m = cv2.convertScaleAbs(b, alpha=0.03125, dst=m)
        cv2.add(b, m, dst=b)

        image = cv2.merge([r, g, b])

        return image

    def droidcast_wait_startup(self):
        """等待DroidCast服务启动完成"""
        timeout = Timer(10).start()
        while 1:
            self.sleep(0.25)
            if timeout.reached():
                break

            try:
                resp = self.droidcast_session.get(self.droidcast_url("/"), timeout=3)
                # Route `/` is unavailable, but 404 means startup completed
                if resp.status_code == 404:
                    logger.attr("DroidCast", "online")
                    return True
            except requests.exceptions.ConnectionError:
                logger.attr("DroidCast", "offline")

        logger.warning("Wait DroidCast startup timeout, assume started")
        return False

    def droidcast_uninstall(self):
        """
        停止DroidCast进程并删除APK
        DroidCast未安装，只是通过JAVA类调用，卸载就是删除文件
        """
        self.droidcast_stop()
        logger.info("Removing DroidCast")
        self.adb_shell(["rm", self.config.DROIDCAST_FILEPATH_REMOTE])

    def _iter_droidcast_proc(self) -> t.Iterable[ProcessInfo]:
        """列出所有DroidCast进程"""
        processes = self.proc_list_uiautomator2()
        for proc in processes:
            if "com.rayworks.droidcast.Main" in proc.cmdline:
                yield proc
            if "com.torther.droidcasts.Main" in proc.cmdline:
                yield proc
            if "ink.mol.droidcast_raw.Main" in proc.cmdline:
                yield proc

    def droidcast_stop(self):
        """停止所有DroidCast进程"""
        logger.info("Stopping DroidCast")
        for proc in self._iter_droidcast_proc():
            logger.info(f"Kill pid={proc.pid}")
            self.adb_shell(["kill", "-s", 9, proc.pid])
