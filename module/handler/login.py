"""
登录处理器
"""

from module.base.timer import Timer
from module.handler.assets import *
from module.logger import logger
from module.ui.ui import UI
from module.ui.assets import *


class LoginHandler(UI):
    """
    登录处理器
    """

    def __init__(self, config, device=None):
        """
        Args:
            config: 配置对象
            device: 设备对象
        """
        super().__init__(config, device)

    def app_start(self):
        """
        启动应用并处理登录
        """
        logger.hr("App start", level=1)

        # 启动游戏
        self.device.app_start()

        # 处理登录流程
        self.handle_app_login()

    def app_stop(self):
        """
        停止应用
        """
        logger.hr("App stop", level=1)
        self.device.app_stop()

    def app_restart(self):
        """
        重启应用
        """
        logger.hr("App restart", level=1)
        self.device.app_stop()
        self.device.app_start()
        self.handle_app_login()

    def handle_app_login(self):
        """
        处理登录流程

        Raises:
            GameStuckError: 界面卡住超过60秒
            GameTooManyClickError: 点击循环
            GameNotRunningError: 应用已挂掉
        """
        logger.hr("App login", level=1)

        confirm_timer = Timer(1.5, count=4).start()
        safe_click_timer = Timer(1.0).start()
        login_success = False  # 标记是否检测到真正的启动

        # 清空记录
        self.device.stuck_record_clear()
        self.device.click_record_clear()

        while 1:
            self.device.screenshot()

            # 检查是否进入主界面
            if self._is_in_main():
                # logger.info("In main")
                if confirm_timer.reached():
                    logger.info("Login to main confirmed")
                    break
            else:
                # logger.info("Not in main, trying again")
                confirm_timer.reset()

            # 检测登录按钮
            if self.appear(LOGIN_CHECK, interval=5):
                logger.info("Login check button detected - clicking")
                self.device.click(LOGIN_CHECK)
                if not login_success:
                    logger.info("Login success - this is a real app start")
                    login_success = True  # 标记为真启动
                continue

            # 处理公告弹窗
            if self.appear(ANNOUNCE_CLOSE, interval=5):
                logger.info("Closing announcement")
                self.device.click(ANNOUNCE_CLOSE)
                continue

            # 检查主页面按钮
            if self.appear(GO_TO_MAIN, interval=5):
                logger.info("Go to main button detected - clicking")
                self.device.click(GO_TO_MAIN)
                continue

            # # 处理卡池播放动画
            # if safe_click_timer.reached() and not self.is_in_main():
            #     logger.info('Click safe area to skip animation')
            #     self.device.click_adb(1278, 713)
            #     safe_click_timer.reset()

        return True

    def _is_in_main(self) -> bool:
        """
        检查是否在主界面

        Returns:
            bool: 是否在主界面
        """
        return self.appear(主界面检查, offset=(30, 30))
