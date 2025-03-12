def restart_game(device_manager, templates, training):
    """重启游戏"""
    logger.info("准备重启游戏")
    try:
        device_manager.device.shell(f"am force-stop {GAME_PACKAGE}")
        logger.info("游戏已停止")
        time.sleep(5)
        if training.click_icon(icon=templates.app_icon):
            logger.info("游戏重启成功")
            time.sleep(15)
        else:
            logger.error("游戏启动失败")
    except Exception as e:
        logger.error(f"重启游戏失败: {str(e)}")

通过这段代码，我能够成功的重启游戏并且进入启动界面，默认我已经登录了，我该如何进入主界面呢？我的想法是识别当前启动界面的一些图标来判断是否是启动界面，然后通过一个周期性的点击某处坐标来达到逐渐进入到主界面，然后再去检测主界面的一些图标来判断是否进入了主界面。

然后更加完善点的做法就是，先识别当前界面是否有主界面的图标，大概识别个 10次左右，如果没有的话就重启游戏然后等待一段时间进入到启动界面再通过一个周期性的点击某处坐标来逐渐进入到主界面。如果你有更好的解决方案可以告诉我，谢谢！

---

这种函数嵌套函数的做法比直接写多个并列函数好吗？

---

from utils.logger import logger
import time
from airtest.core.api import touch, exists, swipe


class Game:
    def __init__(self):
        self.GAME_PACKAGE = "com.bilibili.priconne"

    def restart_game(self, device_manager, templates):
        """重启游戏"""
        logger.info("准备重启游戏")
        try:
            device_manager.device.shell(f"am force-stop {self.GAME_PACKAGE}")
            logger.info("游戏已停止")
            time.sleep(5)
            if self.click_icon(icon=templates.app_icon):
                logger.info("游戏重启成功")
                time.sleep(15)
            else:
                logger.error("游戏启动失败")
        except Exception as e:
            logger.error(f"重启游戏失败: {str(e)}")

    def click_icon(self, icon, max_retries=10):
        """点击图标"""
        retry_count = 0
        while retry_count < max_retries:
            if exists(icon):
                pos = exists(icon)
                logger.info(f"找到图标，坐标：{pos}")
                touch(pos)
                return True
            retry_count += 1
            time.sleep(0.5)
        logger.error("未能找到图标")
        return False
报错：2025-03-12 15:54:10,905 - INFO - 准备重启游戏
2025-03-12 15:54:10,985 - INFO - 游戏已停止
2025-03-12 15:54:15,991 - ERROR - 重启游戏失败: name 'exists' is not defined

---

类里的函数无法使用导入的库的函数？
这个又可以？
"""基础游戏操作"""

from airtest.core.api import touch, exists, swipe
import time
from utils.logger import logger


class GameBase:
    @staticmethod
    def click_icon(icon, max_retries=10):
        """点击图标"""
        retry_count = 0
        while retry_count < max_retries:
            if exists(icon):
                pos = exists(icon)
                logger.info(f"找到图标，坐标：{pos}")
                touch(pos)
                return True
            retry_count += 1
            time.sleep(0.5)
        logger.error("未能找到图标")
        return False

    @staticmethod
    def swipe_screen(start_pos, end_pos):
        """滑动屏幕"""
        swipe(start_pos, end_pos)
        time.sleep(1)

@staticmethod这个有什么作用？

---

请讲得通俗易懂一些，不要太多繁琐的名词，仔细讲解@staticmethod装饰器和没有@staticmethod装饰器的函数的区别

---

from utils.logger import logger
import time
from airtest.core.api import touch, exists, swipe


class Game:
    def __init__(self):
        self.GAME_PACKAGE = "com.bilibili.priconne"

    def restart_game(self, device_manager, templates):
        """重启游戏"""
        logger.info("准备重启游戏")
        try:
            device_manager.device.shell(f"am force-stop {self.GAME_PACKAGE}")
            logger.info("游戏已停止")
            time.sleep(5)
            if self.click_icon(icon=templates.app_icon):
                logger.info("游戏重启成功")
                time.sleep(15)
            else:
                logger.error("游戏启动失败")
        except Exception as e:
            logger.error(f"重启游戏失败: {str(e)}")

    @staticmethod
    def click_icon(icon, max_retries=10):
        """点击图标"""
        retry_count = 0
        while retry_count < max_retries:
            if exists(icon):
                pos = exists(icon)
                logger.info(f"找到图标，坐标：{pos}")
                touch(pos)
                return True
            retry_count += 1
            time.sleep(0.5)
        logger.error("未能找到图标")
        return False

    @staticmethod
    def click_pos(pos):
        """点击坐标"""
        logger.info(f"点击坐标：{pos}")
        touch(pos)
        time.sleep(0.5)

    @staticmethod
    def swipe_screen(start_pos, end_pos):
        """滑动屏幕"""
        swipe(start_pos, end_pos)
        time.sleep(0.5)

因为我的restart_game方法需要用到self.GAME_PACKAGE，所以不能添加@staticmethod？

---

如果使用了@staticmethod，无法使用类的属性，那为什么还要写类呢，我直接写函数不就好了，反正都不能用 self 的属性

---

"""主程序入口 - 公主连结R自动化助手"""

from core.device import DeviceManager
from core.game.goto_jjc_box import GoToJJCBox
from core.game.training import TrainingOperation
from core.templates import GameTemplates
from utils.logger import logger
from utils.environment_check import Env
from utils.game import Game
import time

# # 公主连结R国服包名
# GAME_PACKAGE = "com.bilibili.priconne"


def print_menu():
    print("\n===============公主连结R助手===============")
    print("1. 进入训练场")
    print("2. 重启游戏")
    print("3. 进入竞技场")
    print("4. 进入竞技场防守设置")  # 新增选项
    # print("5. 进入主界面")
    print("0. 退出程序")
    print("===========================================")
    print("请输入对应数字进行操作: ", end="")


def main():
    try:
        # 环境检查（未来对接前端系统初始化模块）
        env = Env()
        if not env.check_python_environment():
            return
        if not env.check_network():
            return

        # 连接模拟器
        device_manager = DeviceManager()
        if not device_manager.connect_device():
            logger.error("连接模拟器失败，请检查模拟器是否正常运行")
            return

        if not device_manager.check_connection():
            logger.error("ADB连接失败，请检查模拟器是否正常运行")
            return

        templates = GameTemplates()  # 基础图标
        training = TrainingOperation()  # 训练场操作
        goto_jjc = GoToJJCBox(device_manager.device)  # 竞技场操作
        game = Game()  # 游戏操作

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

            # 检查游戏运行状态
            if not game.ensure_game_running(device_manager):
                continue

            # 功能选择
            if choice == 1:  # 训练场
                if not training.enter_training_area():
                    logger.error("进入训练场失败，可能是未找到图标")
            elif choice == 3:  # 竞技场
                try:
                    goto_jjc.navigate()
                    logger.info("成功进入竞技场")
                except Exception as e:
                    logger.error(f"进入竞技场失败: {str(e)}")
            else:
                logger.error("无效的选项，请重新输入")

            time.sleep(1)

    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
    finally:
        logger.info("正在清理资源...")


def ensure_game_running(device_manager, templates, training):
    """检查并确保游戏运行"""
    if not device_manager.check_game_activity():
        logger.info("游戏未运行，准备启动")
        if training.click_icon(icon=templates.app_icon):
            logger.info("游戏启动成功")
            time.sleep(15)
            return True
        logger.error("游戏启动失败")
        return False
    return True

这段代码中，# 检查游戏运行状态             if not game.ensure_game_running(device_manager):                 continuez这一段代码是不是没有意义？