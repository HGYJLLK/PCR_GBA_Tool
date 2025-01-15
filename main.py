'''公主连结公会战自动脚本'''

# pip install opencv-python pillow pyautogui airtest
from airtest.core.api import touch,exists,Template,init_device,start_app,stop_app
from airtest.core.settings import Settings as ST
import logging
import subprocess
import time

# 设置 airtest 日志级别为 ERROR，这样可以减少大量 DEBUG 信息
ST.LOG_FILE = "log.txt"  # 将日志输出到文件
logging.getLogger("airtest").setLevel(logging.ERROR)

ADB_PATH = "D:/浏览器/platform-tools_r31.0.2-windows/platform-tools/adb.exe"
device_uuid = "127.0.0.1:16384"

# 连接mumu模拟器
device = init_device(platform="android",uuid = device_uuid)

app_icon = Template(r"static/app_icon.png")
# 游戏Activity名和包名
game_activity = "com.bilibili.priconne/.MainActivity"
package_name = "com.bilibili.priconne"

def run_adb_command(command):
    """执行 ADB 命令"""
    try:
        full_command = f'"{ADB_PATH}" {command}'
        print(f"【ADB】执行命令: {full_command}")
        result = subprocess.check_output(full_command, shell=True, text=True, stderr=subprocess.DEVNULL)
        return result
    except subprocess.CalledProcessError as e:
        print(f"【错误】ADB 命令执行失败: {str(e)}")
        return None

def click_icon(icon):
    """启动游戏"""
    retry_count = 0
    while retry_count < 3:  # 最多尝试3次
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
    result = run_adb_command(f'-s {device_uuid} shell dumpsys window | findstr "mFocusedApp"')
    print(f"【ADB】dumpsys window结果: {result}")
    if game_activity in result:
        return True
    else:
        return False

def check_adb_connection():
    """检查ADB连接状态"""
    try:
        result = run_adb_command(f'-s {device_uuid} devices')
        print(f"【ADB】devices结果: {result}")
        return device_uuid in result and "device" in result
    except:
        return False

# 关闭游戏
def close_game():
    try:
        # 先检查游戏是否在运行
        if check_game_activity():
            # 使用 force-stop 命令强制停止应用
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
                time.sleep(5)  # 等待游戏启动
            else:
                print("【错误】游戏启动失败")
                return

        # 等待一段时间后关闭游戏
        time.sleep(5)
        if not close_game():
            print("【错误】游戏关闭失败")
            return

    except Exception as e:
        print(f"【错误】程序异常: {str(e)}")

if __name__ == "__main__":
    main()