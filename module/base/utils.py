"""
图像处理工具函数
"""

import random

import cv2
import numpy as np
from PIL import Image


def random_normal_distribution_int(a, b, n=3):
    """
    生成正态分布的随机整数

    Args:
        a (int): 最小值
        b (int): 最大值
        n (int): 模拟次数，默认3次

    Returns:
        int: 随机整数
    """
    a = round(a)
    b = round(b)
    if a < b:
        total = 0
        for _ in range(n):
            total += random.randint(a, b)
        return round(total / n)
    else:
        return b


def random_rectangle_point(area, n=3):
    """
    在区域内随机选择一个点

    Args:
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
        n (int): 次数，默认3次

    Returns:
        tuple(int): (x, y)
    """
    x = random_normal_distribution_int(area[0], area[2], n=n)
    y = random_normal_distribution_int(area[1], area[3], n=n)
    return x, y


def area_offset(area, offset):
    """
    移动一个区域

    Args:
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
        offset: (x, y)

    Returns:
        tuple: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
    """
    upper_left_x, upper_left_y, bottom_right_x, bottom_right_y = area
    x, y = offset
    return upper_left_x + x, upper_left_y + y, bottom_right_x + x, bottom_right_y + y


def load_image(file, area=None):
    """
    加载图像并删除alpha通道

    Args:
        file (str): 图像文件路径
        area (tuple): 裁剪区域

    Returns:
        np.ndarray: 图像数组
    """
    import os
    from module.logger import logger

    if not os.path.exists(file):
        logger.error(f"Image file not found: {file}")
        return None

    try:
        with Image.open(file) as f:
            if area is not None:
                f = f.crop(area)
            image = np.array(f)

        # 如果有alpha通道，转换为RGB
        if len(image.shape) == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)

        return image
    except Exception as e:
        logger.error(f"Failed to load image {file}: {e}")
        return None


def save_image(image, file):
    """
    保存图像

    Args:
        image (np.ndarray): 图像数组
        file (str): 保存路径
    """
    Image.fromarray(image).save(file)


def copy_image(src):
    """
    复制图像

    Args:
        src: 源图像

    Returns:
        np.ndarray: 复制的图像
    """
    dst = np.empty_like(src)
    cv2.copyTo(src, None, dst)
    return dst


def crop(image, area, copy=True):
    """
    裁剪图像

    Args:
        image (np.ndarray): 图像
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
        copy (bool): 是否复制图像

    Returns:
        np.ndarray: 裁剪后的图像
    """
    x1, y1, x2, y2 = map(round, area)
    shape = image.shape
    h = shape[0]
    w = shape[1]

    overflow = False

    # 计算边界
    if y1 >= 0:
        top = 0
        if y1 >= h:
            overflow = True
    else:
        top = -y1

    if y2 > h:
        bottom = y2 - h
    else:
        bottom = 0
        if y2 <= 0:
            overflow = True

    if x1 >= 0:
        left = 0
        if x1 >= w:
            overflow = True
    else:
        left = -x1

    if x2 > w:
        right = x2 - w
    else:
        right = 0
        if x2 <= 0:
            overflow = True

    # 如果溢出，返回空图像
    if overflow:
        if len(shape) == 2:
            size = (y2 - y1, x2 - x1)
        else:
            size = (y2 - y1, x2 - x1, shape[2])
        return np.zeros(size, dtype=image.dtype)

    # 限制坐标
    if x1 < 0:
        x1 = 0
    if y1 < 0:
        y1 = 0
    if x2 < 0:
        x2 = 0
    if y2 < 0:
        y2 = 0

    # 裁剪图像
    image = image[y1:y2, x1:x2]

    # 边界填充
    if top or bottom or left or right:
        if len(shape) == 2:
            value = 0
        else:
            value = tuple(0 for _ in range(image.shape[2]))
        return cv2.copyMakeBorder(
            image, top, bottom, left, right, borderType=cv2.BORDER_CONSTANT, value=value
        )
    elif copy:
        return copy_image(image)
    else:
        return image


def rgb2gray(image):
    """
    gray = ( MAX(r, g, b) + MIN(r, g, b)) / 2

    Args:
        image (np.ndarray): Shape (height, width, channel)

    Returns:
        np.ndarray: Shape (height, width)
    """
    r, g, b = cv2.split(image)
    maximum = cv2.max(r, g)
    cv2.min(r, g, dst=r)
    cv2.max(maximum, b, dst=maximum)
    cv2.min(r, b, dst=r)
    # minimum = r
    cv2.convertScaleAbs(maximum, alpha=0.5, dst=maximum)
    cv2.convertScaleAbs(r, alpha=0.5, dst=r)
    cv2.add(maximum, r, dst=maximum)
    return maximum


def rgb2luma(image):
    """
    将RGB图像转换为YUV色彩空间的Y通道

    Args:
        image (np.ndarray): RGB图像，形状 (height, width, channel)

    Returns:
        np.ndarray: 亮度图像，形状 (height, width)
    """
    image = cv2.cvtColor(image, cv2.COLOR_RGB2YUV)
    luma, _, _ = cv2.split(image)
    return luma


def get_color(image, area):
    """
    计算图像特定区域的平均颜色

    Args:
        image (np.ndarray): 截图
        area (tuple): (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)

    Returns:
        tuple: (r, g, b)
    """
    temp = crop(image, area, copy=False)
    color = cv2.mean(temp)
    return color[:3]


def color_similar(color1, color2, threshold=10):
    """
    判断两个颜色是否相似

    Args:
        color1 (tuple): (r, g, b)
        color2 (tuple): (r, g, b)
        threshold (int): 阈值，默认10

    Returns:
        bool: 如果颜色相似返回True
    """
    diff_r = color1[0] - color2[0]
    diff_g = color1[1] - color2[1]
    diff_b = color1[2] - color2[2]

    max_positive = 0
    max_negative = 0

    if diff_r > max_positive:
        max_positive = diff_r
    elif diff_r < max_negative:
        max_negative = diff_r

    if diff_g > max_positive:
        max_positive = diff_g
    elif diff_g < max_negative:
        max_negative = diff_g

    if diff_b > max_positive:
        max_positive = diff_b
    elif diff_b < max_negative:
        max_negative = diff_b

    diff = max_positive - max_negative
    return diff <= threshold


def extract_letters(image, letter=(255, 255, 255), threshold=128):
    """Set letter color to black, set background color to white.

    Args:
        image: Shape (height, width, channel)
        letter (tuple): Letter RGB.
        threshold (int):

    Returns:
        np.ndarray: Shape (height, width)
    """
    diff = cv2.subtract(image, (*letter, 0))
    r, g, b = cv2.split(diff)
    cv2.max(r, g, dst=r)
    cv2.max(r, b, dst=r)
    positive = r
    cv2.subtract((*letter, 0), image, dst=diff)
    r, g, b = cv2.split(diff)
    cv2.max(r, g, dst=r)
    cv2.max(r, b, dst=r)
    negative = r
    cv2.add(positive, negative, dst=positive)
    if threshold != 255:
        cv2.convertScaleAbs(positive, alpha=255.0 / threshold, dst=positive)
    return positive


def float2str(n, decimal=3):
    """
    Args:
        n (float):
        decimal (int):

    Returns:
        str:
    """
    return str(round(n, decimal)).ljust(decimal + 2, "0")


def image_channel(image):
    """
    获取图像通道数

    Args:
        image (np.ndarray): 图像数组

    Returns:
        int: 0 表示灰度图, 3 表示 RGB, 4 表示 RGBA
    """
    return image.shape[2] if len(image.shape) == 3 else 0


def image_size(image):
    """
    获取图像尺寸

    Args:
        image (np.ndarray): 图像数组

    Returns:
        tuple: (width, height)
    """
    shape = image.shape
    return shape[1], shape[0]


class ImageNotSupported(Exception):
    """
    图像不支持异常
    """

    pass


def get_bbox(image, threshold=0):
    """
    获取图像中非背景内容的边界框 - Pillow 的 getbbox() 的 OpenCV 实现

    Args:
        image (np.ndarray): 图像数组
        threshold (int): 阈值
            color > threshold 的像素会被认为是内容
            color <= threshold 的像素会被认为是背景

    Returns:
        tuple[int, int, int, int]: (x1, y1, x2, y2) 边界框坐标

    Raises:
        ImageNotSupported: 如果无法获取边界框
    """
    channel = image_channel(image)
    # 转换为灰度图
    if channel == 3:
        # RGB
        mask = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        cv2.threshold(mask, threshold, 255, cv2.THRESH_BINARY, dst=mask)
    elif channel == 0:
        # grayscale
        _, mask = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY)
    elif channel == 4:
        # RGBA
        mask = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
        cv2.threshold(mask, threshold, 255, cv2.THRESH_BINARY, dst=mask)
    else:
        raise ImageNotSupported(f"shape={image.shape}")

    # 查找边界框
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_y, min_x = mask.shape
    max_x = 0
    max_y = 0
    # 全黑图像
    if not contours:
        raise ImageNotSupported(f"Cannot get bbox from a pure black image")
    for contour in contours:
        # x, y, w, h
        x1, y1, x2, y2 = cv2.boundingRect(contour)
        x2 += x1
        y2 += y1
        if x1 < min_x:
            min_x = x1
        if y1 < min_y:
            min_y = y1
        if x2 > max_x:
            max_x = x2
        if y2 > max_y:
            max_y = y2
    if min_x < max_x and min_y < max_y:
        return min_x, min_y, max_x, max_y
    else:
        raise ImageNotSupported(f"Empty bbox {(min_x, min_y, max_x, max_y)}")


def ensure_int(*args):
    """
    将所有元素转换为 int
    返回与嵌套对象相同的结构

    Args:
        *args: 任意参数

    Returns:
        list: 转换后的结果
    """
    def to_int(item):
        try:
            return int(item)
        except TypeError:
            result = [to_int(i) for i in item]
            if len(result) == 1:
                result = result[0]
            return result

    return to_int(args)


def ensure_time(second, n=3, precision=3):
    """
    确保参数是时间格式

    Args:
        second (int, float, tuple): 时间，如 10, (10, 30), '10, 30'
        n (int): 模拟中的数字数量，默认为 3
        precision (int): 小数位数

    Returns:
        float: 时间值
    """
    if isinstance(second, tuple):
        multiply = 10 ** precision
        result = random_normal_distribution_int(second[0] * multiply, second[1] * multiply, n) / multiply
        return round(result, precision)
    elif isinstance(second, str):
        if ',' in second:
            lower, upper = second.replace(' ', '').split(',')
            lower, upper = int(lower), int(upper)
            return ensure_time((lower, upper), n=n, precision=precision)
        if '-' in second:
            lower, upper = second.replace(' ', '').split('-')
            lower, upper = int(lower), int(upper)
            return ensure_time((lower, upper), n=n, precision=precision)
        else:
            return int(second)
    else:
        return second


def point2str(x, y, length=4):
    """
    将点坐标格式化为字符串

    Args:
        x (int, float): X 坐标
        y (int, float): Y 坐标
        length (int): 对齐长度

    Returns:
        str: 格式化的字符串，如 '( 100,  80)'
    """
    return '(%s, %s)' % (str(int(x)).rjust(length), str(int(y)).rjust(length))


def area_pad(area, pad=10):
    """
    内部偏移一个区域

    Args:
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
        pad (int): 内缩距离

    Returns:
        tuple: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
    """
    upper_left_x, upper_left_y, bottom_right_x, bottom_right_y = area
    return upper_left_x + pad, upper_left_y + pad, bottom_right_x - pad, bottom_right_y - pad


def area_limit(area, limit):
    """
    限制区域在指定范围内

    Args:
        area: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
        limit: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)

    Returns:
        tuple: (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
    """
    x1, y1, x2, y2 = area
    lx1, ly1, lx2, ly2 = limit
    return max(x1, lx1), max(y1, ly1), min(x2, lx2), min(y2, ly2)


class Points:
    """
    点集合类，用于点的批量处理和聚类
    """

    def __init__(self, points):
        """
        初始化点集合

        Args:
            points: 点的数组或列表，如 [[x0, y0], [x1, y1], ...]
        """
        if points is None or len(points) == 0:
            self._bool = False
            self.points = None
        else:
            self._bool = True
            self.points = np.array(points)
            if len(self.points.shape) == 1:
                self.points = np.array([self.points])
            self.x, self.y = self.points.T

    def __str__(self):
        return str(self.points)

    __repr__ = __str__

    def __iter__(self):
        return iter(self.points)

    def __getitem__(self, item):
        return self.points[item]

    def __len__(self):
        if self:
            return len(self.points)
        else:
            return 0

    def __bool__(self):
        return self._bool

    def mean(self):
        """
        计算所有点的平均值

        Returns:
            np.ndarray: 平均点坐标 [x, y]
        """
        if not self:
            return None

        return np.round(np.mean(self.points, axis=0)).astype(int)

    def group(self, threshold=3):
        """
        将距离很近的点聚类成一个点

        Args:
            threshold (int): 聚类距离阈值，距离小于此值的点会被合并

        Returns:
            np.ndarray: 聚类后的点数组
        """
        if not self:
            return np.array([])
        groups = []
        points = self.points
        if len(points) == 1:
            return np.array([points[0]])

        while len(points):
            p0, p1 = points[0], points[1:]
            distance = np.sum(np.abs(p1 - p0), axis=1)
            new = Points(np.append(p1[distance <= threshold], [p0], axis=0)).mean().tolist()
            groups.append(new)
            points = p1[distance > threshold]

        return np.array(groups)
