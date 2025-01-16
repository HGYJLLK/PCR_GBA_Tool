# main.py
"""主程序入口"""
from core.device import DeviceManager
from core.game.training import TrainingOperation
from templates import APP_ICON, SWIPE_ICON1
from utils.logger import logger
import time


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

        # 初始化游戏操作
        training = TrainingOperation()

        # 检查游戏运行状态并启动
        if device_manager.check_game_activity():
            logger.info("游戏已在运行中")
        else:
            logger.info("游戏未运行，准备启动")
            if training.click_icon(icon=APP_ICON):
                logger.info("游戏启动成功")
                time.sleep(5)
            else:
                logger.error("游戏启动失败")
                return

        # 进入训练场
        # training.enter_training_area()

        # 进入boss战
        # training.click_icon(SWIPE_ICON1)

    except Exception as e:
        logger.error(f"程序异常: {str(e)}")


if __name__ == "__main__":
    main()