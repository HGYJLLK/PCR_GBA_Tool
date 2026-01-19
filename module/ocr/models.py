"""
OCR 模型配置
支持 PaddleOCR 和 CnOCR 两种引擎
"""

import os
from module.base.decorator import cached_property
from module.logger import logger


# 模型路径配置
# 获取项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# PCR 计时器模型路径 (PaddleOCR)
PCR_TIMER_MODEL_PATH = os.path.join(
    _PROJECT_ROOT,
    "PaddleOCR_full",
    "inference",
    "pcr_timer_v2"
)


class CnOcrEngine:
    """
    CnOCR 引擎封装
    使用预训练的 densenet_lite_136-fc 模型，无需额外训练
    """

    def __init__(self, name=None, use_gpu=True):
        self._name = name
        self._use_gpu = use_gpu
        self._ocr = None
        self._model_loaded = False

    def init(self):
        """初始化 CnOCR 模型"""
        if self._model_loaded:
            return

        try:
            from cnocr import CnOcr

            # 检测 GPU 可用性
            context = 'cpu'
            use_pytorch = False
            if self._use_gpu:
                try:
                    import torch
                    if torch.cuda.is_available():
                        context = 'gpu'
                        use_pytorch = True  # 使用 PyTorch 后端才能真正用 GPU
                        logger.info(f"CnOCR: GPU (CUDA) available, using PyTorch GPU backend")
                    else:
                        logger.info(f"CnOCR: CUDA not available, using ONNX CPU")
                except ImportError:
                    logger.info(f"CnOCR: PyTorch not found, using ONNX CPU")

            # 使用 PyTorch 后端 + GPU，或默认 ONNX
            if use_pytorch:
                self._ocr = CnOcr(
                    rec_model_name='densenet_lite_136-fc',
                    rec_model_backend='pytorch',
                    context=context
                )
            else:
                self._ocr = CnOcr(
                    rec_model_name='densenet_lite_136-fc',
                    context=context
                )

            self._model_loaded = True
            backend = 'pytorch' if use_pytorch else 'onnx'
            logger.info(f"CnOCR model loaded: {self._name or 'default'} (backend: {backend}, context: {context})")
        except Exception as e:
            logger.error(f"Failed to load CnOCR model: {e}")
            raise

    def atomic_ocr_for_single_lines(self, img_list, cand_alphabet=None):
        """
        批量识别单行文本

        Args:
            img_list: numpy 数组列表 (预处理后的图像)
            cand_alphabet: 候选字符集 (用于过滤结果)

        Returns:
            识别结果列表，每个元素是字符列表
        """
        if not self._model_loaded:
            self.init()

        results = []
        for img in img_list:
            try:
                # CnOCR 识别
                ocr_result = self._ocr.ocr(img)
                if ocr_result:
                    text = ocr_result[0]['text']
                    score = ocr_result[0]['score']

                    # 如果有候选字符限制，过滤结果
                    if cand_alphabet:
                        text = ''.join(c for c in text if c in cand_alphabet)

                    # logger.info(f"CnOCR: '{text}' (confidence: {score:.2%})")
                    results.append(list(text))
                else:
                    results.append([])
            except Exception as e:
                logger.warning(f"CnOCR recognition failed: {e}")
                results.append([])

        return results

    def debug(self, img_list):
        """调试：显示图像"""
        from PIL import Image
        import cv2
        import numpy as np

        for i, img in enumerate(img_list):
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
            Image.fromarray(img).show()


class OcrModel:
    """OCR 模型管理器"""

    @cached_property
    def pcr(self):
        """
        PCR 计时器识别模型 (使用 CnOCR)

        使用预训练的 CnOCR 模型，对时间格式有很好的识别效果
        """
        return CnOcrEngine(name="pcr_timer_cnocr")

    @cached_property
    def cnocr(self):
        """
        通用 CnOCR 模型
        """
        return CnOcrEngine(name="cnocr")

    @cached_property
    def paddle(self):
        """
        PaddleOCR 自定义模型 (备用)

        如果 CnOCR 效果不好，可以切换到 PaddleOCR
        """
        from module.ocr.al_ocr import PaddleOcrEngine
        return PaddleOcrEngine(
            model_dir=PCR_TIMER_MODEL_PATH,
            name="pcr_timer_paddle",
        )


OCR_MODEL = OcrModel()