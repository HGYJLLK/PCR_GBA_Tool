from module.base.button import Button
from module.base.timer import Timer
from module.base.utils import crop
from module.logger import logger
from module.config.config import PriconneConfig
from module.device.device import Device


class ModuleBase:
    """
    PCR 基础模块类
    """

    config: PriconneConfig  # 类属性类型提示，方便 IDE 自动补全
    device: Device

    def __init__(self, config, device=None):
        """
        Args:
            config: 配置对象
            device: 设备对象
        """
        self.config = config
        self.device = device
        self.interval_timer = {}

    def appear(self, button, offset=0, interval=0, similarity=0.85, threshold=10):
        """
        检查按钮是否出现

        Args:
            button (Button, Template): Button 或 Template 对象
            offset (bool, int): 检测区域偏移量
                - 0 或 False: 使用纯颜色匹配
                - True: 使用配置文件中的默认偏移量进行模板匹配
                - 整数: 使用指定偏移量进行模板匹配
            interval (int, float): 两次active事件之间的间隔时间（秒）
                - 当设置了 interval 时，即使按钮出现，也会检查距离上次返回True的时间
                - 如果时间间隔不足，返回False，避免连续快速点击
                - 例如: interval=1.0 表示两次检测到按钮之间至少间隔1秒
            similarity (int, float): 模板匹配相似度，0到1之间
            threshold (int, float): 颜色匹配阈值，0到255之间，值越小表示越相似

        Returns:
            bool: 按钮是否出现

        Examples:
            图像检测:
            ```
            self.device.screenshot()
            self.appear(Button(area=(...), color=(...), button=(...))
            self.appear(Template(file='...')
            ```
        """
        self.device.stuck_record_add(button)

        if interval:
            if button.name in self.interval_timer:
                if self.interval_timer[button.name].limit != interval:
                    self.interval_timer[button.name] = Timer(interval)
            else:
                self.interval_timer[button.name] = Timer(interval)
            if not self.interval_timer[button.name].reached():
                return False

        if offset:
            if isinstance(offset, bool):
                offset = self.config.BUTTON_OFFSET # 在 config/config.py 中定义的偏移量
            # 模版匹配
            appear = button.match(self.device.image, offset=offset, similarity=similarity)
        else:
            # 纯颜色匹配
            appear = button.appear_on(self.device.image, threshold=threshold)

        if appear and interval:
            self.interval_timer[button.name].reset()

        return appear

    def appear_then_click(
        self,
        button,
        screenshot=False,
        genre="items",
        offset=0,
        interval=0,
        similarity=0.85,
        threshold=30,
    ):
        """
        如果按钮出现则点击

        Args:
            button (Button): Button对象
            screenshot (bool): 点击前是否截图保存
            genre (str): 截图保存的类型/文件夹名
            offset (bool, int): 检测区域偏移量
            interval (int, float): 两次点击之间的间隔时间
            similarity (float): 模板匹配相似度
            threshold (int): 颜色匹配阈值

        Returns:
            bool: 是否点击了按钮
        """
        appear = self.appear(
            button,
            offset=offset,
            interval=interval,
            similarity=similarity,
            threshold=threshold,
        )
        if appear:
            if screenshot:
                self.device.sleep(self.config.WAIT_BEFORE_SAVING_SCREEN_SHOT)
                self.device.screenshot()
                self.device.save_screenshot(genre=genre)
            self.device.click(button)
        return appear

    def match_template(self, button, offset=20, similarity=0.85):
        """
        模板匹配

        Args:
            button (Button): Button对象
            offset (int, tuple): 检测区域偏移量
            similarity (float): 相似度阈值

        Returns:
            bool: 是否匹配
        """
        if not hasattr(self.device, "image") or self.device.image is None:
            logger.warning("No screenshot available")
            return False

        if not button.file:
            logger.warning(f"Button {button.name} has no template file")
            return False

        try:
            return button.match_luma(
                self.device.image, offset=offset, similarity=similarity
            )
        except Exception as e:
            logger.warning(f"Template matching failed for {button.name}: {e}")
            return False

    def image_crop(self, button, copy=True):
        """
        从当前截图中裁剪区域

        Args:
            button (Button, tuple): Button 实例或区域元组 (x1, y1, x2, y2)
            copy (bool): 是否复制图像

        Returns:
            np.ndarray: 裁剪后的图像

        Examples:
            # 使用 Button 对象
            card_image = self.image_crop(button)

            # 使用区域元组
            card_image = self.image_crop((100, 100, 200, 200))
        """
        if isinstance(button, Button):
            return crop(self.device.image, button.area, copy=copy)
        elif hasattr(button, "area"):
            return crop(self.device.image, button.area, copy=copy)
        else:
            return crop(self.device.image, button, copy=copy)
