<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""
设备连接管理
"""

import re
import subprocess
import time
import random
import platform

import uiautomator2 as u2
from adbutils import AdbClient, AdbDevice, AdbTimeout, ForwardItem
from adbutils.errors import AdbError

from module.base.decorator import cached_property
from module.config.config import PriconneConfig
from module.config.server import VALID_PACKAGE, set_server
from module.device.method.adb import Adb
from module.device.method.utils import RETRY_TRIES, retry_sleep, possible_reasons
from module.exception import EmulatorNotRunningError, RequestHumanTakeover
from module.logger import logger
from module.base.utils import ensure_time


class AdbDeviceWithStatus(AdbDevice):
    """带状态的 ADB 设备"""

    def __init__(self, client: AdbClient, serial: str, status: str):
        self.status = status
        super().__init__(client, serial)

    def __str__(self):
        return f"AdbDevice({self.serial}, {self.status})"

    __repr__ = __str__

    def __bool__(self):
        return True

    @property
    def port(self) -> int:
        """获取设备端口"""
        try:
            return int(self.serial.split(":")[1])
        except (IndexError, ValueError):
            return 0

    @property
    def is_mumu12_family(self):
        """是否为 MuMu12 系列模拟器 (端口范围 16384-17408)"""
        return 16384 <= self.port <= 17408

    @property
    def is_mumu_family(self):
        """是否为 MuMu 系列模拟器"""
        return self.serial == "127.0.0.1:7555" or self.is_mumu12_family


class Connection(Adb):
    """
    设备连接类
    """

    config: PriconneConfig

    @staticmethod
    def _find_adb():
        """查找 adb 可执行文件"""
        import os
        import shutil

        # 优先使用 PATH 中的 adb
        adb_in_path = shutil.which("adb")
        if adb_in_path:
            return adb_in_path

        # 常见的 adb 路径
        possible_paths = [
            # MuMu12 模拟器
            r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
            r"D:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
            # MuMu 模拟器
            r"C:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
            # 雷电模拟器
            r"C:\leidian\LDPlayer9\adb.exe",
            # 搞机工具箱
            os.path.expanduser(r"~\Documents\搞机工具箱10.1.0\搞机工具箱10.1.0\adb.exe"),
            # Android SDK
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found adb at: {path}")
                return path

        # 默认使用 adb，期望在 PATH 中
        return "adb"

    def __init__(self, config):
        """
        Args:
            config: 配置对象
        """
        super().__init__()
        self.config = config
        # ADB 可执行文件路径 - 尝试多个位置
        self.adb_binary = self._find_adb()
        self.serial = config.Emulator_Serial
        self.package = config.Emulator_PackageName

        # 初始化 ADB 客户端
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)

        # 检测设备
        self.detect_device()

        # 连接设备
        self.adb_connect()
        logger.attr("AdbDevice", self.adb)

        # 检测包名
        if self.package == "auto":
            self.detect_package()
        else:
            set_server(self.package)
        logger.attr("PackageName", self.package)

    def adb_command(self, cmd, timeout=10):
        """
        执行 ADB 命令
        Args:
            cmd (list): 命令列表
            timeout (int): 超时时间（秒）
        Returns:
            str: 命令输出
        """
        cmd = list(map(str, cmd))
        cmd = [self.adb_binary, "-s", self.serial] + cmd

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f'Command timeout: {" ".join(cmd)}')
            raise
        except Exception as e:
            logger.error(f'Command failed: {" ".join(cmd)}, error: {e}')
            raise

    def adb_shell(self, cmd, stream=False, recvall=True, timeout=10, rstrip=True):
        """
        执行 ADB shell 命令
        Args:
            cmd (list, str): 命令列表或字符串
            stream (bool): 返回流而非字符串输出 (默认: False)
            recvall (bool): 当stream=True时接收所有数据 (默认: True)
            timeout (int): 超时时间 (默认: 10)
            rstrip (bool): 去除最后的空行 (默认: True)
        Returns:
            str if stream=False
            bytes if stream=True and recvall=True
            socket if stream=True and recvall=False
        """
        if not isinstance(cmd, str):
            cmd = list(map(str, cmd))

        if stream:
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            if recvall:
                # bytes
                from module.device.method.utils import recv_all

                return recv_all(result)
            else:
                # socket
                return result
        else:
            # str - 普通字符串输出
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            from module.device.method.utils import remove_shell_warning

            result = remove_shell_warning(result)
            return result

    def subprocess_run(self, cmd, timeout=10):
        """
        运行子进程命令
        Args:
            cmd (list): 命令列表
            timeout (int): 超时时间
        Returns:
            str: 命令输出
        """
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Subprocess failed: {e}")
            raise

    def adb_start_server(self):
        """启动 ADB 服务器"""
        logger.info("Starting ADB server")
        try:
            subprocess.run([self.adb_binary, "start-server"], timeout=10)
            time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to start ADB server: {e}")

    def adb_disconnect(self):
        """
        断开 ADB 连接
        """
        msg = self.adb_client.disconnect(self.serial)
        if msg:
            logger.info(msg)
        # 释放缓存资源
        from module.base.decorator import del_cached_property

        del_cached_property(self, "u2")

    def adb_restart(self):
        """
        重启 ADB 服务器
        """
        logger.info("Restart adb server")
        # 杀掉当前 ADB 服务器
        self.adb_client.server_kill()
        # 重新创建 ADB 客户端
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)
        # 释放缓存资源
        from module.base.decorator import del_cached_property

        del_cached_property(self, "u2")

    def adb_reconnect(self):
        """
        重新连接 ADB（重连模拟器）
        """
        logger.info("Reconnecting to ADB device")

        if self.config.Emulator_AdbRestart and len(self.list_device()) == 0:
            # 重启 ADB 服务器（当检测不到设备且配置开启时）
            self.adb_restart()
            # 连接设备
            self.adb_connect()
            self.detect_device()
        else:
            # 只断开重连（不重启 ADB 服务器）
            self.adb_disconnect()
            self.adb_connect()
            self.detect_device()

    def list_device(self):
        """
        列出所有可用设备
        """
        try:
            devices = []
            # 使用 ADB 协议获取设备状态
            with self.adb_client._connect() as c:
                c.send_command("host:devices")
                c.check_okay()
                output = c.read_string_block()
                for line in output.splitlines():
                    parts = line = line.strip().split("\t")
                    if len(parts) != 2:
                        continue

                    serial, status = parts[0].strip(), parts[1].strip()

                    # 无效序列号
                    if not serial or serial == "(no serial number)":
                        logger.warning(f"Skipping device with invalid serial: {serial}")
                        continue

                    # 创建带状态的设备对象
                    device = AdbDeviceWithStatus(self.adb_client, serial, status)
                    devices.append(device)
                    logger.info(f"Found device: {serial} ({status})")

            return devices
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    def detect_device(self):
        """
        检测并选择设备（找模拟器）
        """
        logger.hr("Detecting device", level=2)
        logger.info(
            f"Current config: Serial='{self.serial}', PackageName='{self.package}'"
        )

        for attempt in range(2):
            devices = self.list_device()
            available = [d for d in devices if d.status == "device"]
            logger.info(f"Found {len(devices)} devices total")
            logger.info(f"Available devices: {[d.serial for d in available]}")

            if available:
                break  # 找到了可用的设备，跳出循环

            # 如果是 Windows + auto + 无设备，尝试 brute force connect
            if (
                self.serial == "auto"
                and platform.system() == "Windows"
                and attempt == 0
            ):
                logger.info("Attempting brute-force ADB connect for MuMu12...")
                # 连接 MuMu12 的默认端口
                for port in [16384, 16385, 16386, 16387, 16388]:
                    try:
                        self.adb_client.connect(f"127.0.0.1:{port}")
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Failed to connect 127.0.0.1:{port}: {e}")
                # 再次 list_device，如果已经开启了 mumu12，并且使用了上面的默认接口，应该能找到设备
                continue

        # 指定了 serial
        if ":" in self.serial and not self.serial.startswith("emulator-"):
            try:
                logger.info(f"Attempting to connect to {self.serial}")
                self.adb_client.connect(self.serial)  # 连接指定的设备
                time.sleep(1)
            except Exception as e:
                logger.debug(f"Initial connect failed: {e}")

        # 获取“最终”的设备列表
        devices = self.list_device()
        logger.info(f"Found {len(devices)} devices total")

        # 显示所有设备的详细信息
        if devices:
            for idx, d in enumerate(devices, 1):
                logger.info(f"  [{idx}] {d.serial} - Status: {d.status}")

        # 过滤可用设备
        available = [d for d in devices if d.status == "device"]
        logger.info(f"Available devices (status='device'): {len(available)}")

        if not available:
            logger.error("No available devices found")
            # 检查配置，看是否允许“重启ADB”
            if self.config.Emulator_AdbRestart:
                logger.info("Attempting to restart ADB server")
                self.adb_start_server()  # 重启 ADB
                devices = self.list_device()
                available = [d for d in devices if d.status == "device"]
                logger.info(f"After restart: {len(available)} available devices")

        if not available:
            logger.critical("No devices available")
            possible_reasons(
                "MuMu 模拟器未启动", "ADB 连接未建立", "模拟器 ADB 端口配置错误"
            )
            raise EmulatorNotRunningError("No available devices")

        # 选择设备
        if self.serial == "auto":
            logger.info("Using AUTO mode to select device")
            if len(available) == 1:
                # 只有一个可用设备
                self.serial = available[0].serial
                logger.info(
                    f" Auto selected device: {self.serial} (only one available)"
                )
            # MuMu 12 识别
            elif len(available) == 2:
                # 处理 MuMu12: 127.0.0.1:7555 和 127.0.0.1:16XXX
                logger.info("Found 2 devices, checking for MuMu12 device pair...")
                # 检查是否有 MuMu12 端口 (16xxx)
                mumu12_devices = [d for d in available if d.is_mumu12_family]
                logger.info(f"  MuMu12 devices: {[d.serial for d in mumu12_devices]}")
                # 检查是否有 MuMu 端口 (7555)
                has_7555 = any(d.serial == "127.0.0.1:7555" for d in available)
                logger.info(f"  Has 7555 port: {has_7555}")

                if mumu12_devices and has_7555:
                    # MuMu12 设备对,忽略 7555 使用 16xxx
                    self.serial = mumu12_devices[0].serial
                    logger.info(
                        f" Auto selected MuMu12 device: {self.serial} (ignoring 7555)"
                    )
                else:
                    # 多于 2 个设备,要求手动在 config 文件里指定 serial
                    logger.error(
                        f"Multiple devices found but not MuMu12 pair: {[d.serial for d in available]}"
                    )
                    logger.error(
                        "Please specify device serial in config file (Emulator.Serial)"
                    )
                    raise RequestHumanTakeover("Please specify device serial in config")
            else:
                logger.error(
                    f"Multiple devices found ({len(available)}): {[d.serial for d in available]}"
                )
                logger.error("AUTO mode cannot decide which device to use")
                logger.error(
                    "Please specify device serial in config file (Emulator.Serial)"
                )
                raise RequestHumanTakeover("Please specify device serial in config")
        else:  # self.serial != "auto"
            # 验证指定的设备是否存在
            if not any(d.serial == self.serial for d in available):
                logger.error(f"Device {self.serial} not found in available devices")
                possible_reasons(
                    f"设备 {self.serial} 未连接", "模拟器未启动", "配置的设备序列号错误"
                )
                raise EmulatorNotRunningError(f"Device {self.serial} not found")

        # MuMu12 7555 端口重定向
        if self.serial == "127.0.0.1:7555":
            mumu12_devices = [d for d in available if d.is_mumu12_family]
            if len(mumu12_devices) == 1:
                emu_serial = mumu12_devices[0].serial
                logger.warning(f"Redirect MuMu12 {self.serial} to {emu_serial}")
                self.serial = emu_serial
            elif len(mumu12_devices) >= 2:
                logger.warning(f"Multiple MuMu12 serial found, cannot redirect")

        # MuMu12 动态端口追踪 (16384被占用时切换到16385等)
        current_device = None
        for d in available:
            if d.serial == self.serial:
                current_device = d
                break

        if current_device and current_device.is_mumu12_family:
            # 检查是否精确匹配（即检查它是否真的在列表里）
            matched = False
            for device in available:
                if device.is_mumu12_family and device.port == current_device.port:
                    matched = True
                    break

            if not matched:
                # 端口切换,尝试相邻端口 (±2范围内)
                for device in available:
                    if device.is_mumu12_family:
                        port_diff = device.port - current_device.port
                        if -2 <= port_diff <= 2:
                            # 自动“修正” self.serial 到新的端口
                            logger.info(
                                f"MuMu12 serial switched {self.serial} -> {device.serial}"
                            )
                            self.serial = device.serial
                            break

        logger.info(f"Selected device: {self.serial}")

    def adb_connect(self):
        """
        连接到 ADB 设备（连接模拟器）
        """
        logger.hr("Connecting to device", level=2)

        # 断开 offline 设备
        devices = self.list_device()
        for device in devices:
            if device.status == "offline":
                logger.warning(f"Device {device.serial} is offline, disconnect it")
                try:
                    self.adb_client.disconnect(device.serial)
                except Exception as e:
                    logger.warning(f"Failed to disconnect offline device: {e}")

        # 如果是网络设备，尝试连接
        if ":" in self.serial and not self.serial.startswith("emulator-"):
            for trial in range(3):
                try:
                    logger.info(f"Connecting to {self.serial} (trial {trial + 1}/3)")
                    self.adb_client.connect(self.serial)
                    time.sleep(1)
                    break
                except Exception as e:
                    logger.warning(f"Connection failed: {e}")
                    error_msg = str(e)

                    if trial >= 2:
                        # MuMu12 特殊处理: 端口冲突时尝试相邻端口
                        if "(10061)" in error_msg:
                            # 连接被拒绝
                            logger.error(
                                "Connection refused - emulator may not be running or port is occupied"
                            )

                            # 如果是 MuMu12,尝试暴力连接相邻端口
                            current_device = AdbDeviceWithStatus(
                                self.adb_client, self.serial, "unknown"
                            )
                            if current_device.is_mumu12_family:
                                logger.info("Trying adjacent MuMu12 ports...")
                                port = current_device.port
                                serial_list = [
                                    f"127.0.0.1:{port + offset}"
                                    for offset in [1, -1, 2, -2]
                                ]
                                for alt_serial in serial_list:
                                    try:
                                        logger.info(f"Trying {alt_serial}")
                                        self.adb_client.connect(alt_serial)
                                        time.sleep(1)
                                        self.serial = alt_serial
                                        logger.info(
                                            f"Connected to alternative port: {alt_serial}"
                                        )
                                        break
                                    except Exception as alt_e:
                                        logger.debug(
                                            f"Failed to connect to {alt_serial}: {alt_e}"
                                        )
                                        continue
                                else:
                                    # 所有端口都失败
                                    raise EmulatorNotRunningError(
                                        f"Failed to connect to {self.serial} and adjacent ports"
                                    )
                            else:
                                raise EmulatorNotRunningError(
                                    f"Failed to connect to {self.serial}"
                                )
                        else:
                            raise
                    time.sleep(2)

        # 获取设备对象
        try:
            self.adb = self.adb_client.device(serial=self.serial)
            logger.info(f"Connected to device: {self.serial}")
        except Exception as e:
            logger.error(f"Failed to get device: {e}")
            raise EmulatorNotRunningError(f"Device {self.serial} not accessible")

    def detect_package(self):
        """
        检测游戏包名（找游戏 --> config.Emulator_PackageName）
        """
        logger.hr("Detecting package", level=2)

        # 获取所有已安装的包
        try:
            result = self.adb_shell(["pm", "list", "packages"])
            packages = [
                line.replace("package:", "").strip()
                for line in result.split("\n")
                if line.startswith("package:")
            ]
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
            raise

        # 查找公主连结包
        all_valid_packages = VALID_PACKAGE
        for package in packages:
            if package in all_valid_packages:
                self.package = package
                set_server(package)
                logger.info(f"Detected package: {package}")
                return

        # 未找到包
        logger.error("PCR package not found")
        possible_reasons("游戏未安装", "包名不在支持列表中", "模拟器中未安装公主连结")
        raise RequestHumanTakeover("PCR package not installed")

    def adb_forward(self, remote):
        """
        创建ADB端口转发

        Args:
            remote (str): 设备端地址，如 'tcp:53516'

        Returns:
            int: PC端端口号
        """
        port = 0

        # 检查是否已存在转发，复用或清理
        for forward in self.adb.forward_list():
            if (
                forward.serial == self.serial
                and forward.remote == remote
                and forward.local.startswith("tcp:")
            ):
                if not port:
                    logger.info(f"Reuse forward: {forward}")
                    port = int(forward.local[4:])
                else:
                    logger.info(f"Remove redundant forward: {forward}")
                    self.adb_forward_remove(forward.local)

        # 如果已有端口，直接返回
        if port:
            return port

        # 创建新的端口转发
        port = random.randint(
            self.config.FORWARD_PORT_RANGE[0], self.config.FORWARD_PORT_RANGE[1]
        )
        forward = ForwardItem(self.serial, f"tcp:{port}", remote)
        logger.info(f"Create forward: {forward}")
        self.adb.forward(forward.local, forward.remote)
        return port

    def adb_forward_remove(self, local):
        """
        移除ADB端口转发

        Args:
            local (str): PC端地址，如 'tcp:2437'
        """
        try:
            with self.adb_client._connect() as c:
                list_cmd = f"host-serial:{self.serial}:killforward:{local}"
                c.send_command(list_cmd)
                c.check_okay()
        except AdbError as e:
            msg = str(e)
            if re.search(r"listener .*? not found", msg):
                logger.warning(f"{type(e).__name__}: {msg}")
            else:
                raise

    def adb_push(self, local, remote):
        """
        推送文件到设备

        Args:
            local (str): 本地文件路径
            remote (str): 设备文件路径

        Returns:
            str: 命令输出
        """
        cmd = ["push", local, remote]
        return self.adb_command(cmd)

    @property
    def is_mumu_over_version_356(self) -> bool:
        """
        判断是否为 MuMu12 >= 3.5.6 版本
        该版本具有 nemud.app_keep_alive 属性且始终为竖屏设备
        MuMu PRO (Mac) 具有相同特性
        """
        # 只针对MuMu12模拟器 (端口范围 16384-17408)
        if not (16384 <= self.port <= 17408):
            return False
        # 假设MuMu12都是较新版本
        return True

    @property
    def port(self) -> int:
        """获取设备端口号"""
        try:
            return int(self.serial.split(":")[1])
        except (IndexError, ValueError):
            return 0

    @cached_property
    def u2(self):
        """uiautomator2实例"""
        return u2.connect(self.serial)

    _orientation_description = {
        0: "Normal",
        1: "HOME key on the right",
        2: "HOME key on the top",
        3: "HOME key on the left",
    }
    orientation = 0

    def get_orientation(self):
        """
        获取设备旋转方向

        Returns:
            int:
                0: 'Normal'
                1: 'HOME key on the right'
                2: 'HOME key on the top'
                3: 'HOME key on the left'
        """
        _DISPLAY_RE = re.compile(
            r".*DisplayViewport{.*valid=true, .*orientation=(?P<orientation>\d+), .*deviceWidth=(?P<width>\d+), deviceHeight=(?P<height>\d+).*"
        )
        output = self.adb_shell(["dumpsys", "display"])

        res = _DISPLAY_RE.search(output, 0)

        if res:
            o = int(res.group("orientation"))
            if o in Connection._orientation_description:
                pass
            else:
                o = 0
                logger.warning(f"Invalid device orientation: {o}, assume it is normal")
        else:
            o = 0
            logger.warning("Unable to get device orientation, assume it is normal")

        self.orientation = o
        logger.attr(
            "Device Orientation",
            f'{o} ({Connection._orientation_description.get(o, "Unknown")})',
        )
        return o

    @staticmethod
    def sleep(second):
        """
        Args:
            second(int, float, tuple): 固定时间或随机范围，如 (1, 2) 表示 1-2 秒之间随机
        """
        time.sleep(ensure_time(second))
=======
"""
设备连接管理
"""

import re
import subprocess
import time
import random
import platform

import uiautomator2 as u2
from adbutils import AdbClient, AdbDevice, AdbTimeout, ForwardItem
from adbutils.errors import AdbError

from module.base.decorator import cached_property
from module.config.config import PriconneConfig
from module.config.server import VALID_PACKAGE, set_server
from module.device.method.adb import Adb
from module.device.method.utils import RETRY_TRIES, retry_sleep, possible_reasons
from module.exception import EmulatorNotRunningError, RequestHumanTakeover
from module.logger import logger
from module.base.utils import ensure_time


class AdbDeviceWithStatus(AdbDevice):
    """带状态的 ADB 设备"""

    def __init__(self, client: AdbClient, serial: str, status: str):
        self.status = status
        super().__init__(client, serial)

    def __str__(self):
        return f"AdbDevice({self.serial}, {self.status})"

    __repr__ = __str__

    def __bool__(self):
        return True

    @property
    def port(self) -> int:
        """获取设备端口"""
        try:
            return int(self.serial.split(":")[1])
        except (IndexError, ValueError):
            return 0

    @property
    def is_mumu12_family(self):
        """是否为 MuMu12 系列模拟器 (端口范围 16384-17408)"""
        return 16384 <= self.port <= 17408

    @property
    def is_mumu_family(self):
        """是否为 MuMu 系列模拟器"""
        return self.serial == "127.0.0.1:7555" or self.is_mumu12_family


class Connection(Adb):
    """
    设备连接类
    """

    config: PriconneConfig

    @staticmethod
    def _find_adb():
        """查找 adb 可执行文件"""
        import os
        import shutil

        # 优先使用 PATH 中的 adb
        adb_in_path = shutil.which("adb")
        if adb_in_path:
            return adb_in_path

        # 常见的 adb 路径
        possible_paths = [
            # MuMu12 模拟器
            r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
            r"D:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
            # MuMu 模拟器
            r"C:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
            # 雷电模拟器
            r"C:\leidian\LDPlayer9\adb.exe",
            # 搞机工具箱
            os.path.expanduser(r"~\Documents\搞机工具箱10.1.0\搞机工具箱10.1.0\adb.exe"),
            # Android SDK
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found adb at: {path}")
                return path

        # 默认使用 adb，期望在 PATH 中
        return "adb"

    def __init__(self, config):
        """
        Args:
            config: 配置对象
        """
        super().__init__()
        self.config = config
        # ADB 可执行文件路径 - 尝试多个位置
        self.adb_binary = self._find_adb()
        self.serial = config.Emulator_Serial
        self.package = config.Emulator_PackageName

        # 初始化 ADB 客户端
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)

        # 检测设备
        self.detect_device()

        # 连接设备
        self.adb_connect()
        logger.attr("AdbDevice", self.adb)

        # 检测包名
        if self.package == "auto":
            self.detect_package()
        else:
            set_server(self.package)
        logger.attr("PackageName", self.package)

    def adb_command(self, cmd, timeout=10):
        """
        执行 ADB 命令
        Args:
            cmd (list): 命令列表
            timeout (int): 超时时间（秒）
        Returns:
            str: 命令输出
        """
        cmd = list(map(str, cmd))
        cmd = [self.adb_binary, "-s", self.serial] + cmd

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f'Command timeout: {" ".join(cmd)}')
            raise
        except Exception as e:
            logger.error(f'Command failed: {" ".join(cmd)}, error: {e}')
            raise

    def adb_shell(self, cmd, stream=False, recvall=True, timeout=10, rstrip=True):
        """
        执行 ADB shell 命令
        Args:
            cmd (list, str): 命令列表或字符串
            stream (bool): 返回流而非字符串输出 (默认: False)
            recvall (bool): 当stream=True时接收所有数据 (默认: True)
            timeout (int): 超时时间 (默认: 10)
            rstrip (bool): 去除最后的空行 (默认: True)
        Returns:
            str if stream=False
            bytes if stream=True and recvall=True
            socket if stream=True and recvall=False
        """
        if not isinstance(cmd, str):
            cmd = list(map(str, cmd))

        if stream:
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            if recvall:
                # bytes
                from module.device.method.utils import recv_all

                return recv_all(result)
            else:
                # socket
                return result
        else:
            # str - 普通字符串输出
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            from module.device.method.utils import remove_shell_warning

            result = remove_shell_warning(result)
            return result

    def subprocess_run(self, cmd, timeout=10):
        """
        运行子进程命令
        Args:
            cmd (list): 命令列表
            timeout (int): 超时时间
        Returns:
            str: 命令输出
        """
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Subprocess failed: {e}")
            raise

    def adb_start_server(self):
        """启动 ADB 服务器"""
        logger.info("Starting ADB server")
        try:
            subprocess.run([self.adb_binary, "start-server"], timeout=10)
            time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to start ADB server: {e}")

    def adb_disconnect(self):
        """
        断开 ADB 连接
        """
        msg = self.adb_client.disconnect(self.serial)
        if msg:
            logger.info(msg)
        # 释放缓存资源
        from module.base.decorator import del_cached_property

        del_cached_property(self, "u2")

    def adb_restart(self):
        """
        重启 ADB 服务器
        """
        logger.info("Restart adb server")
        # 杀掉当前 ADB 服务器
        self.adb_client.server_kill()
        # 重新创建 ADB 客户端
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)
        # 释放缓存资源
        from module.base.decorator import del_cached_property

        del_cached_property(self, "u2")

    def adb_reconnect(self):
        """
        重新连接 ADB（重连模拟器）
        """
        logger.info("Reconnecting to ADB device")

        if self.config.Emulator_AdbRestart and len(self.list_device()) == 0:
            # 重启 ADB 服务器（当检测不到设备且配置开启时）
            self.adb_restart()
            # 连接设备
            self.adb_connect()
            self.detect_device()
        else:
            # 只断开重连（不重启 ADB 服务器）
            self.adb_disconnect()
            self.adb_connect()
            self.detect_device()

    def list_device(self):
        """
        列出所有可用设备
        """
        try:
            devices = []
            # 使用 ADB 协议获取设备状态
            with self.adb_client._connect() as c:
                c.send_command("host:devices")
                c.check_okay()
                output = c.read_string_block()
                for line in output.splitlines():
                    parts = line = line.strip().split("\t")
                    if len(parts) != 2:
                        continue

                    serial, status = parts[0].strip(), parts[1].strip()

                    # 无效序列号
                    if not serial or serial == "(no serial number)":
                        logger.warning(f"Skipping device with invalid serial: {serial}")
                        continue

                    # 创建带状态的设备对象
                    device = AdbDeviceWithStatus(self.adb_client, serial, status)
                    devices.append(device)
                    logger.info(f"Found device: {serial} ({status})")

            return devices
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    def detect_device(self):
        """
        检测并选择设备（找模拟器）
        """
        logger.hr("Detecting device", level=2)
        logger.info(
            f"Current config: Serial='{self.serial}', PackageName='{self.package}'"
        )

        for attempt in range(2):
            devices = self.list_device()
            available = [d for d in devices if d.status == "device"]
            logger.info(f"Found {len(devices)} devices total")
            logger.info(f"Available devices: {[d.serial for d in available]}")

            if available:
                break  # 找到了可用的设备，跳出循环

            # 如果是 Windows + auto + 无设备，尝试 brute force connect
            if (
                self.serial == "auto"
                and platform.system() == "Windows"
                and attempt == 0
            ):
                logger.info("Attempting brute-force ADB connect for MuMu12...")
                # 连接 MuMu12 的默认端口
                for port in [16384, 16385, 16386, 16387, 16388]:
                    try:
                        self.adb_client.connect(f"127.0.0.1:{port}")
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Failed to connect 127.0.0.1:{port}: {e}")
                # 再次 list_device，如果已经开启了 mumu12，并且使用了上面的默认接口，应该能找到设备
                continue

        # 指定了 serial
        if ":" in self.serial and not self.serial.startswith("emulator-"):
            try:
                logger.info(f"Attempting to connect to {self.serial}")
                self.adb_client.connect(self.serial)  # 连接指定的设备
                time.sleep(1)
            except Exception as e:
                logger.debug(f"Initial connect failed: {e}")

        # 获取“最终”的设备列表
        devices = self.list_device()
        logger.info(f"Found {len(devices)} devices total")

        # 显示所有设备的详细信息
        if devices:
            for idx, d in enumerate(devices, 1):
                logger.info(f"  [{idx}] {d.serial} - Status: {d.status}")

        # 过滤可用设备
        available = [d for d in devices if d.status == "device"]
        logger.info(f"Available devices (status='device'): {len(available)}")

        if not available:
            logger.error("No available devices found")
            # 检查配置，看是否允许“重启ADB”
            if self.config.Emulator_AdbRestart:
                logger.info("Attempting to restart ADB server")
                self.adb_start_server()  # 重启 ADB
                devices = self.list_device()
                available = [d for d in devices if d.status == "device"]
                logger.info(f"After restart: {len(available)} available devices")

        if not available:
            logger.critical("No devices available")
            possible_reasons(
                "MuMu 模拟器未启动", "ADB 连接未建立", "模拟器 ADB 端口配置错误"
            )
            raise EmulatorNotRunningError("No available devices")

        # 选择设备
        if self.serial == "auto":
            logger.info("Using AUTO mode to select device")
            if len(available) == 1:
                # 只有一个可用设备
                self.serial = available[0].serial
                logger.info(
                    f" Auto selected device: {self.serial} (only one available)"
                )
            # MuMu 12 识别
            elif len(available) == 2:
                # 处理 MuMu12: 127.0.0.1:7555 和 127.0.0.1:16XXX
                logger.info("Found 2 devices, checking for MuMu12 device pair...")
                # 检查是否有 MuMu12 端口 (16xxx)
                mumu12_devices = [d for d in available if d.is_mumu12_family]
                logger.info(f"  MuMu12 devices: {[d.serial for d in mumu12_devices]}")
                # 检查是否有 MuMu 端口 (7555)
                has_7555 = any(d.serial == "127.0.0.1:7555" for d in available)
                logger.info(f"  Has 7555 port: {has_7555}")

                if mumu12_devices and has_7555:
                    # MuMu12 设备对,忽略 7555 使用 16xxx
                    self.serial = mumu12_devices[0].serial
                    logger.info(
                        f" Auto selected MuMu12 device: {self.serial} (ignoring 7555)"
                    )
                else:
                    # 多于 2 个设备,要求手动在 config 文件里指定 serial
                    logger.error(
                        f"Multiple devices found but not MuMu12 pair: {[d.serial for d in available]}"
                    )
                    logger.error(
                        "Please specify device serial in config file (Emulator.Serial)"
                    )
                    raise RequestHumanTakeover("Please specify device serial in config")
            else:
                logger.error(
                    f"Multiple devices found ({len(available)}): {[d.serial for d in available]}"
                )
                logger.error("AUTO mode cannot decide which device to use")
                logger.error(
                    "Please specify device serial in config file (Emulator.Serial)"
                )
                raise RequestHumanTakeover("Please specify device serial in config")
        else:  # self.serial != "auto"
            # 验证指定的设备是否存在
            if not any(d.serial == self.serial for d in available):
                logger.error(f"Device {self.serial} not found in available devices")
                possible_reasons(
                    f"设备 {self.serial} 未连接", "模拟器未启动", "配置的设备序列号错误"
                )
                raise EmulatorNotRunningError(f"Device {self.serial} not found")

        # MuMu12 7555 端口重定向
        if self.serial == "127.0.0.1:7555":
            mumu12_devices = [d for d in available if d.is_mumu12_family]
            if len(mumu12_devices) == 1:
                emu_serial = mumu12_devices[0].serial
                logger.warning(f"Redirect MuMu12 {self.serial} to {emu_serial}")
                self.serial = emu_serial
            elif len(mumu12_devices) >= 2:
                logger.warning(f"Multiple MuMu12 serial found, cannot redirect")

        # MuMu12 动态端口追踪 (16384被占用时切换到16385等)
        current_device = None
        for d in available:
            if d.serial == self.serial:
                current_device = d
                break

        if current_device and current_device.is_mumu12_family:
            # 检查是否精确匹配（即检查它是否真的在列表里）
            matched = False
            for device in available:
                if device.is_mumu12_family and device.port == current_device.port:
                    matched = True
                    break

            if not matched:
                # 端口切换,尝试相邻端口 (±2范围内)
                for device in available:
                    if device.is_mumu12_family:
                        port_diff = device.port - current_device.port
                        if -2 <= port_diff <= 2:
                            # 自动“修正” self.serial 到新的端口
                            logger.info(
                                f"MuMu12 serial switched {self.serial} -> {device.serial}"
                            )
                            self.serial = device.serial
                            break

        logger.info(f"Selected device: {self.serial}")

    def adb_connect(self):
        """
        连接到 ADB 设备（连接模拟器）
        """
        logger.hr("Connecting to device", level=2)

        # 断开 offline 设备
        devices = self.list_device()
        for device in devices:
            if device.status == "offline":
                logger.warning(f"Device {device.serial} is offline, disconnect it")
                try:
                    self.adb_client.disconnect(device.serial)
                except Exception as e:
                    logger.warning(f"Failed to disconnect offline device: {e}")

        # 如果是网络设备，尝试连接
        if ":" in self.serial and not self.serial.startswith("emulator-"):
            for trial in range(3):
                try:
                    logger.info(f"Connecting to {self.serial} (trial {trial + 1}/3)")
                    self.adb_client.connect(self.serial)
                    time.sleep(1)
                    break
                except Exception as e:
                    logger.warning(f"Connection failed: {e}")
                    error_msg = str(e)

                    if trial >= 2:
                        # MuMu12 特殊处理: 端口冲突时尝试相邻端口
                        if "(10061)" in error_msg:
                            # 连接被拒绝
                            logger.error(
                                "Connection refused - emulator may not be running or port is occupied"
                            )

                            # 如果是 MuMu12,尝试暴力连接相邻端口
                            current_device = AdbDeviceWithStatus(
                                self.adb_client, self.serial, "unknown"
                            )
                            if current_device.is_mumu12_family:
                                logger.info("Trying adjacent MuMu12 ports...")
                                port = current_device.port
                                serial_list = [
                                    f"127.0.0.1:{port + offset}"
                                    for offset in [1, -1, 2, -2]
                                ]
                                for alt_serial in serial_list:
                                    try:
                                        logger.info(f"Trying {alt_serial}")
                                        self.adb_client.connect(alt_serial)
                                        time.sleep(1)
                                        self.serial = alt_serial
                                        logger.info(
                                            f"Connected to alternative port: {alt_serial}"
                                        )
                                        break
                                    except Exception as alt_e:
                                        logger.debug(
                                            f"Failed to connect to {alt_serial}: {alt_e}"
                                        )
                                        continue
                                else:
                                    # 所有端口都失败
                                    raise EmulatorNotRunningError(
                                        f"Failed to connect to {self.serial} and adjacent ports"
                                    )
                            else:
                                raise EmulatorNotRunningError(
                                    f"Failed to connect to {self.serial}"
                                )
                        else:
                            raise
                    time.sleep(2)

        # 获取设备对象
        try:
            self.adb = self.adb_client.device(serial=self.serial)
            logger.info(f"Connected to device: {self.serial}")
        except Exception as e:
            logger.error(f"Failed to get device: {e}")
            raise EmulatorNotRunningError(f"Device {self.serial} not accessible")

    def detect_package(self):
        """
        检测游戏包名（找游戏 --> config.Emulator_PackageName）
        """
        logger.hr("Detecting package", level=2)

        # 获取所有已安装的包
        try:
            result = self.adb_shell(["pm", "list", "packages"])
            packages = [
                line.replace("package:", "").strip()
                for line in result.split("\n")
                if line.startswith("package:")
            ]
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
            raise

        # 查找公主连结包
        all_valid_packages = VALID_PACKAGE
        for package in packages:
            if package in all_valid_packages:
                self.package = package
                set_server(package)
                logger.info(f"Detected package: {package}")
                return

        # 未找到包
        logger.error("PCR package not found")
        possible_reasons("游戏未安装", "包名不在支持列表中", "模拟器中未安装公主连结")
        raise RequestHumanTakeover("PCR package not installed")

    def adb_forward(self, remote):
        """
        创建ADB端口转发

        Args:
            remote (str): 设备端地址，如 'tcp:53516'

        Returns:
            int: PC端端口号
        """
        port = 0

        # 检查是否已存在转发，复用或清理
        for forward in self.adb.forward_list():
            if (
                forward.serial == self.serial
                and forward.remote == remote
                and forward.local.startswith("tcp:")
            ):
                if not port:
                    logger.info(f"Reuse forward: {forward}")
                    port = int(forward.local[4:])
                else:
                    logger.info(f"Remove redundant forward: {forward}")
                    self.adb_forward_remove(forward.local)

        # 如果已有端口，直接返回
        if port:
            return port

        # 创建新的端口转发
        port = random.randint(
            self.config.FORWARD_PORT_RANGE[0], self.config.FORWARD_PORT_RANGE[1]
        )
        forward = ForwardItem(self.serial, f"tcp:{port}", remote)
        logger.info(f"Create forward: {forward}")
        self.adb.forward(forward.local, forward.remote)
        return port

    def adb_forward_remove(self, local):
        """
        移除ADB端口转发

        Args:
            local (str): PC端地址，如 'tcp:2437'
        """
        try:
            with self.adb_client._connect() as c:
                list_cmd = f"host-serial:{self.serial}:killforward:{local}"
                c.send_command(list_cmd)
                c.check_okay()
        except AdbError as e:
            msg = str(e)
            if re.search(r"listener .*? not found", msg):
                logger.warning(f"{type(e).__name__}: {msg}")
            else:
                raise

    def adb_push(self, local, remote):
        """
        推送文件到设备

        Args:
            local (str): 本地文件路径
            remote (str): 设备文件路径

        Returns:
            str: 命令输出
        """
        cmd = ["push", local, remote]
        return self.adb_command(cmd)

    @property
    def is_mumu_over_version_356(self) -> bool:
        """
        判断是否为 MuMu12 >= 3.5.6 版本
        该版本具有 nemud.app_keep_alive 属性且始终为竖屏设备
        MuMu PRO (Mac) 具有相同特性
        """
        # 只针对MuMu12模拟器 (端口范围 16384-17408)
        if not (16384 <= self.port <= 17408):
            return False
        # 假设MuMu12都是较新版本
        return True

    @property
    def port(self) -> int:
        """获取设备端口号"""
        try:
            return int(self.serial.split(":")[1])
        except (IndexError, ValueError):
            return 0

    @cached_property
    def u2(self):
        """uiautomator2实例"""
        return u2.connect(self.serial)

    _orientation_description = {
        0: "Normal",
        1: "HOME key on the right",
        2: "HOME key on the top",
        3: "HOME key on the left",
    }
    orientation = 0

    def get_orientation(self):
        """
        获取设备旋转方向

        Returns:
            int:
                0: 'Normal'
                1: 'HOME key on the right'
                2: 'HOME key on the top'
                3: 'HOME key on the left'
        """
        _DISPLAY_RE = re.compile(
            r".*DisplayViewport{.*valid=true, .*orientation=(?P<orientation>\d+), .*deviceWidth=(?P<width>\d+), deviceHeight=(?P<height>\d+).*"
        )
        output = self.adb_shell(["dumpsys", "display"])

        res = _DISPLAY_RE.search(output, 0)

        if res:
            o = int(res.group("orientation"))
            if o in Connection._orientation_description:
                pass
            else:
                o = 0
                logger.warning(f"Invalid device orientation: {o}, assume it is normal")
        else:
            o = 0
            logger.warning("Unable to get device orientation, assume it is normal")

        self.orientation = o
        logger.attr(
            "Device Orientation",
            f'{o} ({Connection._orientation_description.get(o, "Unknown")})',
        )
        return o

    @staticmethod
    def sleep(second):
        """
        Args:
            second(int, float, tuple): 固定时间或随机范围，如 (1, 2) 表示 1-2 秒之间随机
        """
        time.sleep(ensure_time(second))
>>>>>>> Stashed changes
=======
"""
设备连接管理
"""

import re
import subprocess
import time
import random
import platform

import uiautomator2 as u2
from adbutils import AdbClient, AdbDevice, AdbTimeout, ForwardItem
from adbutils.errors import AdbError

from module.base.decorator import cached_property
from module.config.config import PriconneConfig
from module.config.server import VALID_PACKAGE, set_server
from module.device.method.adb import Adb
from module.device.method.utils import RETRY_TRIES, retry_sleep, possible_reasons
from module.exception import EmulatorNotRunningError, RequestHumanTakeover
from module.logger import logger
from module.base.utils import ensure_time


class AdbDeviceWithStatus(AdbDevice):
    """带状态的 ADB 设备"""

    def __init__(self, client: AdbClient, serial: str, status: str):
        self.status = status
        super().__init__(client, serial)

    def __str__(self):
        return f"AdbDevice({self.serial}, {self.status})"

    __repr__ = __str__

    def __bool__(self):
        return True

    @property
    def port(self) -> int:
        """获取设备端口"""
        try:
            return int(self.serial.split(":")[1])
        except (IndexError, ValueError):
            return 0

    @property
    def is_mumu12_family(self):
        """是否为 MuMu12 系列模拟器 (端口范围 16384-17408)"""
        return 16384 <= self.port <= 17408

    @property
    def is_mumu_family(self):
        """是否为 MuMu 系列模拟器"""
        return self.serial == "127.0.0.1:7555" or self.is_mumu12_family


class Connection(Adb):
    """
    设备连接类
    """

    config: PriconneConfig

    @staticmethod
    def _find_adb():
        """查找 adb 可执行文件"""
        import os
        import shutil

        # 优先使用 PATH 中的 adb
        adb_in_path = shutil.which("adb")
        if adb_in_path:
            return adb_in_path

        # 常见的 adb 路径
        possible_paths = [
            # MuMu12 模拟器
            r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
            r"D:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
            # MuMu 模拟器
            r"C:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
            # 雷电模拟器
            r"C:\leidian\LDPlayer9\adb.exe",
            # 搞机工具箱
            os.path.expanduser(r"~\Documents\搞机工具箱10.1.0\搞机工具箱10.1.0\adb.exe"),
            # Android SDK
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found adb at: {path}")
                return path

        # 默认使用 adb，期望在 PATH 中
        return "adb"

    def __init__(self, config):
        """
        Args:
            config: 配置对象
        """
        super().__init__()
        self.config = config
        # ADB 可执行文件路径 - 尝试多个位置
        self.adb_binary = self._find_adb()
        self.serial = config.Emulator_Serial
        self.package = config.Emulator_PackageName

        # 初始化 ADB 客户端
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)

        # 检测设备
        self.detect_device()

        # 连接设备
        self.adb_connect()
        logger.attr("AdbDevice", self.adb)

        # 检测包名
        if self.package == "auto":
            self.detect_package()
        else:
            set_server(self.package)
        logger.attr("PackageName", self.package)

    def adb_command(self, cmd, timeout=10):
        """
        执行 ADB 命令
        Args:
            cmd (list): 命令列表
            timeout (int): 超时时间（秒）
        Returns:
            str: 命令输出
        """
        cmd = list(map(str, cmd))
        cmd = [self.adb_binary, "-s", self.serial] + cmd

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f'Command timeout: {" ".join(cmd)}')
            raise
        except Exception as e:
            logger.error(f'Command failed: {" ".join(cmd)}, error: {e}')
            raise

    def adb_shell(self, cmd, stream=False, recvall=True, timeout=10, rstrip=True):
        """
        执行 ADB shell 命令
        Args:
            cmd (list, str): 命令列表或字符串
            stream (bool): 返回流而非字符串输出 (默认: False)
            recvall (bool): 当stream=True时接收所有数据 (默认: True)
            timeout (int): 超时时间 (默认: 10)
            rstrip (bool): 去除最后的空行 (默认: True)
        Returns:
            str if stream=False
            bytes if stream=True and recvall=True
            socket if stream=True and recvall=False
        """
        if not isinstance(cmd, str):
            cmd = list(map(str, cmd))

        if stream:
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            if recvall:
                # bytes
                from module.device.method.utils import recv_all

                return recv_all(result)
            else:
                # socket
                return result
        else:
            # str - 普通字符串输出
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            from module.device.method.utils import remove_shell_warning

            result = remove_shell_warning(result)
            return result

    def subprocess_run(self, cmd, timeout=10):
        """
        运行子进程命令
        Args:
            cmd (list): 命令列表
            timeout (int): 超时时间
        Returns:
            str: 命令输出
        """
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Subprocess failed: {e}")
            raise

    def adb_start_server(self):
        """启动 ADB 服务器"""
        logger.info("Starting ADB server")
        try:
            subprocess.run([self.adb_binary, "start-server"], timeout=10)
            time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to start ADB server: {e}")

    def adb_disconnect(self):
        """
        断开 ADB 连接
        """
        msg = self.adb_client.disconnect(self.serial)
        if msg:
            logger.info(msg)
        # 释放缓存资源
        from module.base.decorator import del_cached_property

        del_cached_property(self, "u2")

    def adb_restart(self):
        """
        重启 ADB 服务器
        """
        logger.info("Restart adb server")
        # 杀掉当前 ADB 服务器
        self.adb_client.server_kill()
        # 重新创建 ADB 客户端
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)
        # 释放缓存资源
        from module.base.decorator import del_cached_property

        del_cached_property(self, "u2")

    def adb_reconnect(self):
        """
        重新连接 ADB（重连模拟器）
        """
        logger.info("Reconnecting to ADB device")

        if self.config.Emulator_AdbRestart and len(self.list_device()) == 0:
            # 重启 ADB 服务器（当检测不到设备且配置开启时）
            self.adb_restart()
            # 连接设备
            self.adb_connect()
            self.detect_device()
        else:
            # 只断开重连（不重启 ADB 服务器）
            self.adb_disconnect()
            self.adb_connect()
            self.detect_device()

    def list_device(self):
        """
        列出所有可用设备
        """
        try:
            devices = []
            # 使用 ADB 协议获取设备状态
            with self.adb_client._connect() as c:
                c.send_command("host:devices")
                c.check_okay()
                output = c.read_string_block()
                for line in output.splitlines():
                    parts = line = line.strip().split("\t")
                    if len(parts) != 2:
                        continue

                    serial, status = parts[0].strip(), parts[1].strip()

                    # 无效序列号
                    if not serial or serial == "(no serial number)":
                        logger.warning(f"Skipping device with invalid serial: {serial}")
                        continue

                    # 创建带状态的设备对象
                    device = AdbDeviceWithStatus(self.adb_client, serial, status)
                    devices.append(device)
                    logger.info(f"Found device: {serial} ({status})")

            return devices
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    def detect_device(self):
        """
        检测并选择设备（找模拟器）
        """
        logger.hr("Detecting device", level=2)
        logger.info(
            f"Current config: Serial='{self.serial}', PackageName='{self.package}'"
        )

        for attempt in range(2):
            devices = self.list_device()
            available = [d for d in devices if d.status == "device"]
            logger.info(f"Found {len(devices)} devices total")
            logger.info(f"Available devices: {[d.serial for d in available]}")

            if available:
                break  # 找到了可用的设备，跳出循环

            # 如果是 Windows + auto + 无设备，尝试 brute force connect
            if (
                self.serial == "auto"
                and platform.system() == "Windows"
                and attempt == 0
            ):
                logger.info("Attempting brute-force ADB connect for MuMu12...")
                # 连接 MuMu12 的默认端口
                for port in [16384, 16385, 16386, 16387, 16388]:
                    try:
                        self.adb_client.connect(f"127.0.0.1:{port}")
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Failed to connect 127.0.0.1:{port}: {e}")
                # 再次 list_device，如果已经开启了 mumu12，并且使用了上面的默认接口，应该能找到设备
                continue

        # 指定了 serial
        if ":" in self.serial and not self.serial.startswith("emulator-"):
            try:
                logger.info(f"Attempting to connect to {self.serial}")
                self.adb_client.connect(self.serial)  # 连接指定的设备
                time.sleep(1)
            except Exception as e:
                logger.debug(f"Initial connect failed: {e}")

        # 获取“最终”的设备列表
        devices = self.list_device()
        logger.info(f"Found {len(devices)} devices total")

        # 显示所有设备的详细信息
        if devices:
            for idx, d in enumerate(devices, 1):
                logger.info(f"  [{idx}] {d.serial} - Status: {d.status}")

        # 过滤可用设备
        available = [d for d in devices if d.status == "device"]
        logger.info(f"Available devices (status='device'): {len(available)}")

        if not available:
            logger.error("No available devices found")
            # 检查配置，看是否允许“重启ADB”
            if self.config.Emulator_AdbRestart:
                logger.info("Attempting to restart ADB server")
                self.adb_start_server()  # 重启 ADB
                devices = self.list_device()
                available = [d for d in devices if d.status == "device"]
                logger.info(f"After restart: {len(available)} available devices")

        if not available:
            logger.critical("No devices available")
            possible_reasons(
                "MuMu 模拟器未启动", "ADB 连接未建立", "模拟器 ADB 端口配置错误"
            )
            raise EmulatorNotRunningError("No available devices")

        # 选择设备
        if self.serial == "auto":
            logger.info("Using AUTO mode to select device")
            if len(available) == 1:
                # 只有一个可用设备
                self.serial = available[0].serial
                logger.info(
                    f" Auto selected device: {self.serial} (only one available)"
                )
            # MuMu 12 识别
            elif len(available) == 2:
                # 处理 MuMu12: 127.0.0.1:7555 和 127.0.0.1:16XXX
                logger.info("Found 2 devices, checking for MuMu12 device pair...")
                # 检查是否有 MuMu12 端口 (16xxx)
                mumu12_devices = [d for d in available if d.is_mumu12_family]
                logger.info(f"  MuMu12 devices: {[d.serial for d in mumu12_devices]}")
                # 检查是否有 MuMu 端口 (7555)
                has_7555 = any(d.serial == "127.0.0.1:7555" for d in available)
                logger.info(f"  Has 7555 port: {has_7555}")

                if mumu12_devices and has_7555:
                    # MuMu12 设备对,忽略 7555 使用 16xxx
                    self.serial = mumu12_devices[0].serial
                    logger.info(
                        f" Auto selected MuMu12 device: {self.serial} (ignoring 7555)"
                    )
                else:
                    # 多于 2 个设备,要求手动在 config 文件里指定 serial
                    logger.error(
                        f"Multiple devices found but not MuMu12 pair: {[d.serial for d in available]}"
                    )
                    logger.error(
                        "Please specify device serial in config file (Emulator.Serial)"
                    )
                    raise RequestHumanTakeover("Please specify device serial in config")
            else:
                logger.error(
                    f"Multiple devices found ({len(available)}): {[d.serial for d in available]}"
                )
                logger.error("AUTO mode cannot decide which device to use")
                logger.error(
                    "Please specify device serial in config file (Emulator.Serial)"
                )
                raise RequestHumanTakeover("Please specify device serial in config")
        else:  # self.serial != "auto"
            # 验证指定的设备是否存在
            if not any(d.serial == self.serial for d in available):
                logger.error(f"Device {self.serial} not found in available devices")
                possible_reasons(
                    f"设备 {self.serial} 未连接", "模拟器未启动", "配置的设备序列号错误"
                )
                raise EmulatorNotRunningError(f"Device {self.serial} not found")

        # MuMu12 7555 端口重定向
        if self.serial == "127.0.0.1:7555":
            mumu12_devices = [d for d in available if d.is_mumu12_family]
            if len(mumu12_devices) == 1:
                emu_serial = mumu12_devices[0].serial
                logger.warning(f"Redirect MuMu12 {self.serial} to {emu_serial}")
                self.serial = emu_serial
            elif len(mumu12_devices) >= 2:
                logger.warning(f"Multiple MuMu12 serial found, cannot redirect")

        # MuMu12 动态端口追踪 (16384被占用时切换到16385等)
        current_device = None
        for d in available:
            if d.serial == self.serial:
                current_device = d
                break

        if current_device and current_device.is_mumu12_family:
            # 检查是否精确匹配（即检查它是否真的在列表里）
            matched = False
            for device in available:
                if device.is_mumu12_family and device.port == current_device.port:
                    matched = True
                    break

            if not matched:
                # 端口切换,尝试相邻端口 (±2范围内)
                for device in available:
                    if device.is_mumu12_family:
                        port_diff = device.port - current_device.port
                        if -2 <= port_diff <= 2:
                            # 自动“修正” self.serial 到新的端口
                            logger.info(
                                f"MuMu12 serial switched {self.serial} -> {device.serial}"
                            )
                            self.serial = device.serial
                            break

        logger.info(f"Selected device: {self.serial}")

    def adb_connect(self):
        """
        连接到 ADB 设备（连接模拟器）
        """
        logger.hr("Connecting to device", level=2)

        # 断开 offline 设备
        devices = self.list_device()
        for device in devices:
            if device.status == "offline":
                logger.warning(f"Device {device.serial} is offline, disconnect it")
                try:
                    self.adb_client.disconnect(device.serial)
                except Exception as e:
                    logger.warning(f"Failed to disconnect offline device: {e}")

        # 如果是网络设备，尝试连接
        if ":" in self.serial and not self.serial.startswith("emulator-"):
            for trial in range(3):
                try:
                    logger.info(f"Connecting to {self.serial} (trial {trial + 1}/3)")
                    self.adb_client.connect(self.serial)
                    time.sleep(1)
                    break
                except Exception as e:
                    logger.warning(f"Connection failed: {e}")
                    error_msg = str(e)

                    if trial >= 2:
                        # MuMu12 特殊处理: 端口冲突时尝试相邻端口
                        if "(10061)" in error_msg:
                            # 连接被拒绝
                            logger.error(
                                "Connection refused - emulator may not be running or port is occupied"
                            )

                            # 如果是 MuMu12,尝试暴力连接相邻端口
                            current_device = AdbDeviceWithStatus(
                                self.adb_client, self.serial, "unknown"
                            )
                            if current_device.is_mumu12_family:
                                logger.info("Trying adjacent MuMu12 ports...")
                                port = current_device.port
                                serial_list = [
                                    f"127.0.0.1:{port + offset}"
                                    for offset in [1, -1, 2, -2]
                                ]
                                for alt_serial in serial_list:
                                    try:
                                        logger.info(f"Trying {alt_serial}")
                                        self.adb_client.connect(alt_serial)
                                        time.sleep(1)
                                        self.serial = alt_serial
                                        logger.info(
                                            f"Connected to alternative port: {alt_serial}"
                                        )
                                        break
                                    except Exception as alt_e:
                                        logger.debug(
                                            f"Failed to connect to {alt_serial}: {alt_e}"
                                        )
                                        continue
                                else:
                                    # 所有端口都失败
                                    raise EmulatorNotRunningError(
                                        f"Failed to connect to {self.serial} and adjacent ports"
                                    )
                            else:
                                raise EmulatorNotRunningError(
                                    f"Failed to connect to {self.serial}"
                                )
                        else:
                            raise
                    time.sleep(2)

        # 获取设备对象
        try:
            self.adb = self.adb_client.device(serial=self.serial)
            logger.info(f"Connected to device: {self.serial}")
        except Exception as e:
            logger.error(f"Failed to get device: {e}")
            raise EmulatorNotRunningError(f"Device {self.serial} not accessible")

    def detect_package(self):
        """
        检测游戏包名（找游戏 --> config.Emulator_PackageName）
        """
        logger.hr("Detecting package", level=2)

        # 获取所有已安装的包
        try:
            result = self.adb_shell(["pm", "list", "packages"])
            packages = [
                line.replace("package:", "").strip()
                for line in result.split("\n")
                if line.startswith("package:")
            ]
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
            raise

        # 查找公主连结包
        all_valid_packages = VALID_PACKAGE
        for package in packages:
            if package in all_valid_packages:
                self.package = package
                set_server(package)
                logger.info(f"Detected package: {package}")
                return

        # 未找到包
        logger.error("PCR package not found")
        possible_reasons("游戏未安装", "包名不在支持列表中", "模拟器中未安装公主连结")
        raise RequestHumanTakeover("PCR package not installed")

    def adb_forward(self, remote):
        """
        创建ADB端口转发

        Args:
            remote (str): 设备端地址，如 'tcp:53516'

        Returns:
            int: PC端端口号
        """
        port = 0

        # 检查是否已存在转发，复用或清理
        for forward in self.adb.forward_list():
            if (
                forward.serial == self.serial
                and forward.remote == remote
                and forward.local.startswith("tcp:")
            ):
                if not port:
                    logger.info(f"Reuse forward: {forward}")
                    port = int(forward.local[4:])
                else:
                    logger.info(f"Remove redundant forward: {forward}")
                    self.adb_forward_remove(forward.local)

        # 如果已有端口，直接返回
        if port:
            return port

        # 创建新的端口转发
        port = random.randint(
            self.config.FORWARD_PORT_RANGE[0], self.config.FORWARD_PORT_RANGE[1]
        )
        forward = ForwardItem(self.serial, f"tcp:{port}", remote)
        logger.info(f"Create forward: {forward}")
        self.adb.forward(forward.local, forward.remote)
        return port

    def adb_forward_remove(self, local):
        """
        移除ADB端口转发

        Args:
            local (str): PC端地址，如 'tcp:2437'
        """
        try:
            with self.adb_client._connect() as c:
                list_cmd = f"host-serial:{self.serial}:killforward:{local}"
                c.send_command(list_cmd)
                c.check_okay()
        except AdbError as e:
            msg = str(e)
            if re.search(r"listener .*? not found", msg):
                logger.warning(f"{type(e).__name__}: {msg}")
            else:
                raise

    def adb_push(self, local, remote):
        """
        推送文件到设备

        Args:
            local (str): 本地文件路径
            remote (str): 设备文件路径

        Returns:
            str: 命令输出
        """
        cmd = ["push", local, remote]
        return self.adb_command(cmd)

    @property
    def is_mumu_over_version_356(self) -> bool:
        """
        判断是否为 MuMu12 >= 3.5.6 版本
        该版本具有 nemud.app_keep_alive 属性且始终为竖屏设备
        MuMu PRO (Mac) 具有相同特性
        """
        # 只针对MuMu12模拟器 (端口范围 16384-17408)
        if not (16384 <= self.port <= 17408):
            return False
        # 假设MuMu12都是较新版本
        return True

    @property
    def port(self) -> int:
        """获取设备端口号"""
        try:
            return int(self.serial.split(":")[1])
        except (IndexError, ValueError):
            return 0

    @cached_property
    def u2(self):
        """uiautomator2实例"""
        return u2.connect(self.serial)

    _orientation_description = {
        0: "Normal",
        1: "HOME key on the right",
        2: "HOME key on the top",
        3: "HOME key on the left",
    }
    orientation = 0

    def get_orientation(self):
        """
        获取设备旋转方向

        Returns:
            int:
                0: 'Normal'
                1: 'HOME key on the right'
                2: 'HOME key on the top'
                3: 'HOME key on the left'
        """
        _DISPLAY_RE = re.compile(
            r".*DisplayViewport{.*valid=true, .*orientation=(?P<orientation>\d+), .*deviceWidth=(?P<width>\d+), deviceHeight=(?P<height>\d+).*"
        )
        output = self.adb_shell(["dumpsys", "display"])

        res = _DISPLAY_RE.search(output, 0)

        if res:
            o = int(res.group("orientation"))
            if o in Connection._orientation_description:
                pass
            else:
                o = 0
                logger.warning(f"Invalid device orientation: {o}, assume it is normal")
        else:
            o = 0
            logger.warning("Unable to get device orientation, assume it is normal")

        self.orientation = o
        logger.attr(
            "Device Orientation",
            f'{o} ({Connection._orientation_description.get(o, "Unknown")})',
        )
        return o

    @staticmethod
    def sleep(second):
        """
        Args:
            second(int, float, tuple): 固定时间或随机范围，如 (1, 2) 表示 1-2 秒之间随机
        """
        time.sleep(ensure_time(second))
>>>>>>> Stashed changes
=======
"""
设备连接管理
"""

import re
import subprocess
import time
import random
import platform

import uiautomator2 as u2
from adbutils import AdbClient, AdbDevice, AdbTimeout, ForwardItem
from adbutils.errors import AdbError

from module.base.decorator import cached_property
from module.config.config import PriconneConfig
from module.config.server import VALID_PACKAGE, set_server
from module.device.method.adb import Adb
from module.device.method.utils import RETRY_TRIES, retry_sleep, possible_reasons
from module.exception import EmulatorNotRunningError, RequestHumanTakeover
from module.logger import logger
from module.base.utils import ensure_time


class AdbDeviceWithStatus(AdbDevice):
    """带状态的 ADB 设备"""

    def __init__(self, client: AdbClient, serial: str, status: str):
        self.status = status
        super().__init__(client, serial)

    def __str__(self):
        return f"AdbDevice({self.serial}, {self.status})"

    __repr__ = __str__

    def __bool__(self):
        return True

    @property
    def port(self) -> int:
        """获取设备端口"""
        try:
            return int(self.serial.split(":")[1])
        except (IndexError, ValueError):
            return 0

    @property
    def is_mumu12_family(self):
        """是否为 MuMu12 系列模拟器 (端口范围 16384-17408)"""
        return 16384 <= self.port <= 17408

    @property
    def is_mumu_family(self):
        """是否为 MuMu 系列模拟器"""
        return self.serial == "127.0.0.1:7555" or self.is_mumu12_family


class Connection(Adb):
    """
    设备连接类
    """

    config: PriconneConfig

    @staticmethod
    def _find_adb():
        """查找 adb 可执行文件"""
        import os
        import shutil

        # 优先使用 PATH 中的 adb
        adb_in_path = shutil.which("adb")
        if adb_in_path:
            return adb_in_path

        # 常见的 adb 路径
        possible_paths = [
            # MuMu12 模拟器
            r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
            r"D:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
            # MuMu 模拟器
            r"C:\Program Files\Netease\MuMu Player 12\shell\adb.exe",
            # 雷电模拟器
            r"C:\leidian\LDPlayer9\adb.exe",
            # 搞机工具箱
            os.path.expanduser(r"~\Documents\搞机工具箱10.1.0\搞机工具箱10.1.0\adb.exe"),
            # Android SDK
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found adb at: {path}")
                return path

        # 默认使用 adb，期望在 PATH 中
        return "adb"

    def __init__(self, config):
        """
        Args:
            config: 配置对象
        """
        super().__init__()
        self.config = config
        # ADB 可执行文件路径 - 尝试多个位置
        self.adb_binary = self._find_adb()
        self.serial = config.Emulator_Serial
        self.package = config.Emulator_PackageName

        # 初始化 ADB 客户端
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)

        # 检测设备
        self.detect_device()

        # 连接设备
        self.adb_connect()
        logger.attr("AdbDevice", self.adb)

        # 检测包名
        if self.package == "auto":
            self.detect_package()
        else:
            set_server(self.package)
        logger.attr("PackageName", self.package)

    def adb_command(self, cmd, timeout=10):
        """
        执行 ADB 命令
        Args:
            cmd (list): 命令列表
            timeout (int): 超时时间（秒）
        Returns:
            str: 命令输出
        """
        cmd = list(map(str, cmd))
        cmd = [self.adb_binary, "-s", self.serial] + cmd

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f'Command timeout: {" ".join(cmd)}')
            raise
        except Exception as e:
            logger.error(f'Command failed: {" ".join(cmd)}, error: {e}')
            raise

    def adb_shell(self, cmd, stream=False, recvall=True, timeout=10, rstrip=True):
        """
        执行 ADB shell 命令
        Args:
            cmd (list, str): 命令列表或字符串
            stream (bool): 返回流而非字符串输出 (默认: False)
            recvall (bool): 当stream=True时接收所有数据 (默认: True)
            timeout (int): 超时时间 (默认: 10)
            rstrip (bool): 去除最后的空行 (默认: True)
        Returns:
            str if stream=False
            bytes if stream=True and recvall=True
            socket if stream=True and recvall=False
        """
        if not isinstance(cmd, str):
            cmd = list(map(str, cmd))

        if stream:
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            if recvall:
                # bytes
                from module.device.method.utils import recv_all

                return recv_all(result)
            else:
                # socket
                return result
        else:
            # str - 普通字符串输出
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            from module.device.method.utils import remove_shell_warning

            result = remove_shell_warning(result)
            return result

    def subprocess_run(self, cmd, timeout=10):
        """
        运行子进程命令
        Args:
            cmd (list): 命令列表
            timeout (int): 超时时间
        Returns:
            str: 命令输出
        """
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Subprocess failed: {e}")
            raise

    def adb_start_server(self):
        """启动 ADB 服务器"""
        logger.info("Starting ADB server")
        try:
            subprocess.run([self.adb_binary, "start-server"], timeout=10)
            time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to start ADB server: {e}")

    def adb_disconnect(self):
        """
        断开 ADB 连接
        """
        msg = self.adb_client.disconnect(self.serial)
        if msg:
            logger.info(msg)
        # 释放缓存资源
        from module.base.decorator import del_cached_property

        del_cached_property(self, "u2")

    def adb_restart(self):
        """
        重启 ADB 服务器
        """
        logger.info("Restart adb server")
        # 杀掉当前 ADB 服务器
        self.adb_client.server_kill()
        # 重新创建 ADB 客户端
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)
        # 释放缓存资源
        from module.base.decorator import del_cached_property

        del_cached_property(self, "u2")

    def adb_reconnect(self):
        """
        重新连接 ADB（重连模拟器）
        """
        logger.info("Reconnecting to ADB device")

        if self.config.Emulator_AdbRestart and len(self.list_device()) == 0:
            # 重启 ADB 服务器（当检测不到设备且配置开启时）
            self.adb_restart()
            # 连接设备
            self.adb_connect()
            self.detect_device()
        else:
            # 只断开重连（不重启 ADB 服务器）
            self.adb_disconnect()
            self.adb_connect()
            self.detect_device()

    def list_device(self):
        """
        列出所有可用设备
        """
        try:
            devices = []
            # 使用 ADB 协议获取设备状态
            with self.adb_client._connect() as c:
                c.send_command("host:devices")
                c.check_okay()
                output = c.read_string_block()
                for line in output.splitlines():
                    parts = line = line.strip().split("\t")
                    if len(parts) != 2:
                        continue

                    serial, status = parts[0].strip(), parts[1].strip()

                    # 无效序列号
                    if not serial or serial == "(no serial number)":
                        logger.warning(f"Skipping device with invalid serial: {serial}")
                        continue

                    # 创建带状态的设备对象
                    device = AdbDeviceWithStatus(self.adb_client, serial, status)
                    devices.append(device)
                    logger.info(f"Found device: {serial} ({status})")

            return devices
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    def detect_device(self):
        """
        检测并选择设备（找模拟器）
        """
        logger.hr("Detecting device", level=2)
        logger.info(
            f"Current config: Serial='{self.serial}', PackageName='{self.package}'"
        )

        for attempt in range(2):
            devices = self.list_device()
            available = [d for d in devices if d.status == "device"]
            logger.info(f"Found {len(devices)} devices total")
            logger.info(f"Available devices: {[d.serial for d in available]}")

            if available:
                break  # 找到了可用的设备，跳出循环

            # 如果是 Windows + auto + 无设备，尝试 brute force connect
            if (
                self.serial == "auto"
                and platform.system() == "Windows"
                and attempt == 0
            ):
                logger.info("Attempting brute-force ADB connect for MuMu12...")
                # 连接 MuMu12 的默认端口
                for port in [16384, 16385, 16386, 16387, 16388]:
                    try:
                        self.adb_client.connect(f"127.0.0.1:{port}")
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Failed to connect 127.0.0.1:{port}: {e}")
                # 再次 list_device，如果已经开启了 mumu12，并且使用了上面的默认接口，应该能找到设备
                continue

        # 指定了 serial
        if ":" in self.serial and not self.serial.startswith("emulator-"):
            try:
                logger.info(f"Attempting to connect to {self.serial}")
                self.adb_client.connect(self.serial)  # 连接指定的设备
                time.sleep(1)
            except Exception as e:
                logger.debug(f"Initial connect failed: {e}")

        # 获取“最终”的设备列表
        devices = self.list_device()
        logger.info(f"Found {len(devices)} devices total")

        # 显示所有设备的详细信息
        if devices:
            for idx, d in enumerate(devices, 1):
                logger.info(f"  [{idx}] {d.serial} - Status: {d.status}")

        # 过滤可用设备
        available = [d for d in devices if d.status == "device"]
        logger.info(f"Available devices (status='device'): {len(available)}")

        if not available:
            logger.error("No available devices found")
            # 检查配置，看是否允许“重启ADB”
            if self.config.Emulator_AdbRestart:
                logger.info("Attempting to restart ADB server")
                self.adb_start_server()  # 重启 ADB
                devices = self.list_device()
                available = [d for d in devices if d.status == "device"]
                logger.info(f"After restart: {len(available)} available devices")

        if not available:
            logger.critical("No devices available")
            possible_reasons(
                "MuMu 模拟器未启动", "ADB 连接未建立", "模拟器 ADB 端口配置错误"
            )
            raise EmulatorNotRunningError("No available devices")

        # 选择设备
        if self.serial == "auto":
            logger.info("Using AUTO mode to select device")
            if len(available) == 1:
                # 只有一个可用设备
                self.serial = available[0].serial
                logger.info(
                    f" Auto selected device: {self.serial} (only one available)"
                )
            # MuMu 12 识别
            elif len(available) == 2:
                # 处理 MuMu12: 127.0.0.1:7555 和 127.0.0.1:16XXX
                logger.info("Found 2 devices, checking for MuMu12 device pair...")
                # 检查是否有 MuMu12 端口 (16xxx)
                mumu12_devices = [d for d in available if d.is_mumu12_family]
                logger.info(f"  MuMu12 devices: {[d.serial for d in mumu12_devices]}")
                # 检查是否有 MuMu 端口 (7555)
                has_7555 = any(d.serial == "127.0.0.1:7555" for d in available)
                logger.info(f"  Has 7555 port: {has_7555}")

                if mumu12_devices and has_7555:
                    # MuMu12 设备对,忽略 7555 使用 16xxx
                    self.serial = mumu12_devices[0].serial
                    logger.info(
                        f" Auto selected MuMu12 device: {self.serial} (ignoring 7555)"
                    )
                else:
                    # 多于 2 个设备,要求手动在 config 文件里指定 serial
                    logger.error(
                        f"Multiple devices found but not MuMu12 pair: {[d.serial for d in available]}"
                    )
                    logger.error(
                        "Please specify device serial in config file (Emulator.Serial)"
                    )
                    raise RequestHumanTakeover("Please specify device serial in config")
            else:
                logger.error(
                    f"Multiple devices found ({len(available)}): {[d.serial for d in available]}"
                )
                logger.error("AUTO mode cannot decide which device to use")
                logger.error(
                    "Please specify device serial in config file (Emulator.Serial)"
                )
                raise RequestHumanTakeover("Please specify device serial in config")
        else:  # self.serial != "auto"
            # 验证指定的设备是否存在
            if not any(d.serial == self.serial for d in available):
                logger.error(f"Device {self.serial} not found in available devices")
                possible_reasons(
                    f"设备 {self.serial} 未连接", "模拟器未启动", "配置的设备序列号错误"
                )
                raise EmulatorNotRunningError(f"Device {self.serial} not found")

        # MuMu12 7555 端口重定向
        if self.serial == "127.0.0.1:7555":
            mumu12_devices = [d for d in available if d.is_mumu12_family]
            if len(mumu12_devices) == 1:
                emu_serial = mumu12_devices[0].serial
                logger.warning(f"Redirect MuMu12 {self.serial} to {emu_serial}")
                self.serial = emu_serial
            elif len(mumu12_devices) >= 2:
                logger.warning(f"Multiple MuMu12 serial found, cannot redirect")

        # MuMu12 动态端口追踪 (16384被占用时切换到16385等)
        current_device = None
        for d in available:
            if d.serial == self.serial:
                current_device = d
                break

        if current_device and current_device.is_mumu12_family:
            # 检查是否精确匹配（即检查它是否真的在列表里）
            matched = False
            for device in available:
                if device.is_mumu12_family and device.port == current_device.port:
                    matched = True
                    break

            if not matched:
                # 端口切换,尝试相邻端口 (±2范围内)
                for device in available:
                    if device.is_mumu12_family:
                        port_diff = device.port - current_device.port
                        if -2 <= port_diff <= 2:
                            # 自动“修正” self.serial 到新的端口
                            logger.info(
                                f"MuMu12 serial switched {self.serial} -> {device.serial}"
                            )
                            self.serial = device.serial
                            break

        logger.info(f"Selected device: {self.serial}")

    def adb_connect(self):
        """
        连接到 ADB 设备（连接模拟器）
        """
        logger.hr("Connecting to device", level=2)

        # 断开 offline 设备
        devices = self.list_device()
        for device in devices:
            if device.status == "offline":
                logger.warning(f"Device {device.serial} is offline, disconnect it")
                try:
                    self.adb_client.disconnect(device.serial)
                except Exception as e:
                    logger.warning(f"Failed to disconnect offline device: {e}")

        # 如果是网络设备，尝试连接
        if ":" in self.serial and not self.serial.startswith("emulator-"):
            for trial in range(3):
                try:
                    logger.info(f"Connecting to {self.serial} (trial {trial + 1}/3)")
                    self.adb_client.connect(self.serial)
                    time.sleep(1)
                    break
                except Exception as e:
                    logger.warning(f"Connection failed: {e}")
                    error_msg = str(e)

                    if trial >= 2:
                        # MuMu12 特殊处理: 端口冲突时尝试相邻端口
                        if "(10061)" in error_msg:
                            # 连接被拒绝
                            logger.error(
                                "Connection refused - emulator may not be running or port is occupied"
                            )

                            # 如果是 MuMu12,尝试暴力连接相邻端口
                            current_device = AdbDeviceWithStatus(
                                self.adb_client, self.serial, "unknown"
                            )
                            if current_device.is_mumu12_family:
                                logger.info("Trying adjacent MuMu12 ports...")
                                port = current_device.port
                                serial_list = [
                                    f"127.0.0.1:{port + offset}"
                                    for offset in [1, -1, 2, -2]
                                ]
                                for alt_serial in serial_list:
                                    try:
                                        logger.info(f"Trying {alt_serial}")
                                        self.adb_client.connect(alt_serial)
                                        time.sleep(1)
                                        self.serial = alt_serial
                                        logger.info(
                                            f"Connected to alternative port: {alt_serial}"
                                        )
                                        break
                                    except Exception as alt_e:
                                        logger.debug(
                                            f"Failed to connect to {alt_serial}: {alt_e}"
                                        )
                                        continue
                                else:
                                    # 所有端口都失败
                                    raise EmulatorNotRunningError(
                                        f"Failed to connect to {self.serial} and adjacent ports"
                                    )
                            else:
                                raise EmulatorNotRunningError(
                                    f"Failed to connect to {self.serial}"
                                )
                        else:
                            raise
                    time.sleep(2)

        # 获取设备对象
        try:
            self.adb = self.adb_client.device(serial=self.serial)
            logger.info(f"Connected to device: {self.serial}")
        except Exception as e:
            logger.error(f"Failed to get device: {e}")
            raise EmulatorNotRunningError(f"Device {self.serial} not accessible")

    def detect_package(self):
        """
        检测游戏包名（找游戏 --> config.Emulator_PackageName）
        """
        logger.hr("Detecting package", level=2)

        # 获取所有已安装的包
        try:
            result = self.adb_shell(["pm", "list", "packages"])
            packages = [
                line.replace("package:", "").strip()
                for line in result.split("\n")
                if line.startswith("package:")
            ]
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
            raise

        # 查找公主连结包
        all_valid_packages = VALID_PACKAGE
        for package in packages:
            if package in all_valid_packages:
                self.package = package
                set_server(package)
                logger.info(f"Detected package: {package}")
                return

        # 未找到包
        logger.error("PCR package not found")
        possible_reasons("游戏未安装", "包名不在支持列表中", "模拟器中未安装公主连结")
        raise RequestHumanTakeover("PCR package not installed")

    def adb_forward(self, remote):
        """
        创建ADB端口转发

        Args:
            remote (str): 设备端地址，如 'tcp:53516'

        Returns:
            int: PC端端口号
        """
        port = 0

        # 检查是否已存在转发，复用或清理
        for forward in self.adb.forward_list():
            if (
                forward.serial == self.serial
                and forward.remote == remote
                and forward.local.startswith("tcp:")
            ):
                if not port:
                    logger.info(f"Reuse forward: {forward}")
                    port = int(forward.local[4:])
                else:
                    logger.info(f"Remove redundant forward: {forward}")
                    self.adb_forward_remove(forward.local)

        # 如果已有端口，直接返回
        if port:
            return port

        # 创建新的端口转发
        port = random.randint(
            self.config.FORWARD_PORT_RANGE[0], self.config.FORWARD_PORT_RANGE[1]
        )
        forward = ForwardItem(self.serial, f"tcp:{port}", remote)
        logger.info(f"Create forward: {forward}")
        self.adb.forward(forward.local, forward.remote)
        return port

    def adb_forward_remove(self, local):
        """
        移除ADB端口转发

        Args:
            local (str): PC端地址，如 'tcp:2437'
        """
        try:
            with self.adb_client._connect() as c:
                list_cmd = f"host-serial:{self.serial}:killforward:{local}"
                c.send_command(list_cmd)
                c.check_okay()
        except AdbError as e:
            msg = str(e)
            if re.search(r"listener .*? not found", msg):
                logger.warning(f"{type(e).__name__}: {msg}")
            else:
                raise

    def adb_push(self, local, remote):
        """
        推送文件到设备

        Args:
            local (str): 本地文件路径
            remote (str): 设备文件路径

        Returns:
            str: 命令输出
        """
        cmd = ["push", local, remote]
        return self.adb_command(cmd)

    @property
    def is_mumu_over_version_356(self) -> bool:
        """
        判断是否为 MuMu12 >= 3.5.6 版本
        该版本具有 nemud.app_keep_alive 属性且始终为竖屏设备
        MuMu PRO (Mac) 具有相同特性
        """
        # 只针对MuMu12模拟器 (端口范围 16384-17408)
        if not (16384 <= self.port <= 17408):
            return False
        # 假设MuMu12都是较新版本
        return True

    @property
    def port(self) -> int:
        """获取设备端口号"""
        try:
            return int(self.serial.split(":")[1])
        except (IndexError, ValueError):
            return 0

    @cached_property
    def u2(self):
        """uiautomator2实例"""
        return u2.connect(self.serial)

    _orientation_description = {
        0: "Normal",
        1: "HOME key on the right",
        2: "HOME key on the top",
        3: "HOME key on the left",
    }
    orientation = 0

    def get_orientation(self):
        """
        获取设备旋转方向

        Returns:
            int:
                0: 'Normal'
                1: 'HOME key on the right'
                2: 'HOME key on the top'
                3: 'HOME key on the left'
        """
        _DISPLAY_RE = re.compile(
            r".*DisplayViewport{.*valid=true, .*orientation=(?P<orientation>\d+), .*deviceWidth=(?P<width>\d+), deviceHeight=(?P<height>\d+).*"
        )
        output = self.adb_shell(["dumpsys", "display"])

        res = _DISPLAY_RE.search(output, 0)

        if res:
            o = int(res.group("orientation"))
            if o in Connection._orientation_description:
                pass
            else:
                o = 0
                logger.warning(f"Invalid device orientation: {o}, assume it is normal")
        else:
            o = 0
            logger.warning("Unable to get device orientation, assume it is normal")

        self.orientation = o
        logger.attr(
            "Device Orientation",
            f'{o} ({Connection._orientation_description.get(o, "Unknown")})',
        )
        return o

    @staticmethod
    def sleep(second):
        """
        Args:
            second(int, float, tuple): 固定时间或随机范围，如 (1, 2) 表示 1-2 秒之间随机
        """
        time.sleep(ensure_time(second))
>>>>>>> Stashed changes
