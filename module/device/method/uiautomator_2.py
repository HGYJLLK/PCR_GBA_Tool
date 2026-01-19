"""
Uiautomator2 设备控制方法
"""

import typing as t
from dataclasses import dataclass
from subprocess import list2cmdline

from module.device.connection import Connection


@dataclass
class ProcessInfo:
    """进程信息"""

    pid: int
    ppid: int
    thread_count: int
    cmdline: str
    name: str


@dataclass
class ShellBackgroundResponse:
    """后台Shell响应"""

    success: bool
    pid: int
    description: str


class Uiautomator2(Connection):
    """Uiautomator2 设备控制类"""

    def resolution_uiautomator2(self, cal_rotation=True) -> t.Tuple[int, int]:
        """
        获取设备分辨率

        Args:
            cal_rotation: 是否根据旋转角度计算分辨率

        Returns:
            (width, height): 设备分辨率
        """
        info = self.u2.http.get("/info").json()
        w, h = info["display"]["width"], info["display"]["height"]

        if cal_rotation:
            rotation = self.get_orientation()
            if (w > h) != (rotation % 2 == 1):
                w, h = h, w

        return w, h

    def proc_list_uiautomator2(self) -> t.List[ProcessInfo]:
        """
        获取设备当前进程列表

        Returns:
            List[ProcessInfo]: 进程信息列表
        """
        resp = self.u2.http.get("/proc/list", timeout=10)
        resp.raise_for_status()

        result = [
            ProcessInfo(
                pid=proc["pid"],
                ppid=proc["ppid"],
                thread_count=proc["threadCount"],
                cmdline=(
                    " ".join(proc["cmdline"]) if proc["cmdline"] is not None else ""
                ),
                name=proc["name"],
            )
            for proc in resp.json()
        ]

        return result

    def u2_shell_background(self, cmdline, timeout=10) -> ShellBackgroundResponse:
        """
        在后台运行shell命令

        Args:
            cmdline: 命令行 (list, tuple或str)
            timeout: 超时时间(秒)

        Returns:
            ShellBackgroundResponse: Shell响应
        """
        if isinstance(cmdline, (list, tuple)):
            cmdline = list2cmdline(cmdline)
        elif isinstance(cmdline, str):
            cmdline = cmdline
        else:
            raise TypeError("cmdargs type invalid", type(cmdline))

        data = dict(command=cmdline, timeout=str(timeout))
        ret = self.u2.http.post("/shell/background", data=data, timeout=timeout + 10)
        ret.raise_for_status()

        resp = ret.json()
        resp = ShellBackgroundResponse(
            success=bool(resp.get("success", False)),
            pid=resp.get("pid", 0),
            description=resp.get("description", ""),
        )

        return resp
