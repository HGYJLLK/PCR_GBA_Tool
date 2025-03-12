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