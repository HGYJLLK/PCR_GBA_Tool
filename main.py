"""主程序入口 - 公主连结R自动化助手"""

from core.device import DeviceManager
from core.game.goto_jjc_box import GoToJJCBox
from core.game.training import TrainingOperation
from core.templates import GameTemplates
from utils.logger import logger
from utils.environment_check import Env
from utils.game import Game
from utils.navigate import Nav
import time

# # 公主连结R国服包名
# GAME_PACKAGE = "com.bilibili.priconne"


def print_menu():
    print("\n===============公主连结R助手===============")
    print("1. 进入训练场")
    print("2. 重启游戏")
    print("3. 进入竞技场")
    print("4. 进入竞技场防守设置")
    print("5. 进入主界面")
    print("0. 退出程序")
    print("===========================================")
    print("请输入对应数字进行操作: ", end="")


def main():
    try:

        env = Env()
        device_manager = DeviceManager()
        templates = GameTemplates()  # 基础图标
        training = TrainingOperation()  # 训练场操作
        goto_jjc = GoToJJCBox(device_manager.device)  # 竞技场操作
        game = Game()  # 游戏操作
        nav = Nav()  # 导航操作

        # 获取系统信息
        sys = env.check_sys()

        # 环境检查（未来对接前端系统初始化模块）
        if not env.check_python_environment():
            return
        if not env.check_network():
            return

        # 连接模拟器
        if not device_manager.connect_device():
            logger.error("连接模拟器失败，请检查模拟器是否正常运行")
            return

        if not device_manager.check_connection():
            logger.error("ADB连接失败，请检查模拟器是否正常运行")
            return

        while True:
            print_menu()
            try:
                choice = int(input())
            except ValueError:
                logger.error("输入无效，请输入数字")
                continue

            # 游戏基础操作
            if choice == 0:
                logger.info("程序退出")
                break
            elif choice == 2:
                game.restart_game(device_manager)
                continue

            # 检查游戏运行状态，没有运行则跳过本次循环，重新输入
            if not game.ensure_game_running(device_manager, sys):
                continue

            # 功能选择
            if choice == 1:  # 训练场
                if not training.enter_training_area(templates.training_icon):
                    logger.error("进入训练场失败，可能是未找到图标")
            elif choice == 3:  # 竞技场
                try:
                    goto_jjc.navigate()
                    logger.info("成功进入竞技场")
                except Exception as e:
                    logger.error(f"进入竞技场失败: {str(e)}")
            elif choice == 5:  # 主界面
                nav.nav_to_main(device_manager, sys)
            else:
                logger.error("无效的选项，请重新输入")

            time.sleep(1)

    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
    finally:
        logger.info("正在清理资源...")


# def ensure_game_running(device_manager, templates, training):
#     """检查并确保游戏运行"""
#     if not device_manager.check_game_activity():
#         logger.info("游戏未运行，准备启动")
#         if training.click_icon(icon=templates.app_icon):
#             logger.info("游戏启动成功")
#             time.sleep(15)
#             return True
#         logger.error("游戏启动失败")
#         return False
#     return True


# def restart_game(device_manager, templates, training):
#     """重启游戏"""
#     logger.info("准备重启游戏")
#     try:
#         device_manager.device.shell(f"am force-stop {GAME_PACKAGE}")
#         logger.info("游戏已停止")
#         time.sleep(5)
#         if training.click_icon(icon=templates.app_icon):
#             logger.info("游戏重启成功")
#             time.sleep(15)
#         else:
#             logger.error("游戏启动失败")
#     except Exception as e:
#         logger.error(f"重启游戏失败: {str(e)}")


if __name__ == "__main__":
    main()
