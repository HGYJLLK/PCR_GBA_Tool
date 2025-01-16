"""基础配置文件"""

# ADB路径配置
MAC_ADB_PATH = "/opt/homebrew/bin/adb"
WINDOWS_ADB_PATH = "D:/浏览器/platform-tools_r31.0.2-windows/platform-tools/adb.exe"

# 设备配置
DEVICE_UUID = "127.0.0.1:5555"

# 游戏配置
GAME_ACTIVITY = "com.bilibili.priconne/.MainActivity"
PACKAGE_NAME = "com.bilibili.priconne"

# 确保这些变量可以被导出
__all__ = [
    'MAC_ADB_PATH',
    'WINDOWS_ADB_PATH',
    'DEVICE_UUID',
    'GAME_ACTIVITY',
    'PACKAGE_NAME'
]