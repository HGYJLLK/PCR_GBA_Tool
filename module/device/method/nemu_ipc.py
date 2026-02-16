"""
MuMu12 模拟器 nemu IPC 截图
通过共享内存直接读取模拟器显存
"""

import ctypes
import os
import sys
import contextlib

import cv2
import numpy as np

from module.logger import logger


class NemuIpcIncompatible(Exception):
    """MuMu 版本不兼容"""

    pass


class NemuIpcError(Exception):
    """IPC 错误"""

    pass


@contextlib.contextmanager
def suppress_stderr():
    """临时抑制 stderr 输出（用于抑制 DLL 的 'screencap fail' 消息）"""
    if sys.platform == "win32":
        # 重定向 stderr 到 NUL
        import msvcrt

        stderr_fd = sys.stderr.fileno()
        old_stderr = os.dup(stderr_fd)
        devnull = os.open("NUL", os.O_WRONLY)
        os.dup2(devnull, stderr_fd)
        try:
            yield
        finally:
            os.dup2(old_stderr, stderr_fd)
            os.close(old_stderr)
            os.close(devnull)
    else:
        yield


class CaptureStd:
    """
    捕获 stdout 和 stderr（包括 C 库的输出）
    https://stackoverflow.com/questions/5081657/how-do-i-prevent-a-c-shared-library-to-print-on-stdout-in-python
    """

    def __init__(self):
        self.stdout = b""
        self.stderr = b""

    def _redirect_stdout(self, to):
        sys.stdout.close()
        os.dup2(to, self.fdout)
        sys.stdout = os.fdopen(self.fdout, "w")

    def _redirect_stderr(self, to):
        sys.stderr.close()
        os.dup2(to, self.fderr)
        sys.stderr = os.fdopen(self.fderr, "w")

    def __enter__(self):
        self.fdout = sys.stdout.fileno()
        self.fderr = sys.stderr.fileno()
        self.reader_out, self.writer_out = os.pipe()
        self.reader_err, self.writer_err = os.pipe()
        self.old_stdout = os.dup(self.fdout)
        self.old_stderr = os.dup(self.fderr)

        file_out = os.fdopen(self.writer_out, "w")
        file_err = os.fdopen(self.writer_err, "w")
        self._redirect_stdout(to=file_out.fileno())
        self._redirect_stderr(to=file_err.fileno())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._redirect_stdout(to=self.old_stdout)
        self._redirect_stderr(to=self.old_stderr)
        os.close(self.old_stdout)
        os.close(self.old_stderr)

        self.stdout = self._recvall(self.reader_out)
        self.stderr = self._recvall(self.reader_err)
        os.close(self.reader_out)
        os.close(self.reader_err)

    @staticmethod
    def _recvall(reader, length=1024) -> bytes:
        fragments = []
        while True:
            chunk = os.read(reader, length)
            if chunk:
                fragments.append(chunk)
            else:
                break
        return b"".join(fragments)


class CaptureNemuIpc(CaptureStd):
    """捕获 nemu IPC 输出并检查错误"""

    instance = None

    def is_capturing(self):
        cls = self.__class__
        return isinstance(cls.instance, cls) and cls.instance != self

    def __enter__(self):
        if self.is_capturing():
            return self
        super().__enter__()
        CaptureNemuIpc.instance = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_capturing():
            return
        CaptureNemuIpc.instance = None
        super().__exit__(exc_type, exc_val, exc_tb)
        self._check_stderr()

    def _check_stderr(self):
        if not self.stderr:
            return

        logger.warning(f"NemuIpc stderr: {self.stderr}")

        # MuMu12 版本过低
        if b"error: 1783" in self.stderr or b"error: 1745" in self.stderr:
            raise NemuIpcIncompatible(
                "NemuIpc 需要 MuMu12 版本 >= 3.8.13，请升级模拟器"
            )
        # 连接 ID 错误
        if b"cannot find rpc connection" in self.stderr:
            raise NemuIpcError(self.stderr)
        # 模拟器进程挂掉
        if b"error: 1722" in self.stderr or b"error: 1726" in self.stderr:
            raise NemuIpcError("模拟器实例可能已关闭")


class NemuIpcImpl:
    """
    MuMu12 nemu IPC 实现

    Args:
        nemu_folder: MuMu12 安装路径，如 C:/Program Files/Netease/MuMu Player 12
        instance_id: 模拟器实例 ID，从 0 开始
        display_id: 显示 ID，通常为 0
    """

    def __init__(self, nemu_folder: str, instance_id: int = 0, display_id: int = 0):
        self.nemu_folder = nemu_folder
        self.instance_id = instance_id
        self.display_id = display_id

        # 尝试从多个路径加载 DLL
        dll_paths = [
            # MuMu12 标准路径
            os.path.abspath(
                os.path.join(nemu_folder, "./shell/sdk/external_renderer_ipc.dll")
            ),
            # MuMu12 新版路径
            os.path.abspath(
                os.path.join(nemu_folder, "./nx_main/sdk/external_renderer_ipc.dll")
            ),
            # MuMu12 5.0+
            os.path.abspath(
                os.path.join(
                    nemu_folder, "./nx_device/12.0/shell/sdk/external_renderer_ipc.dll"
                )
            ),
        ]

        self.lib = None
        self.dll_path = None
        for dll_path in dll_paths:
            if not os.path.exists(dll_path):
                continue
            try:
                self.lib = ctypes.CDLL(dll_path)
                self.dll_path = dll_path
                break
            except OSError as e:
                logger.warning(f"DLL 存在但无法加载: {dll_path}, 错误: {e}")
                continue

        if self.lib is None:
            raise NemuIpcIncompatible(
                f"未找到 external_renderer_ipc.dll，请确认 MuMu12 版本 >= 3.8.13\n"
                f"搜索路径: {dll_paths}"
            )

        logger.info(
            f"NemuIpc 初始化: folder={nemu_folder}, dll={self.dll_path}, "
            f"instance_id={instance_id}, display_id={display_id}"
        )

        self.connect_id = 0
        self.width = 0
        self.height = 0

    def connect(self):
        """连接到模拟器"""
        if self.connect_id > 0:
            return

        # nemu_connect 接受字符串路径和实例 ID
        # 抑制 DLL 输出（如 "nemu_connect instance_name", "connect not same day"）
        with suppress_stderr():
            connect_id = self.lib.nemu_connect(self.nemu_folder, self.instance_id)
        logger.info(f"nemu_connect 返回: {connect_id}")

        if connect_id == 0:
            raise NemuIpcError(
                f"连接失败，请确认:\n"
                f"  1. 模拟器正在运行\n"
                f"  2. 路径正确: {self.nemu_folder}\n"
                f"  3. 实例 ID 正确: {self.instance_id}"
            )

        self.connect_id = connect_id
        logger.info(f"NemuIpc 已连接: connect_id={self.connect_id}")

    def disconnect(self):
        """断开连接"""
        if self.connect_id == 0:
            return

        self.lib.nemu_disconnect(self.connect_id)
        logger.info(f"NemuIpc 已断开: connect_id={self.connect_id}")
        self.connect_id = 0

    def reconnect(self):
        """重新连接"""
        self.disconnect()
        self.connect()

    def get_resolution(self):
        """获取模拟器分辨率"""
        if self.connect_id == 0:
            self.connect()

        width_ptr = ctypes.pointer(ctypes.c_int(0))
        height_ptr = ctypes.pointer(ctypes.c_int(0))
        nullptr = ctypes.POINTER(ctypes.c_int)()

        # 抑制 DLL 的 "screencap fail" 输出
        with suppress_stderr():
            self.lib.nemu_capture_display(
                self.connect_id, self.display_id, 0, width_ptr, height_ptr, nullptr
            )

        self.width = width_ptr.contents.value
        self.height = height_ptr.contents.value
        return self.width, self.height

    def screenshot(self) -> np.ndarray:
        """
        截图

        Returns:
            np.ndarray: BGR 格式图像
        """
        if self.connect_id == 0:
            self.connect()
        if self.width == 0 or self.height == 0:
            self.get_resolution()

        width_ptr = ctypes.pointer(ctypes.c_int(self.width))
        height_ptr = ctypes.pointer(ctypes.c_int(self.height))
        length = self.width * self.height * 4  # RGBA
        pixels_pointer = ctypes.pointer((ctypes.c_ubyte * length)())

        # 抑制 DLL 的 "screencap fail" 输出
        with suppress_stderr():
            self.lib.nemu_capture_display(
                self.connect_id,
                self.display_id,
                length,
                width_ptr,
                height_ptr,
                pixels_pointer,
            )

        # 转换为 numpy 数组
        image = np.ctypeslib.as_array(pixels_pointer.contents).reshape(
            (self.height, self.width, 4)
        )

        # RGBA -> BGR，并垂直翻转
        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        cv2.flip(image, 0, dst=image)

        return image

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @staticmethod
    def serial_to_id(serial: str) -> int:
        """
        从设备 serial 推断实例 ID

        例如:
            "127.0.0.1:16384" -> 0
            "127.0.0.1:16416" -> 1

        Returns:
            int: instance_id，失败返回 None
        """
        try:
            port = int(serial.split(":")[1])
        except (IndexError, ValueError):
            return None
        # MuMu12 端口规则: 16384 + instance_id * 32
        index, offset = divmod(port - 16384 + 16, 32)
        offset -= 16
        if 0 <= index < 32 and offset in [-2, -1, 0, 1, 2]:
            return index
        return None


# 全局实例缓存
_nemu_ipc_instance = None


def get_nemu_ipc(
    nemu_folder: str = None, instance_id: int = 0, serial: str = None
) -> NemuIpcImpl:
    """
    获取 NemuIpc 实例

    Args:
        nemu_folder: MuMu12 安装路径，默认自动搜索
        instance_id: 实例 ID，如果提供 serial 会自动推断
        serial: 设备 serial，如 "127.0.0.1:16384"
    """
    global _nemu_ipc_instance

    # 从 serial 推断 instance_id
    if serial and instance_id == 0:
        inferred_id = NemuIpcImpl.serial_to_id(serial)
        if inferred_id is not None:
            instance_id = inferred_id

    # 自动搜索 MuMu 安装路径
    if nemu_folder is None:
        search_paths = [
            r"C:\Program Files\Netease\MuMu Player 12",
            r"D:\Program Files\Netease\MuMu Player 12",
            r"E:\Program Files\Netease\MuMu Player 12",
            r"C:\Program Files\Netease\MuMuPlayer-12.0",
            r"D:\Program Files\Netease\MuMuPlayer-12.0",
        ]
        for path in search_paths:
            if os.path.exists(path):
                nemu_folder = path
                break

    if nemu_folder is None:
        raise NemuIpcIncompatible("未找到 MuMu12 安装路径")

    # 复用或创建实例
    if _nemu_ipc_instance is None or _nemu_ipc_instance.instance_id != instance_id:
        if _nemu_ipc_instance is not None:
            _nemu_ipc_instance.disconnect()
        _nemu_ipc_instance = NemuIpcImpl(nemu_folder, instance_id)
        _nemu_ipc_instance.connect()

    return _nemu_ipc_instance
