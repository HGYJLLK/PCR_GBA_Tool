"""
Button类
"""

import os
import cv2
import numpy as np
import traceback
import imageio
from PIL import Image, ImageDraw

from module.base.utils import *
from module.logger import logger


class Button:
    """
    按钮类
    """

    def __init__(self, area, color, button, file=None, name=None):
        """
        初始化Button实例

        Args:
            area (dict[tuple], tuple): 按钮检测区域
                          (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
            color (dict[tuple], tuple): 期望的颜色值
                           (r, g, b)
            button (dict[tuple], tuple): 实际点击的区域
                            (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
            file (dict[str], str): 模板图片文件路径
            name (str): 按钮名称

        Examples:
            LOGIN_CHECK = Button(
                area=(600, 400, 680, 480),
                color=(100, 150, 255),
                button=(550, 380, 730, 500),
                file='./assets/pcr/login_check.png',
            )
        """
        self.raw_area = area
        self.raw_color = color
        self.raw_button = button
        self.raw_file = file
        self.raw_name = name

        self._button_offset = None
        self._match_init = False
        self._match_binary_init = False
        self._match_luma_init = False
        self.image = None
        self.image_binary = None
        self.image_luma = None

        # 解析属性
        self.area = self._parse_property(self.raw_area)
        self.color = self._parse_property(self.raw_color)
        self._button = self._parse_property(self.raw_button)
        self.file = self._parse_property(self.raw_file)

        if self.raw_name:
            self.name = self.raw_name
        elif self.file:
            self.name = os.path.splitext(os.path.split(self.file)[1])[0]
        else:
            self.name = "BUTTON"

    @property
    def is_gif(self):
        """判断是否为 GIF 文件"""
        if self.file:
            return os.path.splitext(self.file)[1] == ".gif"
        else:
            return False

    def _parse_property(self, data, server=None):
        """
        解析属性

        Args:
            data: 字典或元组
            server (str): 服务器标识

        Returns:
            解析后的值
        """
        if server is None:
            # 使用默认服务器
            from module.config.server import server as current_server

            server = current_server

        if isinstance(data, dict):
            return data.get(server, data.get(list(data.keys())[0]))
        else:
            return data

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self.name)

    def __bool__(self):
        return True

    @property
    def button(self):
        """返回点击区域（含偏移）"""
        if self._button_offset is None:
            return self._button
        else:
            return self._button_offset

    def appear_on(self, image, threshold=10):
        """
        颜色匹配检查按钮是否出现

        Args:
            image (np.ndarray): 截图
            threshold (int): 颜色阈值，默认10

        Returns:
            bool: 如果按钮出现返回True
        """
        return color_similar(
            color1=get_color(image, self.area), color2=self.color, threshold=threshold
        )

    def load_color(self, image):
        """
        从指定图像区域加载颜色

        Args:
            image: 截图

        Returns:
            tuple: 颜色 (r, g, b)
        """
        self.color = get_color(image, self.area)
        self.image = crop(image, self.area)
        return self.color

    def clear_offset(self):
        """清除按钮偏移"""
        self._button_offset = None

    def ensure_template(self):
        """
        加载模板图像
        """
        if not self._match_init:
            if self.is_gif:
                self.image = []
                for image in imageio.mimread(self.file):
                    image = image[:, :, :3].copy() if len(image.shape) == 3 else image
                    image = crop(image, self.area)
                    self.image.append(image)
            else:
                self.image = load_image(self.file, self.area)
                logger.debug(
                    f"Loaded template for button '{self.name}' from '{self.file}'"
                )
            self._match_init = True

    def ensure_binary_template(self):
        """
        加载二值化模板
        """
        if not self._match_binary_init:
            if self.is_gif:
                self.image_binary = []
                for image in self.image:
                    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    _, image_binary = cv2.threshold(
                        image_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
                    )
                    self.image_binary.append(image_binary)
            else:
                image_gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
                _, self.image_binary = cv2.threshold(
                    image_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
                )
            self._match_binary_init = True

    def ensure_luma_template(self):
        """
        加载亮度模板
        """
        if not self._match_luma_init:
            if self.is_gif:
                self.image_luma = []
                for image in self.image:
                    luma = rgb2luma(image)
                    self.image_luma.append(luma)
            else:
                self.image_luma = rgb2luma(self.image)
            self._match_luma_init = True

    def match(self, image, offset=30, similarity=0.85):
        """
        通过彩色模板匹配检测按钮。用于位置可能不固定的按钮。

        Args:
            image: 截图
            offset (int, tuple): 检测区域偏移
            similarity (float): 相似度阈值，0-1之间，默认0.85

        Returns:
            bool: 是否匹配成功
        """
        self.ensure_template()

        # 处理offset参数
        if isinstance(offset, tuple):
            if len(offset) == 2:
                offset = np.array((-offset[0], -offset[1], offset[0], offset[1]))
            else:
                offset = np.array(offset)
        else:
            offset = np.array((-3, -offset, 3, offset))

        # 裁剪搜索区域
        image = crop(image, offset + self.area, copy=False)

        # GIF 支持
        if self.is_gif:
            for template in self.image:
                res = cv2.matchTemplate(template, image, cv2.TM_CCOEFF_NORMED)
                _, sim, _, point = cv2.minMaxLoc(res)
                self._button_offset = area_offset(
                    self._button, offset[:2] + np.array(point)
                )
                if sim > similarity:
                    return True
            return False
        else:
            # 单张图片模板匹配
            res = cv2.matchTemplate(self.image, image, cv2.TM_CCOEFF_NORMED)
            _, sim, _, point = cv2.minMaxLoc(res)
            self._button_offset = area_offset(
                self._button, offset[:2] + np.array(point)
            )
            return sim > similarity

    def match_binary(self, image, offset=30, similarity=0.85):
        """
        通过二值化模板匹配检测按钮。用于位置可能不固定的按钮。
        此方法会在二值化后进行模板匹配。

        Args:
            image: 截图
            offset (int, tuple): 检测区域偏移
            similarity (float): 相似度阈值，0-1之间，默认0.85

        Returns:
            bool: 是否匹配成功
        """
        self.ensure_template()
        self.ensure_binary_template()

        # 处理offset参数
        if isinstance(offset, tuple):
            if len(offset) == 2:
                offset = np.array((-offset[0], -offset[1], offset[0], offset[1]))
            else:
                offset = np.array(offset)
        else:
            offset = np.array((-3, -offset, 3, offset))

        # 裁剪搜索区域
        image = crop(image, offset + self.area, copy=False)

        # GIF 支持
        if self.is_gif:
            for template in self.image_binary:
                # graying
                image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                # binarization
                _, image_binary = cv2.threshold(
                    image_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
                )
                # template matching
                res = cv2.matchTemplate(template, image_binary, cv2.TM_CCOEFF_NORMED)
                _, sim, _, point = cv2.minMaxLoc(res)
                self._button_offset = area_offset(
                    self._button, offset[:2] + np.array(point)
                )
                if sim > similarity:
                    return True
            return False
        else:
            # graying
            image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # binarization
            _, image_binary = cv2.threshold(
                image_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
            )
            # template matching
            res = cv2.matchTemplate(
                self.image_binary, image_binary, cv2.TM_CCOEFF_NORMED
            )
            _, sim, _, point = cv2.minMaxLoc(res)
            self._button_offset = area_offset(
                self._button, offset[:2] + np.array(point)
            )
            return sim > similarity

    def match_luma(self, image, offset=30, similarity=0.85):
        """
        在Y通道下进行模板匹配

        Args:
            image: 截图
            offset (int, tuple): 检测区域偏移
            similarity (float): 相似度阈值，0-1之间，默认0.85

        Returns:
            bool: 是否匹配成功
        """
        self.ensure_template()
        self.ensure_luma_template()

        # 处理offset参数
        if isinstance(offset, tuple):
            if len(offset) == 2:
                offset = np.array((-offset[0], -offset[1], offset[0], offset[1]))
            else:
                offset = np.array(offset)
        else:
            offset = np.array([-offset, -offset, offset, offset])

        # 裁剪搜索区域
        image = crop(image, offset + self.area, copy=False)

        # GIF 支持
        if self.is_gif:
            for template in self.image_luma:
                image_luma = rgb2luma(image)
                res = cv2.matchTemplate(image_luma, template, cv2.TM_CCOEFF_NORMED)
                _, sim, _, point = cv2.minMaxLoc(res)
                self._button_offset = area_offset(
                    self._button, offset[:2] + np.array(point)
                )
                if sim > similarity:
                    return True
            return False
        else:
            # 转换为灰度图
            image_luma = rgb2luma(image)
            # 模板匹配
            res = cv2.matchTemplate(image_luma, self.image_luma, cv2.TM_CCOEFF_NORMED)
            _, sim, _, point = cv2.minMaxLoc(res)
            # 计算按钮偏移
            self._button_offset = area_offset(
                self._button, offset[:2] + np.array(point)
            )
            return sim > similarity

    def match_template_color(
        self, image, offset=(20, 20), similarity=0.85, threshold=30
    ):
        """
        模版匹配 + 颜色验证

        Args:
            image: 截图
            offset (int, tuple): 检测区域偏移
            similarity (float): 模板匹配相似度，0-1之间，默认0.85
            threshold (int): 颜色匹配阈值，默认30

        Returns:
            bool: 是否匹配成功
        """
        # 模板匹配
        template_match = self.match_luma(image, offset=offset, similarity=similarity)
        # logger.debug(f"{self.name} 模板匹配结果: {template_match}")

        if template_match:
            # 颜色验证
            diff = np.subtract(self.button, self._button)[:2]
            area = area_offset(self.area, offset=diff)
            color = get_color(image, area)
            color_match = color_similar(
                color1=color, color2=self.color, threshold=threshold
            )
            # logger.debug(
            #     f"{self.name} 颜色匹配 - 实际颜色: {color}, 期望颜色: {self.color}, 匹配结果: {color_match}"
            # )
            # logger.debug(f"颜色匹配结果: {color_match}")
            return color_match
        else:
            # logger.debug(f"{self.name} 模板匹配失败")
            return False

    def crop(self, area, image=None, name=None):
        """
        相对坐标获取新按钮

        Args:
            area (tuple): 相对区域
            image (np.ndarray): 截图
            name (str): 新按钮名称

        Returns:
            Button: 新按钮对象
        """
        if name is None:
            name = self.name
        new_area = area_offset(area, offset=self.area[:2])
        new_button = area_offset(area, offset=self.button[:2])
        button = Button(
            area=new_area,
            color=self.color,
            button=new_button,
            file=self.file,
            name=name,
        )
        if image is not None:
            button.load_color(image)
        return button

    def move(self, vector, image=None, name=None):
        """
        移动按钮

        Args:
            vector (tuple): 移动向量 (x, y)
            image (np.ndarray): 截图
            name (str): 新按钮名称

        Returns:
            Button: 新按钮对象
        """
        if name is None:
            name = self.name
        new_area = area_offset(self.area, offset=vector)
        new_button = area_offset(self.button, offset=vector)
        button = Button(
            area=new_area,
            color=self.color,
            button=new_button,
            file=self.file,
            name=name,
        )
        if image is not None:
            button.load_color(image)
        return button


class ButtonGrid:
    """
    按钮网格类

    用于管理规则排列的按钮网格，角色列表

    示例:
        # 定义 7x2 的角色卡片网格
        CARD_GRIDS = ButtonGrid(
            origin=(93, 76),           # 左上角起始坐标
            delta=(167, 227),          # 单元格间距 (横向, 纵向)
            button_shape=(138, 204),   # 单个卡片大小 (宽, 高)
            grid_shape=(7, 2),         # 网格形状 (列数, 行数)
            name='CARD'
        )

        # 访问第 3 列第 1 行的卡片
        button = CARD_GRIDS[(2, 0)]
    """

    def __init__(self, origin, delta, button_shape, grid_shape, name=None):
        """
        初始化按钮网格

        Args:
            origin (tuple): 第一张卡片左上角 (x, y)
            delta (tuple): 第一张卡片左上角到第二张卡片的左上角距离 (delta_x, delta_y)
            button_shape (tuple): 单个卡片大小 (width, height)
            grid_shape (tuple): 表格一行多少列 (columns, rows)
            name (str): 网格名称
        """
        self.origin = np.array(origin)
        self.delta = np.array(delta)
        self.button_shape = np.array(button_shape)
        self.grid_shape = np.array(grid_shape)
        if name:
            self._name = name
        else:
            (filename, line_number, function_name, text) = traceback.extract_stack()[-2]
            self._name = text[: text.find("=")].strip()

    def __getitem__(self, item):
        """
        通过索引访问网格中的按钮

        Args:
            item (tuple): (column, row) 索引，从 0 开始

        Returns:
            Button: 对应位置的 Button 对象

        示例:
            button = CARD_GRIDS[(2, 1)]  # 第 3 列第 2 行
        """
        base = np.round(np.array(item) * self.delta + self.origin).astype(int)
        area = tuple(np.append(base, base + self.button_shape))
        return Button(
            area=area,
            color=(),
            button=area,
            name="%s_%s_%s" % (self._name, item[0], item[1]),
        )

    def generate(self):
        """
        遍历网格中的所有按钮

        Yields:
            tuple: (x, y, button) 三元组
        """
        for y in range(self.grid_shape[1]):
            for x in range(self.grid_shape[0]):
                yield x, y, self[x, y]

    @property
    def buttons(self):
        """
        获取所有按钮的列表

        Returns:
            list: Button 对象列表
        """
        return list([button for _, _, button in self.generate()])

    def move(self, vector, name=None):
        """
        移动整个网格

        Args:
            vector (tuple): 移动向量 (x, y)
            name (str): 新 ButtonGrid 的名称

        Returns:
            ButtonGrid: 新的 ButtonGrid 实例
        """
        if name is None:
            name = self._name
        origin = self.origin + vector
        return ButtonGrid(
            origin=origin,
            delta=self.delta,
            button_shape=self.button_shape,
            grid_shape=self.grid_shape,
            name=name,
        )

    def gen_mask(self):
        """
        生成用于调试的掩码图像

        Returns:
            PIL.Image.Image: 掩码图像，白色区域表示按钮，黑色表示背景
        """
        image = Image.new("RGB", (1280, 720), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        for button in self.buttons:
            draw.rectangle(
                (button.area[:2], button.button[2:]), fill=(255, 255, 255), outline=None
            )
        return image

    def show_mask(self):
        """
        显示掩码图像
        """
        self.gen_mask().show()

    def save_mask(self):
        """
        保存掩码图像到文件 {name}.png
        """
        self.gen_mask().save(f"{self._name}.png")
