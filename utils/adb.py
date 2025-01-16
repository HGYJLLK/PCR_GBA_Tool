# utils/adb.py
"""ADB工具类"""
import subprocess
import platform
from setting import MAC_ADB_PATH, WINDOWS_ADB_PATH, DEVICE_UUID
from utils.logger import logger


class ADBTool:
    def __init__(self):
        self.adb_path = self._get_adb_path()

    def _get_adb_path(self):
        """获取ADB路径"""
        current_os = platform.system()
        logger.info(f"当前操作系统: {current_os}")  # 添加日志

        if current_os == "Windows":
            return WINDOWS_ADB_PATH
        elif current_os == "Darwin":  # platform.system() 在 Mac 上返回 "Darwin"
            return MAC_ADB_PATH
        else:
            logger.warning(f"未识别的操作系统: {current_os}")  # 添加警告日志
            return MAC_ADB_PATH  # 默认返回 MAC 路径而不是抛出错误

    def run_command(self, command):
        """执行ADB命令"""
        try:
            full_command = f'"{self.adb_path}" {command}'
            logger.info(f"执行ADB命令: {full_command}")

            if '|' in command:
                process = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True)
                output, error = process.communicate()
                if error:
                    logger.warning(f"命令执行产生警告: {error}")
                return output
            else:
                result = subprocess.check_output(full_command, shell=True, text=True,
                                                 stderr=subprocess.PIPE)
                return result
        except subprocess.CalledProcessError as e:
            logger.error(f"ADB命令执行失败: {str(e)}")
            return None