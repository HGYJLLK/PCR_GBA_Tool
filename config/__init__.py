"""配置模块"""
# 直接指定导入的变量名
from .setting import MAC_ADB_PATH, WINDOWS_ADB_PATH, DEVICE_UUID, GAME_ACTIVITY, PACKAGE_NAME
from templates import APP_ICON, MX_ICON, ZCD_ICON, XLC_ICON, SWIPE_ICON, SWIPE_ICON1

__all__ = [
    'MAC_ADB_PATH', 
    'WINDOWS_ADB_PATH', 
    'DEVICE_UUID',
    'GAME_ACTIVITY', 
    'PACKAGE_NAME',
    'APP_ICON', 
    'MX_ICON', 
    'ZCD_ICON', 
    'XLC_ICON',
    'SWIPE_ICON', 
    'SWIPE_ICON1'
]