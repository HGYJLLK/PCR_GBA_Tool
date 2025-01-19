"""主程序入口 - 公主连结R自动化助手"""
from core.device import DeviceManager
from core.game.training import TrainingOperation
from core.templates import GameTemplates
from utils.logger import logger
import time

# 公主连结R国服包名
GAME_PACKAGE = "com.bilibili.priconne"

def print_menu():
    """打印操作菜单"""
    print("\n===============公主连结R助手===============")
    print("1. 进入训练场")
    print("2. 重启游戏")
    print("0. 退出程序")
    print("===========================================")
    print("请输入对应数字进行操作: ", end='')

def main():
    try:
        # 初始化设备管理器
        device_manager = DeviceManager()

        # 连接设备
        if not device_manager.connect_device():
            logger.error("连接模拟器失败，请检查模拟器是否正常运行")
            return

        # 检查ADB连接
        if not device_manager.check_connection():
            logger.error("ADB连接失败，请检查模拟器是否正常运行")
            return

        # 初始化模板和游戏操作
        templates = GameTemplates()
        training = TrainingOperation()

        while True:
            print_menu()

            try:
                choice = int(input())
            except ValueError:
                logger.error("输入无效，请输入数字")
                continue

            if choice == 0:
                logger.info("程序退出")
                break

            elif choice == 1:
                # 检查游戏是否运行
                if not device_manager.check_game_activity():
                    logger.info("游戏未运行，准备启动")
                    if training.click_icon(icon=templates.app_icon):
                        logger.info("游戏启动成功")
                        time.sleep(15)  # 增加启动等待时间
                    else:
                        logger.error("游戏启动失败")
                        continue

                # 进入训练场前等待游戏加载
                logger.info("等待游戏完全加载...")
                time.sleep(10)  # 额外等待游戏加载

                # 进入训练场
                if not training.enter_training_area():
                    logger.error("进入训练场失败，可能是未找到图标")
                    continue

            elif choice == 2:
                # 重启游戏
                logger.info("准备重启游戏")
                try:
                    # 强制停止游戏
                    device_manager.device.shell(f'am force-stop {GAME_PACKAGE}')
                    logger.info("游戏已停止")
                    time.sleep(5)  # 增加停止等待时间

                    # 重新启动游戏
                    if training.click_icon(icon=templates.app_icon):
                        logger.info("游戏重启成功")
                        time.sleep(15)  # 增加启动等待时间
                    else:
                        logger.error("游戏启动失败")
                except Exception as e:
                    logger.error(f"重启游戏失败: {str(e)}")

            else:
                logger.error("无效的选项，请重新输入")

            # 每个操作后暂停一下，让用户看清输出
            time.sleep(1)

    except Exception as e:
        logger.error(f"程序异常: {str(e)}")

    finally:
        logger.info("正在清理资源...")

if __name__ == "__main__":
    main()