"""
Mask 类用于图像遮罩过滤
"""

import cv2
import numpy as np

from module.base.template import Template
from module.base.utils import image_channel, load_image, rgb2luma


class Mask(Template):
    """
    遮罩类，用于过滤图像中的特定区域

    使用黑白图像作为遮罩：
    - 白色区域（255）：保留识别
    - 黑色区域（0）：遮挡过滤
    """

    @property
    def image(self):
        """加载遮罩图像并转换为灰度图"""
        if self._image is None:
            image = load_image(self.file)
            if image_channel(image) == 3:
                image = rgb2luma(image)
            self._image = image

        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    def set_channel(self, channel):
        """
        设置遮罩的通道数

        Args:
            channel (int): 0 为单色，3 为 RGB
                - 0：单色遮罩
                - 3：RGB 遮罩

        Returns:
            bool: 如果改变了通道数返回 True
        """
        mask_channel = image_channel(self.image)
        if channel == 0:
            if mask_channel == 0:
                return False
            else:
                self._image, _, _ = cv2.split(self._image)
                return True
        else:
            # 遮罩是单通道
            if mask_channel == 0:
                # 把单通道复制 3 份，叠成 RGB (R=G=B)
                self._image = cv2.merge([self._image] * 3)
                return True
            else:
                return False

    def apply(self, image):
        """
        将遮罩应用到图像上

        使用 cv2.bitwise_and 进行位运算：
        - 白色（255）与原图 AND → 保留原图像素
        - 黑色（0）与原图 AND → 像素变为 0（黑色）

        Args:
            image (np.ndarray): 要应用遮罩的图像

        Returns:
            np.ndarray: 应用遮罩后的图像
        """
        # 把遮罩调整成和 image 一样的通道数(OpenCV 要求图像通道相同才能进行位运算)
        self.set_channel(image_channel(image))
        '''
        像素 vs 白色 (1)：原像素 AND 1 = 原像素（保留原貌）
        像素 vs 黑色 (0)：原像素 AND 0 = 0（变成纯黑）
        '''
        return cv2.bitwise_and(image, self.image)
