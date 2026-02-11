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

    def __init__(self, name=None, use_gpu=True, model_path=None):
        self._name = name
        self._use_gpu = use_gpu
        self._model_path = model_path  # 自定义模型路径
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

            # 如果指定了自定义模型路径，使用自定义模型
            if self._model_path:
                import os
                import re
                
                logger.info(f"Loading custom CnOCR model from: {self._model_path}")
                
                # 查找 .params 或 .ckpt 文件
                model_dir = self._model_path
                params_files = [f for f in os.listdir(model_dir) if f.endswith('.params')]
                ckpt_files = [f for f in os.listdir(model_dir) if f.endswith('.ckpt')]
                
                if ckpt_files:
                     # 优先使用 .ckpt (PyTorch Lightning Checkpoint)
                    ckpt_file = ckpt_files[0]
                    # 如果有 'model.ckpt' 优先使用
                    if 'model.ckpt' in ckpt_files:
                        ckpt_file = 'model.ckpt'
                        
                    model_fp = os.path.join(model_dir, ckpt_file)
                    vocab_fp = os.path.join(model_dir, "vocab.txt")
                    logger.info(f"Loading custom CnOCR model (PyTorch): {ckpt_file} with vocab: {vocab_fp}")
                    
                    self._ocr = CnOcr(
                        rec_model_name='densenet_lite_136-fc',
                        rec_model_fp=model_fp,
                        rec_model_backend='pytorch',
                        rec_vocab_fp=vocab_fp, # 必须指定词表文件，否则会用默认词表导致 size mismatch
                        context=context
                    )
                elif params_files:
                    # 使用旧版 MXNet .params
                    # 假设只有一个模型文件，或者取第一个
                    # 格式通常是: prefix-0015.params
                    params_file = params_files[0]
                    
                    # 提取 epoch
                    match = re.search(r'-(\d{4})\.params$', params_file)
                    if match:
                        epoch = int(match.group(1))
                        prefix = params_file[:-12] # 去掉 -0015.params
                    else:
                        # 如果格式不对，尝试直接作为前缀
                        epoch = 0
                        prefix = params_file.replace('.params', '')
                    
                    model_fp = os.path.join(model_dir, prefix)
                    logger.info(f"Loading custom CnOCR model (MXNet): {prefix}, Epoch: {epoch}")
                    
                    self._ocr = CnOcr(
                        rec_model_name='densenet_lite_136-fc',
                        rec_model_fp=model_fp,
                        rec_model_epoch=epoch,
                        rec_model_backend='pytorch' if use_pytorch else 'onnx',
                        context=context
                    )
                else:
                    raise FileNotFoundError(f"No .params or .ckpt file found in {model_dir}")
            # 使用 PyTorch 后端 + GPU，或默认 ONNX
            elif use_pytorch:
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
            model_info = f"custom ({self._model_path})" if self._model_path else "default"
            logger.info(f"CnOCR model loaded: {self._name or model_info} (backend: {backend}, context: {context})")
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
                # 预处理图像以提高识别率
                processed_img = self._preprocess_image(img)
                
                # CnOCR 识别
                ocr_result = self._ocr.ocr(processed_img)
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
    
    def _preprocess_image(self, img):
        """
        预处理图像以提高 OCR 识别率
        
        Args:
            img: numpy 数组图像
            
        Returns:
            预处理后的图像
        """
        import cv2
        import numpy as np
        
        # 1. 转灰度
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # 2. 自适应二值化（处理不同光照条件）
        binary = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            11, 2
        )
        
        # 3. 去噪
        denoised = cv2.fastNlMeansDenoising(binary, None, h=10, templateWindowSize=7, searchWindowSize=21)
        
        # 4. 轻微锐化
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        return sharpened

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
        PCR 计时器识别模型 (使用自定义训练的 SimpleCNN 模型)

        使用自定义训练的 SimpleCNN 模型，100% 准确率
        """
        import os
        from module.ocr.simple_cnn import SimpleCNNOCR
        
        # 优先尝试加载微调后的模型
        finetuned_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "module", "ocr", "timer_cnn_finetuned.pth"
        )
        best_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "timer_cnn_best.pth"
        )
        
        if os.path.exists(finetuned_path):
            model_path = finetuned_path
            logger.info(f"Loading Fine-tuned SimpleCNN model from: {model_path}")
        else:
            model_path = best_path
            logger.info(f"Loading Best SimpleCNN model from: {model_path}")
            
        return SimpleCNNOCR(model_path)

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