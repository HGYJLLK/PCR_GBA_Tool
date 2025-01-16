'''公主连结公会战自动脚本'''

import warnings
warnings.filterwarnings('ignore', category=Warning)

# pip install opencv-python pillow pyautogui airtest
from airtest.core.api import touch, exists, Template, init_device, start_app, stop_app,swipe
from airtest.core.settings import Settings as ST
import logging
import subprocess
import time
import platform

# 设置 airtest 日志级别为 ERROR
ST.LOG_FILE = "log.txt"
logging.getLogger("airtest").setLevel(logging.ERROR)

MAC_ADB_PATH = "/opt/homebrew/bin/adb"
WINDOWS_ADB_PATH = "D:/浏览器/platform-tools_r31.0.2-windows/platform-tools/adb.exe"
ADB_PATH = ''
device_uuid = "127.0.0.1:5555"

app_icon = Template(r"static/app_icon.png")
mx_icon = Template(r"static/mx.png")
zcd_icon = Template(r"static/zcd.png")
xlc_icon = Template(r"static/xlc.png")
swipe_icon = Template(r"static/spider.png")
swipe_icon1 = Template(r"static/spider1.png")

# 游戏Activity名和包名
game_activity = "com.bilibili.priconne/.MainActivity"
package_name = "com.bilibili.priconne"

# 连接模拟器
def connect_device():
    """连接模拟器"""
    try:
        device = init_device(platform="android",uuid = device_uuid)
        print(f"【设备】连接成功: {device}")
        return device
    except Exception as e:
        print(f"【错误】连接失败: {str(e)}")
        return None

def run_adb_command(command):
    """执行 ADB 命令"""
    try:
        full_command = f'"{ADB_PATH}" {command}'
        print(f"【ADB】执行命令: {full_command}")
        if '|' in command:
            process = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if error:
                print(f"【警告】命令执行产生警告: {error}")
            return output
        else:
            result = subprocess.check_output(full_command, shell=True, text=True, stderr=subprocess.PIPE)
            return result
    except subprocess.CalledProcessError as e:
        print(f"【错误】ADB 命令执行失败: {str(e)}")
        if e.stderr:
            print(f"错误详情: {e.stderr}")
        return None

def click_icon(icon):
    """启动游戏"""
    retry_count = 0
    while retry_count < 3:
        if exists(icon):
            result = exists(icon)
            print(f"【操作】找到游戏图标，坐标：{result}")
            x, y = result
            touch((x, y))
            return True
        retry_count += 1
        time.sleep(2)
    print("【错误】未能找到游戏图标")
    return False

def check_game_activity():
    """检测游戏是否在运行"""
    result = run_adb_command(f'-s {device_uuid} shell dumpsys window | grep "mFocusedApp"')
    print(f"【ADB】dumpsys 结果: {result}")
    if result and game_activity in result:
        return True
    return False

def check_adb_connection():
    """检查ADB连接状态"""
    try:
        result = run_adb_command(f'-s {device_uuid} devices')
        print(f"【ADB】devices结果: {result}")
        return device_uuid in result and "device" in result
    except:
        return False

# 进入训练场
def enter_training_area():
    """30s内每2s检测一次是否有xlc_icon图标出现，如果出现则点击进入游戏"""
    retry_count = 0
    # 1166,698
    while retry_count < 15:
        if exists(xlc_icon):
            result = exists(xlc_icon)
            print(f"【操作】找到xlc图标，坐标：{result}")
            x, y = result
            touch((x, y))
            time.sleep(1)
            if not exists(xlc_icon):
                print("【状态】进入主界面成功")
                break
        else:
            print("【状态】未找到xlc图标")
            touch((1166, 698))
            time.sleep(2)
        retry_count += 1

def close_game():
    """关闭游戏"""
    try:
        if check_game_activity():
            result = run_adb_command(f'-s {device_uuid} shell am force-stop {package_name}')
            print("【状态】关闭游戏成功")
            return True
        else:
            print("【状态】游戏已经是关闭状态")
            return True
    except Exception as e:
        print(f"【错误】关闭游戏失败: {str(e)}")
        return False

def scroll_and_select_icon(swipe_icon,target_icon):
    """滑动屏幕并选择目标图标"""
    result = exists(swipe_icon)
    print(f"【操作】找到滑动图标，坐标：{result}")
    x, y = result
    touch((x, y))
    time.sleep(1)
    # swipe_count = 0
    # max_swipes = 5
    # while swipe_count < max_swipes:
    #     if exists(target_icon):
    #         result = exists(target_icon)
    #         print(f"【操作】找到目标图标，坐标：{result}")
    #         x, y = result
    #         touch((x, y))
    #         time.sleep(1)
    #         if not exists(target_icon):
    #             print("【状态】选择目标图标成功")
    #             return True
    #     elif (swipe_count%2) == 0:
    #         swipe((1228,223), (1228,467))
    #     else:
    #         swipe((1228,467), (1228,223))
    #     swipe_count += 1
    # print(f"【错误】未找到目标图标，已尝试{max_swipes}次")
    # return False

# 检测当前操作系统
def check_os():
    """获取当前操作系统"""
    current_os = platform.system()
    print(f"【系统】当前操作系统：{current_os}")
    return current_os

def main():
    try:
        global ADB_PATH
        # 连接模拟器
        device = connect_device()
        if device is None:
            print("【错误】连接模拟器失败，请检查模拟器是否正常运行")
            return

        # 获取 ADB 路径
        current_os = check_os()
        if current_os == "Windows":
            ADB_PATH = WINDOWS_ADB_PATH
        elif current_os == "Mac":
            ADB_PATH = MAC_ADB_PATH
        else:
            print("【错误】当前操作系统不支持")
            return

        # 检查 ADB 连接
        if not check_adb_connection():
            print("【错误】ADB 连接失败，请检查模拟器是否正常运行")
            return

        # 检查游戏运行状态
        if check_game_activity():
            print("【状态】游戏已在运行中")
        else:
            print("【状态】游戏未运行，准备启动")
            if click_icon(icon=app_icon):
                print("【状态】游戏启动成功")
                time.sleep(5)
            else:
                print("【错误】游戏启动失败")
                return
        
        # 进入训练场
        enter_training_area()

        # 进入boss
        scroll_and_select_icon(swipe_icon1,app_icon)

    except Exception as e:
        print(f"【错误】程序异常: {str(e)}")

if __name__ == "__main__":
    main()