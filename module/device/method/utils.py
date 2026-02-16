"""
设备方法工具函数
"""

import time
import socket
from module.exception import RequestHumanTakeover
from adbutils import _AdbStreamConnection as AdbConnection


# 重试配置
RETRY_TRIES = 5
RETRY_DELAY = 3


class PackageNotInstalled(Exception):
    """应用包未安装"""

    pass


class ImageTruncated(Exception):
    """图像数据被截断"""

    pass


def retry_sleep(retry_count: int) -> float:
    """
    计算重试延迟时间
    Args:
        retry_count: 重试次数
    Returns:
        float: 延迟秒数
    """
    return RETRY_DELAY


def handle_adb_error(error) -> bool:
    """
    处理 ADB 错误
    Args:
        error: AdbError 异常对象
    Returns:
        bool: 是否为可重试的连接错误
    """
    error_str = str(error)
    # 连接相关错误
    if any(
        msg in error_str for msg in ["Broken pipe", "EOF occurred", "Connection reset"]
    ):
        return True
    return False


def handle_unknown_host_service(error) -> bool:
    """
    处理未知主机服务错误
    Args:
        error: AdbError 异常对象
    Returns:
        bool: 是否为 ADB 服务器未启动错误
    """
    error_str = str(error)
    return "unknown host service" in error_str.lower()


def remove_prefix(text: bytes, prefix: bytes) -> bytes:
    """
    移除字节串前缀
    Args:
        text: 原始字节串
        prefix: 要移除的前缀
    Returns:
        bytes: 移除前缀后的字节串
    """
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


def remove_shell_warning(text: str) -> str:
    """
    移除 shell 输出中的警告信息
    Args:
        text: shell 输出文本
    Returns:
        str: 清理后的文本
    """
    lines = text.split("\n")
    # 过滤掉警告行
    result_lines = [line for line in lines if not line.strip().startswith("WARNING:")]
    return "\n".join(result_lines)


def recv_all(stream, chunk_size=4096, recv_interval=0.000):
    """
    从流中接收所有数据
    Args:
        stream: 数据流对象 (AdbConnection 或 socket)
        chunk_size: 每次接收的块大小 (默认: 4096)
        recv_interval: 接收间隔 (默认: 0.000, 如果作为服务器接收使用 0.001)
    Returns:
        bytes: 接收到的所有数据
    """
    if isinstance(stream, AdbConnection):
        stream = stream.conn
        stream.settimeout(10)

    fragments = []
    while True:
        try:
            chunk = stream.recv(chunk_size)
            if chunk:
                fragments.append(chunk)
                if recv_interval:
                    time.sleep(recv_interval)
            else:
                break
        except socket.timeout:
            break

    return b"".join(fragments)


def possible_reasons(*args):
    """
    打印可能的失败原因
    """
    from module.logger import logger

    logger.info("可能的原因:")
    for reason in args:
        logger.info(f"  - {reason}")
