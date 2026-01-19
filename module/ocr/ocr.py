"""
OCR 识别模块
提供 Ocr 和 Duration 类用于图像文字识别
"""

import time
import re
from datetime import timedelta
from typing import TYPE_CHECKING

from module.base.button import Button
from module.base.decorator import cached_property
from module.base.utils import *
from module.logger import logger
from module.ocr.models import OCR_MODEL

if TYPE_CHECKING:
    from module.ocr.al_ocr import PaddleOcrEngine


class Ocr:
    """
    通用 OCR 识别类
    """
    SHOW_LOG = True
    SHOW_REVISE_WARNING = False

    def __init__(
        self,
        buttons,
        lang="pcr",
        letter=(255, 255, 255),
        threshold=128,
        alphabet=None,
        name=None,
    ):
        """
        初始化 OCR 识别器

        Args:
            buttons (Button, tuple, list[Button], list[tuple]): OCR 区域
            lang (str): 语言/模型标识，'pcr' 或 'cnocr'
            letter (tuple(int)): 目标字符 RGB 颜色
            threshold (int): 二值化阈值
            alphabet: 候选字符白名单
            name (str): 识别器名称
        """
        self.name = str(buttons) if isinstance(buttons, Button) else name
        self._buttons = buttons
        self.letter = letter
        self.threshold = threshold
        self.alphabet = alphabet
        self.lang = lang

    @property
    def cnocr(self) -> "PaddleOcrEngine":
        """获取 OCR 引擎实例"""
        return OCR_MODEL.__getattribute__(self.lang)

    @property
    def buttons(self):
        """获取 OCR 区域列表"""
        buttons = self._buttons
        buttons = buttons if isinstance(buttons, list) else [buttons]
        buttons = [
            button.area if isinstance(button, Button) else button for button in buttons
        ]
        return buttons

    @buttons.setter
    def buttons(self, value):
        self._buttons = value

    def pre_process(self, image):
        """
        图像预处理

        Args:
            image (np.ndarray): 输入图像，形状 (height, width, channel)

        Returns:
            np.ndarray: 预处理后的图像
        """
        # CnOCR 对原始图像识别效果更好，跳过二值化
        if self.lang in ("pcr", "cnocr"):
            return image

        # PaddleOCR 使用二值化预处理
        image = extract_letters(image, letter=self.letter, threshold=self.threshold)
        return image.astype(np.uint8)

    def after_process(self, result):
        """
        OCR 结果后处理

        Args:
            result (str): OCR 识别的原始结果

        Returns:
            str: 处理后的结果
        """
        return result

    def ocr(self, image, direct_ocr=False):
        """
        执行 OCR 识别

        Args:
            image (np.ndarray, list[np.ndarray]): 输入图像
            direct_ocr (bool): True 表示跳过预处理

        Returns:
            str 或 list: 识别结果
        """
        start_time = time.time()

        if direct_ocr:
            image_list = [self.pre_process(i) for i in image]
        else:
            image_list = [self.pre_process(crop(image, area)) for area in self.buttons]

        # 调试：显示输入 OCR 模型的图像
        # self.cnocr.debug(image_list)

        result_list = self.cnocr.atomic_ocr_for_single_lines(image_list, self.alphabet)
        result_list = ["".join(result) for result in result_list]
        result_list = [self.after_process(result) for result in result_list]

        if len(self.buttons) == 1:
            result_list = result_list[0]

        if self.SHOW_LOG:
            logger.attr(
                name="%s %ss" % (self.name, float2str(time.time() - start_time)),
                value=str(result_list),
            )

        return result_list


class Duration(Ocr):
    """
    时间格式 OCR 识别类
    用于识别 HH:MM:SS 或 M:SS 格式的时间
    """

    def __init__(
        self,
        buttons,
        lang="pcr",
        letter=(255, 255, 255),
        threshold=128,
        alphabet="0123456789:",
        name=None,
    ):
        super().__init__(
            buttons,
            lang=lang,
            letter=letter,
            threshold=threshold,
            alphabet=alphabet,
            name=name,
        )

    def after_process(self, result):
        """
        后处理：修正常见的 OCR 误识别
        """
        result = super().after_process(result)
        # 常见的字符误识别修正
        result = result.replace("I", "1").replace("D", "0").replace("S", "5")
        result = result.replace("B", "8")
        result = result.replace("O", "0").replace("l", "1")
        return result

    def ocr(self, image, direct_ocr=False):
        """
        识别时间格式文本

        Args:
            image: 输入图像
            direct_ocr: 是否跳过预处理

        Returns:
            datetime.timedelta 或 list[datetime.timedelta]: 时间对象
        """
        result_list = super().ocr(image, direct_ocr=direct_ocr)

        if not isinstance(result_list, list):
            result_list = [result_list]

        result_list = [self.parse_time(result) for result in result_list]

        if len(self.buttons) == 1:
            result_list = result_list[0]

        return result_list

    @staticmethod
    def parse_time(string):
        """
        解析时间字符串

        Args:
            string (str): 时间字符串，如 '01:30:00' 或 '1:25'

        Returns:
            datetime.timedelta: 时间对象
        """
        # 尝试匹配 HH:MM:SS 格式
        result = re.search(r"(\d{1,2}):?(\d{2}):?(\d{2})", string)
        if result:
            result = [int(s) for s in result.groups()]
            return timedelta(hours=result[0], minutes=result[1], seconds=result[2])

        # 尝试匹配 M:SS 格式
        result = re.search(r"(\d{1,2}):(\d{2})", string)
        if result:
            result = [int(s) for s in result.groups()]
            return timedelta(minutes=result[0], seconds=result[1])

        # 尝试匹配纯数字（当作秒数，如 "31" -> 31秒）
        result = re.search(r"^(\d{1,3})$", string.strip())
        if result:
            seconds = int(result.group(1))
            if seconds <= 90:  # 合理范围内的秒数
                return timedelta(seconds=seconds)

        # 无法解析
        logger.warning(f"Invalid duration: {string}")
        return timedelta(hours=0, minutes=0, seconds=0)
