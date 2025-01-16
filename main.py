'''公主连结公会战自动脚本'''

import warnings
warnings.filterwarnings('ignore', category=Warning)

# pip install opencv-python pillow pyautogui airtest
from airtest.core.api import touch, exists, Template, init_device, start_app, stop_app
from airtest.core.settings import Settings as ST
import logging
import subprocess
import time

# 设置 airtest 日志级别为 ERROR
ST.LOG_FILE = "log.txt"
logging.getLogger("airtest").setLevel(logging.ERROR)

ADB_PATH = "/opt/homebrew/bin/adb"
device_uuid = "127.0.0.1:5555"

# 连接模拟器
device = init_device(platform="android", uuid=device_uuid)

app_icon = Template(r"static/app_icon.png")
game_activity = "com.bilibili.priconne/.MainActivity"
package_name = "com.bilibili.priconne"

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
    print(f"【ADB】dumpsys window结果: {result}")
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

def main():
    try:
        if not check_adb_connection():
            print("【错误】ADB 连接失败，请检查模拟器是否正常运行")
            return

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

        # time.sleep(5)
        # if not close_game():
        #     print("【错误】游戏关闭失败")
        #     return

    except Exception as e:
        print(f"【错误】程序异常: {str(e)}")

if __name__ == "__main__":
    main()