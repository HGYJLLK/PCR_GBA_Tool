"""
滚动控制模块
"""

import numpy as np
import cv2

from module.base.base import ModuleBase
from module.base.button import Button
from module.base.timer import Timer
from module.base.utils import random_rectangle_point
from module.logger import logger


def color_similarity_2d(image, color):
    """
    计算图像每个像素与目标颜色的相似度

    Args:
        image: 2D array (numpy array or PIL Image)
        color: (r, g, b) 目标颜色

    Returns:
        np.ndarray: uint8 类型，相似度矩阵
    """
    diff = cv2.subtract(image, (*color, 0))
    r, g, b = cv2.split(diff)
    cv2.max(r, g, dst=r)
    cv2.max(r, b, dst=r)
    positive = r
    cv2.subtract((*color, 0), image, dst=diff)
    r, g, b = cv2.split(diff)
    cv2.max(r, g, dst=r)
    cv2.max(r, b, dst=r)
    negative = r
    cv2.add(positive, negative, dst=positive)
    cv2.subtract(255, positive, dst=positive)
    return positive


def rgb2gray(image):
    """
    RGB 转灰度图

    Args:
        image: RGB 图像

    Returns:
        np.ndarray: 灰度图
    """
    r, g, b = cv2.split(image)
    maximum = cv2.max(r, g)
    cv2.min(r, g, dst=r)
    cv2.max(maximum, b, dst=maximum)
    cv2.min(r, b, dst=r)
    cv2.convertScaleAbs(maximum, alpha=0.5, dst=maximum)
    cv2.convertScaleAbs(r, alpha=0.5, dst=r)
    cv2.add(maximum, r, dst=maximum)
    return maximum


class Scroll:
    """
    滚动条控制类
    """

    color_threshold = 221  # 颜色匹配阈值
    drag_threshold = 0.05  # 拖动误差容忍度 (5%)
    edge_threshold = 0.05  # 边缘检测阈值 (5%)
    edge_add = (0.3, 0.5)  # 边缘附加值

    def __init__(self, area, color, name="Scroll", swipe_area=None):
        """
        初始化滚动控制器

        Args:
            area (Button, tuple): 滚动条区域或 Button 对象
            color (tuple): 滚动条颜色 RGB 值
            name (str): 滚动条名称，用于日志
            swipe_area (tuple): 列表区域滑动 (x1, y1, x2, y2)
        """
        if isinstance(area, Button):
            name = area.name
            area = area.area
        self.area = area
        self.color = color
        self.name = name
        self.swipe_area = swipe_area
        self.total = self.area[3] - self.area[1]
        # Just default value, will change in match_color()
        self.length = self.total / 2
        self.drag_interval = Timer(1, count=2)
        self.drag_timeout = Timer(5, count=10)

    def match_color(self, main):
        """
        检测滚动条滑块位置

        Args:
            main (ModuleBase): ModuleBase 实例

        Returns:
            np.ndarray: 布尔数组，True 表示滑块位置
        """
        image = main.image_crop(self.area, copy=False) # 截取滚动条区域
        image = color_similarity_2d(image, color=self.color) # 找到滚动条区域中所有接近“滑块颜色”的像素
        mask = np.max(image, axis=1) > self.color_threshold # 将每“行”的颜色匹配结果压缩为“是”或“否”
        self.length = np.sum(mask) # 计算“滑块”有多长 (有多少行匹配成功)
        return mask

    def cal_position(self, main):
        """
        计算当前滚动位置

        Args:
            main (ModuleBase): ModuleBase 实例

        Returns:
            float: 0.0-1.0
        """
        mask = self.match_color(main)
        middle = np.mean(np.where(mask)[0]) # 计算“滑块”中心位置
        # 计算百分比位置
        position = (middle - self.length / 2) / (self.total - self.length)
        position = position if position > 0 else 0.0 # 0.0 = 顶部
        position = position if position < 1 else 1.0 # 1.0 = 底部
        logger.attr(
            self.name,
            f"{position:.2f} ({middle}-{self.length / 2})/({self.total}-{self.length})",
        )
        return position

    def position_to_screen(self, position, random_range=(-0.05, 0.05)):
        """
        将滚动位置转换为屏幕坐标

        Args:
            position (int, float): 0.0-1.0
            random_range (tuple): 随机偏移范围

        Returns:
            tuple[int]: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
        """
        position = np.add(position, random_range)
        middle = position * (self.total - self.length) + self.length / 2
        middle = middle.astype(int)
        middle += self.area[1]
        while np.max(middle) >= 720:
            middle -= 2
        while np.min(middle) <= 0:
            middle += 2
        area = (self.area[0], middle[0], self.area[2], middle[1])
        return area

    def appear(self, main):
        """
        检测滚动条是否出现

        Args:
            main (ModuleBase): ModuleBase 实例

        Returns:
            bool: 滚动条是否可见
        """
        return np.mean(self.match_color(main)) > 0.1

    def at_top(self, main):
        """
        检测是否在顶部
        """
        mask = self.match_color(main) # 查找滑块
        if np.sum(mask) == 0:
            return False
        # 检查滚动条起始位置是否在轨道顶部
        matched_rows = np.where(mask)[0] # 获取滑块所有 y 坐标
        return matched_rows[0] <= 3

    def at_bottom(self, main):
        """
        检测是否在底部
        """
        mask = self.match_color(main)
        if np.sum(mask) == 0:
            return False
        # 检查滚动条结束位置是否在轨道底部
        matched_rows = np.where(mask)[0]
        return matched_rows[-1] >= self.total - 3

    def set(
        self,
        position,
        main,
        random_range=(-0.05, 0.05),
        distance_check=True,
        skip_first_screenshot=True,
    ):
        """
        滚动到指定位置

        Args:
            position (float, int): 目标位置 0.0-1.0
            main (ModuleBase): ModuleBase 实例
            random_range (tuple): 随机偏移范围
            distance_check (bool): 是否检查滑动距离
            skip_first_screenshot (bool): 是否跳过首次截图

        Returns:
            int: 拖动次数
        """
        logger.info(f"{self.name} set to {position}")
        self.drag_interval.clear()
        self.drag_timeout.reset()
        dragged = 0
        if position <= self.edge_threshold:
            random_range = np.subtract(0, self.edge_add)
        if position >= 1 - self.edge_threshold:
            random_range = self.edge_add

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                main.device.screenshot()

            # 计算当前位置
            current = self.cal_position(main)
            # logger.info(
            #     f"{self.name} current position: {current:.3f}, target: {position:.3f}, diff: {abs(position - current):.3f}"
            # )
            # 判断是否到达目标位置
            if abs(position - current) < self.drag_threshold:
                logger.info(f"{self.name} reached target position")
                break
            if self.length:
                self.drag_timeout.reset()
            else:
                if self.drag_timeout.reached():
                    logger.warning("Scroll disappeared, assume scroll set")
                    break
                else:
                    logger.warning(
                        f"{self.name} length is 0, waiting for scroll to appear..."
                    )
                    continue

            # 滑动
            if self.drag_interval.reached():
                # 计算“滑块”的当前坐标 p1
                p1 = random_rectangle_point(self.position_to_screen(current), n=1)
                # 计算“滑块”的目标坐标 p2
                p2 = random_rectangle_point(
                    self.position_to_screen(position, random_range=random_range), n=1
                )
                distance = np.linalg.norm(np.subtract(p1, p2))
                logger.info(
                    f"{self.name} swipe from {p1} to {p2}, distance: {distance:.1f}px"
                )
                main.device.swipe(p1, p2, name=self.name, distance_check=distance_check)
                self.drag_interval.reset()
                dragged += 1

        logger.info(f"{self.name} dragged {dragged} times")
        return dragged

    def set_top(self, main, random_range=(-0.05, 0.05), skip_first_screenshot=True):
        """
        滚动到顶部
        """
        return self.set(
            0.00,
            main=main,
            random_range=random_range,
            skip_first_screenshot=skip_first_screenshot,
        )

    def set_bottom(self, main, random_range=(-0.05, 0.05), skip_first_screenshot=True):
        """
        滚动到底部
        """
        return self.set(
            1.00,
            main=main,
            random_range=random_range,
            skip_first_screenshot=skip_first_screenshot,
        )

    def drag_page(
        self, page, main, random_range=(-0.05, 0.05), skip_first_screenshot=True
    ):
        """
        向前或向后拖动翻页

        Args:
            page (int, float): 相对位置，1.0 表示下一页，-1.0 表示上一页
            main (ModuleBase): ModuleBase 实例
            random_range (tuple): 随机偏移范围
            skip_first_screenshot (bool): 是否跳过首次截图

        Returns:
            int: 拖动次数
        """
        if not skip_first_screenshot:
            main.device.screenshot()

        # 提供 swipe_area ---> 使用列表区域滑动
        if self.swipe_area:
            return self._drag_page_in_area(page, main)

        # 滚动条拖动
        current = self.cal_position(main)

        multiply = self.length / (self.total - self.length)
        target = current + page * multiply
        target = round(min(max(target, 0), 1), 3)
        return self.set(
            target, main=main, random_range=random_range, skip_first_screenshot=True
        )

    def _drag_page_in_area(self, page, main):
        """
        在列表区域滑动翻页

        Args:
            page (float): 翻页系数，正数向下，负数向上
            main (ModuleBase): ModuleBase 实例

        Returns:
            int: 1 (已滑动)
        """
        # 计算滑动距离
        # page = 0.8 表示滑动 80% 的可见高度
        area_height = self.swipe_area[3] - self.swipe_area[1]
        distance = int(page * area_height)

        # 在列表区域内随机选择起点和终点
        x1, y1, x2, y2 = self.swipe_area

        # 起点：在区域中间偏下（向上滑）或中间偏上（向下滑）
        if page < 0:  # 向上翻页（向上滑动）
            # 起点在下方，终点在上方
            start_y = int(y1 + area_height * 0.7)
            end_y = start_y + distance  # distance 是负数
        else:  # 向下翻页（向下滑动）
            # 起点在上方，终点在下方
            start_y = int(y1 + area_height * 0.3)
            end_y = start_y + distance  # distance 是正数

        # X 坐标在区域中心附近随机
        center_x = (x1 + x2) // 2
        import random

        start_x = center_x + random.randint(-5, 5)
        end_x = center_x + random.randint(-5, 5)

        # 确保坐标在区域内
        start_y = max(y1, min(y2, start_y))
        end_y = max(y1, min(y2, end_y))

        logger.info(
            f"{self.name} swipe in area from ({start_x}, {start_y}) to ({end_x}, {end_y})"
        )

        # 执行滑动
        main.device.swipe(
            (start_x, start_y),
            (end_x, end_y),
            duration=(0.2, 0.3),
            name=f"{self.name}_DRAG_PAGE",
        )

        main.device.sleep(0.3)  # 等待动画
        return 1

    def next_page(
        self, main, page=0.8, random_range=(-0.01, 0.01), skip_first_screenshot=True
    ):
        """
        向下翻页 (向后翻页)
        """
        return self.drag_page(
            page,
            main=main,
            random_range=random_range,
            skip_first_screenshot=skip_first_screenshot,
        )

    def prev_page(
        self, main, page=0.8, random_range=(-0.01, 0.01), skip_first_screenshot=True
    ):
        """
        向上翻页 (向前翻页)
        """
        return self.drag_page(
            -page,
            main=main,
            random_range=random_range,
            skip_first_screenshot=skip_first_screenshot,
        )
