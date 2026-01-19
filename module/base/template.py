"""
动态位置的小模板图识别
"""

import os
import imageio
import cv2
import numpy as np

from module.base.button import Button
from module.base.decorator import cached_property
from module.base.resource import Resource
from module.base.utils import Points, area_offset, load_image, rgb2luma


class Template(Resource):
    """
    Template 类用于识别位置不固定的小图标
    通过全屏搜索进行模板匹配
    """

    def __init__(self, file):
        """
        初始化 Template

        Args:
            file (dict[str], str): 模板文件路径
        """
        self.raw_file = file
        self._image = None
        self._image_binary = None
        self._image_luma = None

        self.resource_add(self.file)

    cached = ["file", "name", "is_gif"]

    @cached_property
    def file(self):
        """获取文件路径"""
        return self.parse_property(self.raw_file)

    @cached_property
    def name(self):
        """从文件名生成名称"""
        return os.path.splitext(os.path.basename(self.file))[0].upper()

    @cached_property
    def is_gif(self):
        """判断是否为 GIF 文件"""
        return os.path.splitext(self.file)[1] == ".gif"

    @property
    def image(self):
        """加载模板图像"""
        if self._image is None:
            if self.is_gif:
                self._image = []
                channel = 0
                for image in imageio.mimread(self.file):
                    if not channel:
                        channel = len(image.shape)
                    if channel == 3:
                        image = image[:, :, :3].copy()
                    elif len(image.shape) == 3:
                        # Follow the first frame
                        image = image[:, :, 0].copy()

                    image = self.pre_process(image)
                    self._image += [image, cv2.flip(image, 1)]
            else:
                self._image = self.pre_process(load_image(self.file))

        return self._image

    @property
    def image_binary(self):
        """二值化模板图像"""
        if self._image_binary is None:
            if self.is_gif:
                self._image_binary = []
                for image in self.image:
                    image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                    _, image_binary = cv2.threshold(
                        image_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
                    )
                    self._image_binary.append(image_binary)
            else:
                image_gray = cv2.cvtColor(self.image, cv2.COLOR_RGB2GRAY)
                _, self._image_binary = cv2.threshold(
                    image_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
                )

        return self._image_binary

    @property
    def image_luma(self):
        """亮度模板图像"""
        if self._image_luma is None:
            if self.is_gif:
                self._image_luma = []
                for image in self.image:
                    luma = rgb2luma(image)
                    self._image_luma.append(luma)
            else:
                self._image_luma = rgb2luma(self.image)

        return self._image_luma

    @image.setter
    def image(self, value):
        self._image = value

    def resource_release(self):
        """释放资源"""
        super().resource_release()
        self._image = None
        self._image_binary = None
        self._image_luma = None

    def pre_process(self, image):
        """
        预处理图像

        Args:
            image (np.ndarray): 输入图像

        Returns:
            np.ndarray: 处理后的图像
        """
        return image

    @cached_property
    def size(self):
        """获取模板尺寸 (width, height)"""
        if self.is_gif:
            return self.image[0].shape[0:2][::-1]
        else:
            return self.image.shape[0:2][::-1]

    def match(self, image, scaling=1.0, similarity=0.85):
        """
        全屏搜索匹配模板（彩色）

        Args:
            image: 全屏截图
            scaling (int, float): 缩放比例
            similarity (float): 相似度阈值 (0-1)

        Returns:
            bool: 是否找到匹配
        """
        scaling = 1 / scaling
        if scaling != 1.0:
            image = cv2.resize(image, None, fx=scaling, fy=scaling)

        if self.is_gif:
            for template in self.image:
                # 全屏模版匹配
                res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
                # 寻找最佳匹配点
                _, sim, _, _ = cv2.minMaxLoc(res)
                # print(self.file, sim)
                if sim > similarity:
                    return True

            return False

        else:
            res = cv2.matchTemplate(image, self.image, cv2.TM_CCOEFF_NORMED)
            _, sim, _, _ = cv2.minMaxLoc(res)
            # print(self.file, sim)
            return sim > similarity

    def match_binary(self, image, similarity=0.85):
        """
        全屏搜索匹配模板（二值化）

        Args:
            image: 全屏截图
            similarity (float): 相似度阈值 (0-1)

        Returns:
            bool: 是否找到匹配
        """
        if self.is_gif:
            # graying
            image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            # binarization
            _, image_binary = cv2.threshold(
                image_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
            )
            for template in self.image_binary:
                # template matching
                res = cv2.matchTemplate(image_binary, template, cv2.TM_CCOEFF_NORMED)
                _, sim, _, _ = cv2.minMaxLoc(res)
                # print(self.file, sim)
                if sim > similarity:
                    return True

            return False

        else:
            # graying
            image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            # binarization
            _, image_binary = cv2.threshold(
                image_gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
            )
            # template matching
            res = cv2.matchTemplate(
                image_binary, self.image_binary, cv2.TM_CCOEFF_NORMED
            )
            _, sim, _, _ = cv2.minMaxLoc(res)
            # print(self.file, sim)
            return sim > similarity

    def match_luma(self, image, similarity=0.85):
        """
        全屏搜索匹配模板（亮度）

        Args:
            image: 全屏截图
            similarity (float): 相似度阈值 (0-1)

        Returns:
            bool: 是否找到匹配
        """
        if self.is_gif:
            image = rgb2luma(image)
            for template in self.image_luma:
                res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
                _, sim, _, _ = cv2.minMaxLoc(res)
                # print(self.file, sim)
                if sim > similarity:
                    return True

            return False

        else:
            image_luma = rgb2luma(image)
            res = cv2.matchTemplate(image_luma, self.image_luma, cv2.TM_CCOEFF_NORMED)
            _, sim, _, _ = cv2.minMaxLoc(res)
            # print(self.file, sim)
            return sim > similarity

    def _point_to_button(self, point, image=None, name=None):
        """
        将匹配点转换为 Button 对象

        Args:
            point: 匹配位置坐标
            image (np.ndarray): 截图
            name (str): 按钮名称

        Returns:
            Button: Button 对象
        """
        if name is None:
            name = self.name
        area = area_offset(area=(0, 0, *self.size), offset=point)
        button = Button(area=area, color=(), button=area, name=name)
        if image is not None:
            button.load_color(image)
        return button

    def match_result(self, image, name=None):
        """
        返回匹配结果（相似度 + 位置）

        Args:
            image: 全屏截图
            name (str): 按钮名称

        Returns:
            float: 相似度
            Button: 匹配位置的 Button 对象
        """
        res = cv2.matchTemplate(image, self.image, cv2.TM_CCOEFF_NORMED)
        _, sim, _, point = cv2.minMaxLoc(res)
        # print(self.file, sim)

        # 转化为 Button
        button = self._point_to_button(point, image=image, name=name)
        return sim, button

    def match_luma_result(self, image, name=None):
        """
        返回亮度匹配结果（相似度 + 位置）

        Args:
            image: 全屏截图
            name (str): 按钮名称

        Returns:
            float: 相似度
            Button: 匹配位置的 Button 对象
        """
        image_luma = rgb2luma(image)
        res = cv2.matchTemplate(image_luma, self.image_luma, cv2.TM_CCOEFF_NORMED)
        _, sim, _, point = cv2.minMaxLoc(res)
        # print(self.file, sim)

        button = self._point_to_button(point, image=image, name=name)
        return sim, button

    def match_multi(self, image, scaling=1.0, similarity=0.85, threshold=3, name=None):
        """
        匹配目标出现的所有位置（返回所有匹配位置）

        Args:
            image: 全屏截图
            scaling (int, float): 缩放比例
            similarity (float): 相似度阈值 (0-1)
            threshold (int): 聚类距离阈值，距离小于此值的点会被合并
            name (str): 按钮名称

        Returns:
            list[Button]: 所有匹配位置的 Button 列表
        """
        scaling = 1 / scaling
        if scaling != 1.0:
            image = cv2.resize(image, None, fx=scaling, fy=scaling)

        raw = image
        if self.is_gif:
            result = []
            for template in self.image:
                res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
                # 找到所有相似度 > 0.85 的点
                res = np.array(np.where(res > similarity)).T[:, ::-1].tolist()
                result += res
            result = np.array(result)
        else:
            result = cv2.matchTemplate(image, self.image, cv2.TM_CCOEFF_NORMED)
            result = np.array(np.where(result > similarity)).T[:, ::-1]

        # result: np.array([[x0, y0], [x1, y1], ...)
        if scaling != 1.0:
            result = np.round(result / scaling).astype(int)
        # 把靠得很近的点合并成一个 (Points.group)
        result = Points(result).group(threshold=threshold)
        # 返回一堆 Button 对象
        return [self._point_to_button(point, image=raw, name=name) for point in result]

    def __str__(self):
        return self.name

    __repr__ = __str__
