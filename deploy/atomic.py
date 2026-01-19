"""
Atomic file operations.
"""

import os
import tempfile
import shutil
from typing import Union


def atomic_read_text(file_path: str, encoding: str = "utf-8") -> str:
    """
    读取文本文件

    Args:
        file_path: 文件路径
        encoding: 文件编码

    Returns:
        str: 文件内容，文件不存在时返回空字符串
    """
    try:
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:
        return ""


def atomic_read_bytes(file_path: str) -> bytes:
    """
    读取二进制文件

    Args:
        file_path: 文件路径

    Returns:
        bytes: 文件内容，文件不存在时返回空字节
    """
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return b""
    except Exception as e:
        return b""


def atomic_write(
    file_path: str, content: Union[str, bytes], encoding: str = "utf-8"
) -> None:
    """
    写入文件（使用临时文件）

    Args:
        file_path: 目标文件路径
        content: 要写入的内容
        encoding: 文件编码
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 根据内容类型选择写入模式
    if isinstance(content, str):
        mode = "w"
    else:
        mode = "wb"
        encoding = None

    # 写入临时文件
    with tempfile.NamedTemporaryFile(
        mode=mode, delete=False, encoding=encoding, dir=os.path.dirname(file_path)
    ) as f:
        f.write(content)
        f_path = f.name

    try:
        # 移动临时文件到目标位置
        shutil.move(f_path, file_path)
    except Exception as e:
        # 清理临时文件
        try:
            os.unlink(f_path)
        except:
            pass
        raise e
