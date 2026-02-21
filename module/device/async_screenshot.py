"""
异步截图模块 - 在后台线程持续截图，供战斗监控等实时处理场景使用
"""

import time
from threading import Thread, Lock


class AsyncScreenshotBase:
    """
    异步截图基类
    子类实现 _capture_single() 返回完整截图 numpy 数组
    """

    def __init__(self, crop_area=None):
        """
        Args:
            crop_area: 截图后裁剪区域 (x1, y1, x2, y2)，None 表示不裁剪
        """
        self.crop_area = crop_area
        self.latest_image = None       # 完整截图
        self.latest_cropped = None     # 裁剪后的图像
        self.screenshot_time = 0.0    # 上次截图耗时(秒)
        self.lock = Lock()
        self.running = False
        self.thread = None

    def start(self):
        """启动后台截图线程"""
        self.running = True
        self.thread = Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止后台截图线程"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _capture_single(self):
        """
        执行一次截图，返回完整图像。子类必须实现。

        Returns:
            np.ndarray: BGR/RGB 图像
        """
        raise NotImplementedError

    def _capture_loop(self):
        while self.running:
            t0 = time.time()
            try:
                image = self._capture_single()
                if self.crop_area:
                    x1, y1, x2, y2 = self.crop_area
                    cropped = image[y1:y2, x1:x2].copy()
                else:
                    cropped = image
                with self.lock:
                    self.latest_image = image
                    self.latest_cropped = cropped
                    self.screenshot_time = time.time() - t0
            except Exception:
                pass

    def get_image(self):
        """
        获取裁剪后的图像

        Returns:
            (np.ndarray | None, float): (裁剪图像, 截图耗时)
        """
        with self.lock:
            return self.latest_cropped, self.screenshot_time

    def get_full_image(self):
        """
        获取完整截图

        Returns:
            np.ndarray | None
        """
        with self.lock:
            return self.latest_image


class AsyncScreenshotNemuIpc(AsyncScreenshotBase):
    """异步截图 - NemuIpc"""

    def __init__(self, nemu_ipc, crop_area=None):
        """
        Args:
            nemu_ipc: NemuIpc 实例
            crop_area: 截图后裁剪区域 (x1, y1, x2, y2)
        """
        super().__init__(crop_area=crop_area)
        self.nemu_ipc = nemu_ipc

    def _capture_single(self):
        return self.nemu_ipc.screenshot()


class AsyncScreenshotDroidCast(AsyncScreenshotBase):
    """异步截图 - DroidCast"""

    def __init__(self, device, crop_area=None):
        """
        Args:
            device: Device 实例
            crop_area: 截图后裁剪区域 (x1, y1, x2, y2)
        """
        super().__init__(crop_area=crop_area)
        self.device = device

    def _capture_single(self):
        return self.device.screenshot_droidcast_raw()


def create_async_screenshot(device, mode="NemuIpc", crop_area=None):
    """
    工厂函数：根据模式创建对应的异步截图实例。

    Args:
        device: Device 实例（DroidCast 模式 | 获取 serial）
        mode (str): "NemuIpc" 或 "DroidCast"
        crop_area (tuple | None): 截图后裁剪区域 (x1, y1, x2, y2)

    Returns:
        AsyncScreenshotBase 子类实例
    """
    if mode == "DroidCast":
        device.droidcast_init()
        return AsyncScreenshotDroidCast(device, crop_area=crop_area)
    else:
        from module.device.method.nemu_ipc import get_nemu_ipc
        nemu = get_nemu_ipc(serial=device.serial)
        return AsyncScreenshotNemuIpc(nemu, crop_area=crop_area)
