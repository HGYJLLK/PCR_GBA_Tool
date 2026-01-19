"""
UI 导航处理器
"""

from module.base.timer import Timer
from module.logger import logger
from module.exception import GameNotRunningError, GamePageUnknownError
from module.base.base import ModuleBase
from module.ui.page import Page, page_main
from module.ui.assets import *
from module.base.decorator import run_once


class UI(ModuleBase):
    """
    UI 导航类
    """

    ui_current: Page = None

    def ui_page_appear(self, page, offset=(30, 30), interval=0):
        """
        检测页面是否出现

        Args:
            page (Page): 页面对象
            offset (tuple): 检测偏移量
            interval (int): 检测间隔

        Returns:
            bool: 页面是否出现
        """
        return self.appear(page.check_button, offset=offset, interval=interval)

    def is_in_main(self, offset=(30, 30), interval=0):
        """
        检查是否在主界面

        Returns:
            bool: 是否在主界面
        """
        return self.ui_page_appear(page_main, offset=offset, interval=interval)

    def ui_get_current_page(self, skip_first_screenshot=True):
        """
        获取当前所在页面

        Args:
            skip_first_screenshot (bool): 是否跳过第一次截图

        Returns:
            Page: 当前页面对象

        Raises:
            GamePageUnknownError: 无法识别当前页面
        """
        logger.info("UI get current page")

        @run_once
        def app_check():
            if not self.device.app_is_running():
                raise GameNotRunningError("Game not running")

        orientation_timer = Timer(5)
        timeout = Timer(10, count=20).start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
                if not self.device.has_cached_image:
                    self.device.screenshot()
            else:
                self.device.screenshot()

            # End
            if timeout.reached():
                break

            # 遍历Page上所有的页面（主页、任务、商店...）
            for page in Page.iter_pages():
                if page.check_button is None:
                    logger.debug(f"Page {page.name} has no check_button")
                    continue
                # 找每个页面的按钮
                if self.ui_page_appear(page=page):
                    logger.attr("UI", page.name)
                    self.ui_current = page
                    return page

            # Unknown page but able to handle
            logger.info("Unknown ui page")

            if self.appear_then_click(GO_TO_MAIN, offset=(30, 30), interval=2):
                timeout.reset()
                continue

            app_check()
            if orientation_timer.reached():
                self.device.get_orientation()
                orientation_timer.reset()

        # Unknown page, need manual switching
        logger.warning("Unknown ui page")
        logger.warning("Starting from current page is not supported")
        logger.warning(f"Supported page: {[str(page) for page in Page.iter_pages()]}")
        logger.critical("Please switch to a supported page before starting PCR")
        raise GamePageUnknownError

    def ui_goto(self, destination, offset=(30, 30), skip_first_screenshot=True):
        """
        导航到指定页面

        Args:
            destination (Page): 目标页面
            offset (tuple): 点击偏移量
            skip_first_screenshot (bool): 是否跳过第一次截图
        """
        # Destination page is different from current page
        logger.hr(f"UI goto {destination}")

        # “GPS”：计算从当前位置到“目标位置”的“点击路径”
        Page.init_connection(destination)  # 使用A*算法计算路径

        # Wait to confirm
        confirm_timer = Timer(0.3, count=1).start()

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
                if not self.device.has_cached_image:
                    self.device.screenshot()
            else:
                self.device.screenshot()

            # 检查是否到达目标位置
            if self.ui_page_appear(destination):
                if confirm_timer.reached():
                    break
            else:
                confirm_timer.reset()

            # 查找当前位置
            # logger.debug(f"[ui_goto] Starting page detection loop")
            for page in Page.iter_pages():
                if page.parent is None or page.check_button is None:
                    continue
                # logger.debug(
                #     f"[ui_goto] Checking page: {page.name}, check_button={page.check_button}"
                # )
                if self.ui_page_appear(page=page):
                    # 下一步从哪里到哪里
                    logger.info(f"UI page switch: {page} -> {page.parent}")
                    # 找到去`page.parent`的按钮
                    button = page.links[page.parent]
                    # logger.debug(f"[ui_goto] Clicking button: {button}")
                    # 点击按钮
                    self.device.click(button)
                    confirm_timer.reset()
                    break
                # else:
                #     # logger.debug("[ui_goto] No page matched in this loop")

        logger.info(f"Arrive {destination}")
        self.ui_current = destination

    def ui_ensure(self, destination, skip_first_screenshot=True):
        """
        确保在指定页面，如果不在则导航过去

        Args:
            destination (Page): 目标页面
            skip_first_screenshot (bool): 是否跳过第一次截图

        Returns:
            bool: 是否进行了导航
        """
        logger.hr(f"UI ensure {destination}")
        self.ui_get_current_page(skip_first_screenshot=skip_first_screenshot)

        if self.ui_current == destination:
            logger.info(f"Already at {destination}")
            return False
        else:
            logger.info(f"Goto {destination}")
            self.ui_goto(destination, skip_first_screenshot=True)
            return True

    def ui_process_check_button(self, check_button, offset=(30, 30)):
        """
        Args:
            check_button (Button, callable, list[Button], tuple[Button]):
            offset:

        Returns:
            bool:
        """
        # Button对象
        if isinstance(check_button, Button):
            return self.appear(check_button, offset=offset)
        # 函数/方法
        elif callable(check_button):
            return check_button()
        # 列表/元组
        elif isinstance(check_button, (list, tuple)):
            # 目标页面可能有多种状态 (比如 "有活动时的界面" 和 "没活动时的界面")
            for button in check_button:
                # 只要匹配其中任意一个
                if self.appear(button, offset=offset):
                    return True
            return False
        # 默认是 Button
        else:
            return self.appear(check_button, offset=offset)

    def ui_click(
        self,
        click_button,
        check_button,
        appear_button=None,
        additional=None,
        confirm_wait=1,
        offset=(30, 30),
        retry_wait=10,
        skip_first_screenshot=False,
    ):
        """
        通用的点击并等待确认方法

        Args:
            click_button (Button): 要点击的按钮
            check_button (Button, callable): 检查按钮或方法
            appear_button (Button, callable): 出现按钮或方法，默认与 click_button 相同
            additional (callable): 额外的处理函数
            confirm_wait (int, float): 确认等待时间
            offset (tuple): 检测偏移量
            retry_wait (int, float): 重试等待时间
            skip_first_screenshot (bool): 是否跳过第一次截图
        """
        logger.hr("UI click")
        if appear_button is None:
            appear_button = click_button

        click_timer = Timer(retry_wait, count=retry_wait // 0.5)
        confirm_wait = confirm_wait if additional is not None else 0
        confirm_timer = Timer(confirm_wait, count=confirm_wait // 0.5).start()

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.ui_process_check_button(check_button, offset=offset):
                if confirm_timer.reached():
                    break
            else:
                confirm_timer.reset()

            # 点击按钮
            if click_timer.reached():
                if (isinstance(appear_button, Button) and self.appear(appear_button, offset=offset)) or (
                        callable(appear_button) and appear_button()
                ):
                    self.device.click(click_button)
                    click_timer.reset()
                    continue

            # 其他弹窗处理
            if additional is not None:
                if additional():
                    continue
