<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""
PaddleOCR 引擎封装
使用 Paddle Inference API 加载自定义训练的模型
支持新版模型格式 (inference.json + inference.pdiparams)
"""

import os
import json
import cv2
import numpy as np
from PIL import Image

from module.logger import logger

# PaddleOCR 相关导入
try:
    import paddle
    from paddle import inference
    import yaml

    PADDLE_AVAILABLE = True
    logger.info("PaddleOCR dependencies loaded successfully")
except ImportError as e:
    PADDLE_AVAILABLE = False
    logger.warning(f"PaddleOCR not available: {e}")


def get_paddle_device():
    """
    检测 Paddle 可用的设备（GPU/CPU）
    """
    if not PADDLE_AVAILABLE:
        return "cpu"

    try:
        if paddle.device.is_compiled_with_cuda():
            gpu_count = paddle.device.cuda.device_count()
            if gpu_count > 0:
                logger.info(f"GPU available, using GPU for OCR (found {gpu_count} GPU(s))")
                return "gpu"
    except Exception as e:
        logger.info(f"GPU check failed: {e}")

    logger.info("Using CPU for OCR")
    return "cpu"


class PaddleOcrEngine:
    """
    PaddleOCR 文字识别引擎
    使用 Paddle Inference API 加载自定义训练的模型

    支持两种模型格式:
    1. 新格式: inference.json + inference.pdiparams + inference.yml
    2. 旧格式: inference.pdmodel + inference.pdiparams + inference.yml
    """

    DEVICE = get_paddle_device()

    def __init__(
        self,
        model_dir,
        use_gpu=None,
        name=None,
    ):
        """
        初始化 PaddleOCR 引擎

        Args:
            model_dir: 模型目录路径
            use_gpu: 是否使用 GPU，默认自动检测
            name: 实例名称
        """
        self._model_dir = model_dir
        self._use_gpu = use_gpu if use_gpu is not None else (self.DEVICE == "gpu")
        self._name = name

        self._predictor = None
        self._model_loaded = False
        self._alphabet = None
        self._config = None
        self._img_shape = [3, 32, 320]  # 默认值，会从配置中读取
        self._model_format = None  # 'json' or 'pdmodel'

    def _detect_model_format(self):
        """检测模型格式"""
        json_path = os.path.join(self._model_dir, "inference.json")
        pdmodel_path = os.path.join(self._model_dir, "inference.pdmodel")

        if os.path.exists(json_path):
            self._model_format = "json"
            logger.info(f"Detected model format: JSON (inference.json)")
        elif os.path.exists(pdmodel_path):
            self._model_format = "pdmodel"
            logger.info(f"Detected model format: PDModel (inference.pdmodel)")
        else:
            raise FileNotFoundError(
                f"No model file found in {self._model_dir}. "
                f"Expected inference.json or inference.pdmodel"
            )

    def _load_config(self):
        """加载模型配置"""
        config_path = os.path.join(self._model_dir, "inference.yml")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Loaded config from {config_path}")

            # 从配置中读取图像尺寸
            try:
                preprocess = self._config.get('PreProcess', {})
                for op in preprocess.get('transform_ops', []):
                    if 'RecResizeImg' in op:
                        self._img_shape = op['RecResizeImg']['image_shape']
                        logger.info(f"Image shape from config: {self._img_shape}")
                        break
            except Exception as e:
                logger.warning(f"Failed to parse image shape: {e}")
        else:
            logger.warning(f"Config file not found: {config_path}")
            self._config = {}

    def _load_char_dict(self):
        """加载字符字典"""
        # 从 yml 配置中读取字符字典
        if self._config:
            try:
                postprocess = self._config.get('PostProcess', {})
                char_dict = postprocess.get('character_dict', [])
                if char_dict:
                    # PaddleOCR 格式：blank 在索引 0，然后是字符
                    self._alphabet = ['blank'] + char_dict
                    logger.info(f"Loaded {len(char_dict)} characters from config: {''.join(char_dict)}")
                    return
            except Exception as e:
                logger.warning(f"Failed to parse character dict from config: {e}")

        # 如果配置中没有，尝试读取字典文件
        possible_names = ['ppocr_keys_v1.txt', 'keys.txt', 'dict.txt', 'label_list.txt']
        for name in possible_names:
            path = os.path.join(self._model_dir, name)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    chars = f.read().strip().split('\n')
                self._alphabet = ['blank'] + chars
                logger.info(f"Loaded {len(chars)} characters from {path}")
                return

        # 默认字符集（计时器识别）
        self._alphabet = ['blank'] + list('0123456789:')
        logger.warning(f"Using default alphabet for timer recognition: {''.join(self._alphabet[1:])}")

    def _create_predictor(self, use_gpu=True):
        """创建 Paddle Inference 预测器"""
        params_file = os.path.join(self._model_dir, "inference.pdiparams")

        # 根据模型格式选择模型文件
        if self._model_format == "json":
            model_file = os.path.join(self._model_dir, "inference.json")
        else:
            model_file = os.path.join(self._model_dir, "inference.pdmodel")

        # 检查模型文件是否存在
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Model file not found: {model_file}")
        if not os.path.exists(params_file):
            raise FileNotFoundError(f"Params file not found: {params_file}")

        device_str = "GPU" if use_gpu else "CPU"
        logger.info(f"Loading OCR model from: {self._model_dir} (using {device_str})")
        logger.info(f"Model format: {self._model_format}")

        try:
            # 创建配置
            config = inference.Config(model_file, params_file)

            if use_gpu:
                config.enable_use_gpu(200, 0)  # 200MB GPU 内存，使用 GPU 0
            else:
                config.disable_gpu()
                config.set_cpu_math_library_num_threads(4)

            # 基本优化配置（兼容性更好）
            config.switch_ir_optim(False)  # 禁用 IR 优化，提高兼容性
            config.enable_memory_optim()

            # 禁用日志
            try:
                config.disable_glog_info()
            except:
                pass

            logger.info(f"Creating predictor...")

            # 创建预测器
            self._predictor = inference.create_predictor(config)

            logger.info(f"OCR model loaded successfully: {self._name or 'default'} ({device_str})")
            return True

        except Exception as e:
            logger.warning(f"Failed to create predictor with {device_str}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def init(self):
        """初始化模型"""
        if self._model_loaded:
            return

        self._detect_model_format()
        self._load_config()
        self._load_char_dict()

        # 尝试 GPU，失败则回退到 CPU
        if self._use_gpu:
            success = self._create_predictor(use_gpu=True)
            if not success:
                logger.info("GPU initialization failed, falling back to CPU...")
                success = self._create_predictor(use_gpu=False)
                if not success:
                    raise RuntimeError("Failed to initialize OCR model on both GPU and CPU")
        else:
            success = self._create_predictor(use_gpu=False)
            if not success:
                raise RuntimeError("Failed to initialize OCR model on CPU")

        self._model_loaded = True

    def _preprocess(self, img):
        """
        预处理图像

        Args:
            img: numpy 数组，灰度图或 BGR 图

        Returns:
            预处理后的图像张量 [1, C, H, W]
        """
        channels, target_height, target_width = self._img_shape

        # 确保是 BGR 3通道图像
        if len(img.shape) == 2:
            # 灰度图转 BGR
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        h, w = img.shape[:2]

        # 保持宽高比调整高度，然后 pad 到目标宽度
        ratio = target_height / h
        new_width = int(w * ratio)

        if new_width > target_width:
            new_width = target_width

        img = cv2.resize(img, (new_width, target_height))

        # Pad 到目标宽度
        if new_width < target_width:
            pad_img = np.zeros((target_height, target_width, 3), dtype=np.uint8)
            pad_img[:, :new_width, :] = img
            img = pad_img

        # 归一化到 [0, 1]
        img = img.astype(np.float32) / 255.0

        # 标准化 (mean=0.5, std=0.5) -> [-1, 1]
        img = (img - 0.5) / 0.5

        # HWC -> CHW
        img = img.transpose((2, 0, 1))

        # 添加批次维度
        img = img[np.newaxis, :, :, :]  # [1, C, H, W]

        return img.astype(np.float32)

    def _decode(self, preds, cand_alphabet=None):
        """
        CTC 解码

        Args:
            preds: 模型输出，shape [batch, seq_len, num_classes]
            cand_alphabet: 候选字符集限制

        Returns:
            解码后的文本列表
        """
        results = []

        for pred in preds:
            # 获取每个时间步的最大概率索引
            pred_idx = np.argmax(pred, axis=-1)

            # CTC 解码：去除重复和空白
            chars = []
            prev_idx = -1
            for idx in pred_idx:
                if idx != 0 and idx != prev_idx:  # 0 是 blank
                    if idx < len(self._alphabet):
                        char = self._alphabet[idx]
                        # 如果有候选字符限制，检查是否在其中
                        if cand_alphabet is None or char in cand_alphabet:
                            chars.append(char)
                prev_idx = idx

            results.append(''.join(chars))

        return results

    def _run_inference(self, img_batch):
        """
        运行推理

        Args:
            img_batch: 批量图像张量 [N, C, H, W]

        Returns:
            模型输出
        """
        input_names = self._predictor.get_input_names()
        input_tensor = self._predictor.get_input_handle(input_names[0])
        input_tensor.reshape(img_batch.shape)
        input_tensor.copy_from_cpu(img_batch)

        self._predictor.run()

        output_names = self._predictor.get_output_names()
        output_tensor = self._predictor.get_output_handle(output_names[0])
        outputs = output_tensor.copy_to_cpu()

        return outputs

    def ocr_for_single_line(self, img):
        """
        识别单行文本

        Args:
            img: numpy 数组

        Returns:
            识别结果字符串
        """
        if not self._model_loaded:
            self.init()

        img_batch = self._preprocess(img)
        outputs = self._run_inference(img_batch)
        results = self._decode(outputs)

        return results[0] if results else ""

    def ocr_for_single_lines(self, img_list):
        """
        批量识别单行文本

        Args:
            img_list: numpy 数组列表

        Returns:
            识别结果列表
        """
        if not self._model_loaded:
            self.init()

        results = []
        for img in img_list:
            result = self.ocr_for_single_line(img)
            results.append(result)

        return results

    def atomic_ocr_for_single_lines(self, img_list, cand_alphabet=None):
        """
        批量识别单行文本（支持候选字符限制）

        Args:
            img_list: numpy 数组列表
            cand_alphabet: 候选字符集

        Returns:
            识别结果列表，每个元素是字符列表
        """
        if not self._model_loaded:
            self.init()

        results = []
        for img in img_list:
            img_batch = self._preprocess(img)
            outputs = self._run_inference(img_batch)
            decoded = self._decode(outputs, cand_alphabet)
            # 返回字符列表而不是字符串，保持与原接口兼容
            results.append(list(decoded[0]) if decoded else [])

        return results

    def debug(self, img_list):
        """
        调试：显示预处理后的图像

        Args:
            img_list: numpy 数组列表
        """
        if not self._model_loaded:
            self.init()

        processed = []
        for img in img_list:
            proc = self._preprocess(img)
            # 反归一化显示: CHW -> HWC
            proc = proc[0].transpose((1, 2, 0))
            proc = ((proc * 0.5 + 0.5) * 255).astype(np.uint8)
            # BGR -> RGB for display
            proc = cv2.cvtColor(proc, cv2.COLOR_BGR2RGB)
            processed.append(proc)

        if processed:
            combined = cv2.hconcat(processed)
            Image.fromarray(combined).show()


# 保持向后兼容的别名
AlOcr = PaddleOcrEngine
=======
"""
PaddleOCR 引擎封装
使用 Paddle Inference API 加载自定义训练的模型
支持新版模型格式 (inference.json + inference.pdiparams)
"""

import os
import json
import cv2
import numpy as np
from PIL import Image

from module.logger import logger

# PaddleOCR 相关导入
try:
    import paddle
    from paddle import inference
    import yaml

    PADDLE_AVAILABLE = True
    logger.info("PaddleOCR dependencies loaded successfully")
except ImportError as e:
    PADDLE_AVAILABLE = False
    logger.warning(f"PaddleOCR not available: {e}")


def get_paddle_device():
    """
    检测 Paddle 可用的设备（GPU/CPU）
    """
    if not PADDLE_AVAILABLE:
        return "cpu"

    try:
        if paddle.device.is_compiled_with_cuda():
            gpu_count = paddle.device.cuda.device_count()
            if gpu_count > 0:
                logger.info(f"GPU available, using GPU for OCR (found {gpu_count} GPU(s))")
                return "gpu"
    except Exception as e:
        logger.info(f"GPU check failed: {e}")

    logger.info("Using CPU for OCR")
    return "cpu"


class PaddleOcrEngine:
    """
    PaddleOCR 文字识别引擎
    使用 Paddle Inference API 加载自定义训练的模型

    支持两种模型格式:
    1. 新格式: inference.json + inference.pdiparams + inference.yml
    2. 旧格式: inference.pdmodel + inference.pdiparams + inference.yml
    """

    DEVICE = get_paddle_device()

    def __init__(
        self,
        model_dir,
        use_gpu=None,
        name=None,
    ):
        """
        初始化 PaddleOCR 引擎

        Args:
            model_dir: 模型目录路径
            use_gpu: 是否使用 GPU，默认自动检测
            name: 实例名称
        """
        self._model_dir = model_dir
        self._use_gpu = use_gpu if use_gpu is not None else (self.DEVICE == "gpu")
        self._name = name

        self._predictor = None
        self._model_loaded = False
        self._alphabet = None
        self._config = None
        self._img_shape = [3, 32, 320]  # 默认值，会从配置中读取
        self._model_format = None  # 'json' or 'pdmodel'

    def _detect_model_format(self):
        """检测模型格式"""
        json_path = os.path.join(self._model_dir, "inference.json")
        pdmodel_path = os.path.join(self._model_dir, "inference.pdmodel")

        if os.path.exists(json_path):
            self._model_format = "json"
            logger.info(f"Detected model format: JSON (inference.json)")
        elif os.path.exists(pdmodel_path):
            self._model_format = "pdmodel"
            logger.info(f"Detected model format: PDModel (inference.pdmodel)")
        else:
            raise FileNotFoundError(
                f"No model file found in {self._model_dir}. "
                f"Expected inference.json or inference.pdmodel"
            )

    def _load_config(self):
        """加载模型配置"""
        config_path = os.path.join(self._model_dir, "inference.yml")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Loaded config from {config_path}")

            # 从配置中读取图像尺寸
            try:
                preprocess = self._config.get('PreProcess', {})
                for op in preprocess.get('transform_ops', []):
                    if 'RecResizeImg' in op:
                        self._img_shape = op['RecResizeImg']['image_shape']
                        logger.info(f"Image shape from config: {self._img_shape}")
                        break
            except Exception as e:
                logger.warning(f"Failed to parse image shape: {e}")
        else:
            logger.warning(f"Config file not found: {config_path}")
            self._config = {}

    def _load_char_dict(self):
        """加载字符字典"""
        # 从 yml 配置中读取字符字典
        if self._config:
            try:
                postprocess = self._config.get('PostProcess', {})
                char_dict = postprocess.get('character_dict', [])
                if char_dict:
                    # PaddleOCR 格式：blank 在索引 0，然后是字符
                    self._alphabet = ['blank'] + char_dict
                    logger.info(f"Loaded {len(char_dict)} characters from config: {''.join(char_dict)}")
                    return
            except Exception as e:
                logger.warning(f"Failed to parse character dict from config: {e}")

        # 如果配置中没有，尝试读取字典文件
        possible_names = ['ppocr_keys_v1.txt', 'keys.txt', 'dict.txt', 'label_list.txt']
        for name in possible_names:
            path = os.path.join(self._model_dir, name)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    chars = f.read().strip().split('\n')
                self._alphabet = ['blank'] + chars
                logger.info(f"Loaded {len(chars)} characters from {path}")
                return

        # 默认字符集（计时器识别）
        self._alphabet = ['blank'] + list('0123456789:')
        logger.warning(f"Using default alphabet for timer recognition: {''.join(self._alphabet[1:])}")

    def _create_predictor(self, use_gpu=True):
        """创建 Paddle Inference 预测器"""
        params_file = os.path.join(self._model_dir, "inference.pdiparams")

        # 根据模型格式选择模型文件
        if self._model_format == "json":
            model_file = os.path.join(self._model_dir, "inference.json")
        else:
            model_file = os.path.join(self._model_dir, "inference.pdmodel")

        # 检查模型文件是否存在
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Model file not found: {model_file}")
        if not os.path.exists(params_file):
            raise FileNotFoundError(f"Params file not found: {params_file}")

        device_str = "GPU" if use_gpu else "CPU"
        logger.info(f"Loading OCR model from: {self._model_dir} (using {device_str})")
        logger.info(f"Model format: {self._model_format}")

        try:
            # 创建配置
            config = inference.Config(model_file, params_file)

            if use_gpu:
                config.enable_use_gpu(200, 0)  # 200MB GPU 内存，使用 GPU 0
            else:
                config.disable_gpu()
                config.set_cpu_math_library_num_threads(4)

            # 基本优化配置（兼容性更好）
            config.switch_ir_optim(False)  # 禁用 IR 优化，提高兼容性
            config.enable_memory_optim()

            # 禁用日志
            try:
                config.disable_glog_info()
            except:
                pass

            logger.info(f"Creating predictor...")

            # 创建预测器
            self._predictor = inference.create_predictor(config)

            logger.info(f"OCR model loaded successfully: {self._name or 'default'} ({device_str})")
            return True

        except Exception as e:
            logger.warning(f"Failed to create predictor with {device_str}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def init(self):
        """初始化模型"""
        if self._model_loaded:
            return

        self._detect_model_format()
        self._load_config()
        self._load_char_dict()

        # 尝试 GPU，失败则回退到 CPU
        if self._use_gpu:
            success = self._create_predictor(use_gpu=True)
            if not success:
                logger.info("GPU initialization failed, falling back to CPU...")
                success = self._create_predictor(use_gpu=False)
                if not success:
                    raise RuntimeError("Failed to initialize OCR model on both GPU and CPU")
        else:
            success = self._create_predictor(use_gpu=False)
            if not success:
                raise RuntimeError("Failed to initialize OCR model on CPU")

        self._model_loaded = True

    def _preprocess(self, img):
        """
        预处理图像

        Args:
            img: numpy 数组，灰度图或 BGR 图

        Returns:
            预处理后的图像张量 [1, C, H, W]
        """
        channels, target_height, target_width = self._img_shape

        # 确保是 BGR 3通道图像
        if len(img.shape) == 2:
            # 灰度图转 BGR
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        h, w = img.shape[:2]

        # 保持宽高比调整高度，然后 pad 到目标宽度
        ratio = target_height / h
        new_width = int(w * ratio)

        if new_width > target_width:
            new_width = target_width

        img = cv2.resize(img, (new_width, target_height))

        # Pad 到目标宽度
        if new_width < target_width:
            pad_img = np.zeros((target_height, target_width, 3), dtype=np.uint8)
            pad_img[:, :new_width, :] = img
            img = pad_img

        # 归一化到 [0, 1]
        img = img.astype(np.float32) / 255.0

        # 标准化 (mean=0.5, std=0.5) -> [-1, 1]
        img = (img - 0.5) / 0.5

        # HWC -> CHW
        img = img.transpose((2, 0, 1))

        # 添加批次维度
        img = img[np.newaxis, :, :, :]  # [1, C, H, W]

        return img.astype(np.float32)

    def _decode(self, preds, cand_alphabet=None):
        """
        CTC 解码

        Args:
            preds: 模型输出，shape [batch, seq_len, num_classes]
            cand_alphabet: 候选字符集限制

        Returns:
            解码后的文本列表
        """
        results = []

        for pred in preds:
            # 获取每个时间步的最大概率索引
            pred_idx = np.argmax(pred, axis=-1)

            # CTC 解码：去除重复和空白
            chars = []
            prev_idx = -1
            for idx in pred_idx:
                if idx != 0 and idx != prev_idx:  # 0 是 blank
                    if idx < len(self._alphabet):
                        char = self._alphabet[idx]
                        # 如果有候选字符限制，检查是否在其中
                        if cand_alphabet is None or char in cand_alphabet:
                            chars.append(char)
                prev_idx = idx

            results.append(''.join(chars))

        return results

    def _run_inference(self, img_batch):
        """
        运行推理

        Args:
            img_batch: 批量图像张量 [N, C, H, W]

        Returns:
            模型输出
        """
        input_names = self._predictor.get_input_names()
        input_tensor = self._predictor.get_input_handle(input_names[0])
        input_tensor.reshape(img_batch.shape)
        input_tensor.copy_from_cpu(img_batch)

        self._predictor.run()

        output_names = self._predictor.get_output_names()
        output_tensor = self._predictor.get_output_handle(output_names[0])
        outputs = output_tensor.copy_to_cpu()

        return outputs

    def ocr_for_single_line(self, img):
        """
        识别单行文本

        Args:
            img: numpy 数组

        Returns:
            识别结果字符串
        """
        if not self._model_loaded:
            self.init()

        img_batch = self._preprocess(img)
        outputs = self._run_inference(img_batch)
        results = self._decode(outputs)

        return results[0] if results else ""

    def ocr_for_single_lines(self, img_list):
        """
        批量识别单行文本

        Args:
            img_list: numpy 数组列表

        Returns:
            识别结果列表
        """
        if not self._model_loaded:
            self.init()

        results = []
        for img in img_list:
            result = self.ocr_for_single_line(img)
            results.append(result)

        return results

    def atomic_ocr_for_single_lines(self, img_list, cand_alphabet=None):
        """
        批量识别单行文本（支持候选字符限制）

        Args:
            img_list: numpy 数组列表
            cand_alphabet: 候选字符集

        Returns:
            识别结果列表，每个元素是字符列表
        """
        if not self._model_loaded:
            self.init()

        results = []
        for img in img_list:
            img_batch = self._preprocess(img)
            outputs = self._run_inference(img_batch)
            decoded = self._decode(outputs, cand_alphabet)
            # 返回字符列表而不是字符串，保持与原接口兼容
            results.append(list(decoded[0]) if decoded else [])

        return results

    def debug(self, img_list):
        """
        调试：显示预处理后的图像

        Args:
            img_list: numpy 数组列表
        """
        if not self._model_loaded:
            self.init()

        processed = []
        for img in img_list:
            proc = self._preprocess(img)
            # 反归一化显示: CHW -> HWC
            proc = proc[0].transpose((1, 2, 0))
            proc = ((proc * 0.5 + 0.5) * 255).astype(np.uint8)
            # BGR -> RGB for display
            proc = cv2.cvtColor(proc, cv2.COLOR_BGR2RGB)
            processed.append(proc)

        if processed:
            combined = cv2.hconcat(processed)
            Image.fromarray(combined).show()


# 保持向后兼容的别名
AlOcr = PaddleOcrEngine
>>>>>>> Stashed changes
=======
"""
PaddleOCR 引擎封装
使用 Paddle Inference API 加载自定义训练的模型
支持新版模型格式 (inference.json + inference.pdiparams)
"""

import os
import json
import cv2
import numpy as np
from PIL import Image

from module.logger import logger

# PaddleOCR 相关导入
try:
    import paddle
    from paddle import inference
    import yaml

    PADDLE_AVAILABLE = True
    logger.info("PaddleOCR dependencies loaded successfully")
except ImportError as e:
    PADDLE_AVAILABLE = False
    logger.warning(f"PaddleOCR not available: {e}")


def get_paddle_device():
    """
    检测 Paddle 可用的设备（GPU/CPU）
    """
    if not PADDLE_AVAILABLE:
        return "cpu"

    try:
        if paddle.device.is_compiled_with_cuda():
            gpu_count = paddle.device.cuda.device_count()
            if gpu_count > 0:
                logger.info(f"GPU available, using GPU for OCR (found {gpu_count} GPU(s))")
                return "gpu"
    except Exception as e:
        logger.info(f"GPU check failed: {e}")

    logger.info("Using CPU for OCR")
    return "cpu"


class PaddleOcrEngine:
    """
    PaddleOCR 文字识别引擎
    使用 Paddle Inference API 加载自定义训练的模型

    支持两种模型格式:
    1. 新格式: inference.json + inference.pdiparams + inference.yml
    2. 旧格式: inference.pdmodel + inference.pdiparams + inference.yml
    """

    DEVICE = get_paddle_device()

    def __init__(
        self,
        model_dir,
        use_gpu=None,
        name=None,
    ):
        """
        初始化 PaddleOCR 引擎

        Args:
            model_dir: 模型目录路径
            use_gpu: 是否使用 GPU，默认自动检测
            name: 实例名称
        """
        self._model_dir = model_dir
        self._use_gpu = use_gpu if use_gpu is not None else (self.DEVICE == "gpu")
        self._name = name

        self._predictor = None
        self._model_loaded = False
        self._alphabet = None
        self._config = None
        self._img_shape = [3, 32, 320]  # 默认值，会从配置中读取
        self._model_format = None  # 'json' or 'pdmodel'

    def _detect_model_format(self):
        """检测模型格式"""
        json_path = os.path.join(self._model_dir, "inference.json")
        pdmodel_path = os.path.join(self._model_dir, "inference.pdmodel")

        if os.path.exists(json_path):
            self._model_format = "json"
            logger.info(f"Detected model format: JSON (inference.json)")
        elif os.path.exists(pdmodel_path):
            self._model_format = "pdmodel"
            logger.info(f"Detected model format: PDModel (inference.pdmodel)")
        else:
            raise FileNotFoundError(
                f"No model file found in {self._model_dir}. "
                f"Expected inference.json or inference.pdmodel"
            )

    def _load_config(self):
        """加载模型配置"""
        config_path = os.path.join(self._model_dir, "inference.yml")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Loaded config from {config_path}")

            # 从配置中读取图像尺寸
            try:
                preprocess = self._config.get('PreProcess', {})
                for op in preprocess.get('transform_ops', []):
                    if 'RecResizeImg' in op:
                        self._img_shape = op['RecResizeImg']['image_shape']
                        logger.info(f"Image shape from config: {self._img_shape}")
                        break
            except Exception as e:
                logger.warning(f"Failed to parse image shape: {e}")
        else:
            logger.warning(f"Config file not found: {config_path}")
            self._config = {}

    def _load_char_dict(self):
        """加载字符字典"""
        # 从 yml 配置中读取字符字典
        if self._config:
            try:
                postprocess = self._config.get('PostProcess', {})
                char_dict = postprocess.get('character_dict', [])
                if char_dict:
                    # PaddleOCR 格式：blank 在索引 0，然后是字符
                    self._alphabet = ['blank'] + char_dict
                    logger.info(f"Loaded {len(char_dict)} characters from config: {''.join(char_dict)}")
                    return
            except Exception as e:
                logger.warning(f"Failed to parse character dict from config: {e}")

        # 如果配置中没有，尝试读取字典文件
        possible_names = ['ppocr_keys_v1.txt', 'keys.txt', 'dict.txt', 'label_list.txt']
        for name in possible_names:
            path = os.path.join(self._model_dir, name)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    chars = f.read().strip().split('\n')
                self._alphabet = ['blank'] + chars
                logger.info(f"Loaded {len(chars)} characters from {path}")
                return

        # 默认字符集（计时器识别）
        self._alphabet = ['blank'] + list('0123456789:')
        logger.warning(f"Using default alphabet for timer recognition: {''.join(self._alphabet[1:])}")

    def _create_predictor(self, use_gpu=True):
        """创建 Paddle Inference 预测器"""
        params_file = os.path.join(self._model_dir, "inference.pdiparams")

        # 根据模型格式选择模型文件
        if self._model_format == "json":
            model_file = os.path.join(self._model_dir, "inference.json")
        else:
            model_file = os.path.join(self._model_dir, "inference.pdmodel")

        # 检查模型文件是否存在
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Model file not found: {model_file}")
        if not os.path.exists(params_file):
            raise FileNotFoundError(f"Params file not found: {params_file}")

        device_str = "GPU" if use_gpu else "CPU"
        logger.info(f"Loading OCR model from: {self._model_dir} (using {device_str})")
        logger.info(f"Model format: {self._model_format}")

        try:
            # 创建配置
            config = inference.Config(model_file, params_file)

            if use_gpu:
                config.enable_use_gpu(200, 0)  # 200MB GPU 内存，使用 GPU 0
            else:
                config.disable_gpu()
                config.set_cpu_math_library_num_threads(4)

            # 基本优化配置（兼容性更好）
            config.switch_ir_optim(False)  # 禁用 IR 优化，提高兼容性
            config.enable_memory_optim()

            # 禁用日志
            try:
                config.disable_glog_info()
            except:
                pass

            logger.info(f"Creating predictor...")

            # 创建预测器
            self._predictor = inference.create_predictor(config)

            logger.info(f"OCR model loaded successfully: {self._name or 'default'} ({device_str})")
            return True

        except Exception as e:
            logger.warning(f"Failed to create predictor with {device_str}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def init(self):
        """初始化模型"""
        if self._model_loaded:
            return

        self._detect_model_format()
        self._load_config()
        self._load_char_dict()

        # 尝试 GPU，失败则回退到 CPU
        if self._use_gpu:
            success = self._create_predictor(use_gpu=True)
            if not success:
                logger.info("GPU initialization failed, falling back to CPU...")
                success = self._create_predictor(use_gpu=False)
                if not success:
                    raise RuntimeError("Failed to initialize OCR model on both GPU and CPU")
        else:
            success = self._create_predictor(use_gpu=False)
            if not success:
                raise RuntimeError("Failed to initialize OCR model on CPU")

        self._model_loaded = True

    def _preprocess(self, img):
        """
        预处理图像

        Args:
            img: numpy 数组，灰度图或 BGR 图

        Returns:
            预处理后的图像张量 [1, C, H, W]
        """
        channels, target_height, target_width = self._img_shape

        # 确保是 BGR 3通道图像
        if len(img.shape) == 2:
            # 灰度图转 BGR
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        h, w = img.shape[:2]

        # 保持宽高比调整高度，然后 pad 到目标宽度
        ratio = target_height / h
        new_width = int(w * ratio)

        if new_width > target_width:
            new_width = target_width

        img = cv2.resize(img, (new_width, target_height))

        # Pad 到目标宽度
        if new_width < target_width:
            pad_img = np.zeros((target_height, target_width, 3), dtype=np.uint8)
            pad_img[:, :new_width, :] = img
            img = pad_img

        # 归一化到 [0, 1]
        img = img.astype(np.float32) / 255.0

        # 标准化 (mean=0.5, std=0.5) -> [-1, 1]
        img = (img - 0.5) / 0.5

        # HWC -> CHW
        img = img.transpose((2, 0, 1))

        # 添加批次维度
        img = img[np.newaxis, :, :, :]  # [1, C, H, W]

        return img.astype(np.float32)

    def _decode(self, preds, cand_alphabet=None):
        """
        CTC 解码

        Args:
            preds: 模型输出，shape [batch, seq_len, num_classes]
            cand_alphabet: 候选字符集限制

        Returns:
            解码后的文本列表
        """
        results = []

        for pred in preds:
            # 获取每个时间步的最大概率索引
            pred_idx = np.argmax(pred, axis=-1)

            # CTC 解码：去除重复和空白
            chars = []
            prev_idx = -1
            for idx in pred_idx:
                if idx != 0 and idx != prev_idx:  # 0 是 blank
                    if idx < len(self._alphabet):
                        char = self._alphabet[idx]
                        # 如果有候选字符限制，检查是否在其中
                        if cand_alphabet is None or char in cand_alphabet:
                            chars.append(char)
                prev_idx = idx

            results.append(''.join(chars))

        return results

    def _run_inference(self, img_batch):
        """
        运行推理

        Args:
            img_batch: 批量图像张量 [N, C, H, W]

        Returns:
            模型输出
        """
        input_names = self._predictor.get_input_names()
        input_tensor = self._predictor.get_input_handle(input_names[0])
        input_tensor.reshape(img_batch.shape)
        input_tensor.copy_from_cpu(img_batch)

        self._predictor.run()

        output_names = self._predictor.get_output_names()
        output_tensor = self._predictor.get_output_handle(output_names[0])
        outputs = output_tensor.copy_to_cpu()

        return outputs

    def ocr_for_single_line(self, img):
        """
        识别单行文本

        Args:
            img: numpy 数组

        Returns:
            识别结果字符串
        """
        if not self._model_loaded:
            self.init()

        img_batch = self._preprocess(img)
        outputs = self._run_inference(img_batch)
        results = self._decode(outputs)

        return results[0] if results else ""

    def ocr_for_single_lines(self, img_list):
        """
        批量识别单行文本

        Args:
            img_list: numpy 数组列表

        Returns:
            识别结果列表
        """
        if not self._model_loaded:
            self.init()

        results = []
        for img in img_list:
            result = self.ocr_for_single_line(img)
            results.append(result)

        return results

    def atomic_ocr_for_single_lines(self, img_list, cand_alphabet=None):
        """
        批量识别单行文本（支持候选字符限制）

        Args:
            img_list: numpy 数组列表
            cand_alphabet: 候选字符集

        Returns:
            识别结果列表，每个元素是字符列表
        """
        if not self._model_loaded:
            self.init()

        results = []
        for img in img_list:
            img_batch = self._preprocess(img)
            outputs = self._run_inference(img_batch)
            decoded = self._decode(outputs, cand_alphabet)
            # 返回字符列表而不是字符串，保持与原接口兼容
            results.append(list(decoded[0]) if decoded else [])

        return results

    def debug(self, img_list):
        """
        调试：显示预处理后的图像

        Args:
            img_list: numpy 数组列表
        """
        if not self._model_loaded:
            self.init()

        processed = []
        for img in img_list:
            proc = self._preprocess(img)
            # 反归一化显示: CHW -> HWC
            proc = proc[0].transpose((1, 2, 0))
            proc = ((proc * 0.5 + 0.5) * 255).astype(np.uint8)
            # BGR -> RGB for display
            proc = cv2.cvtColor(proc, cv2.COLOR_BGR2RGB)
            processed.append(proc)

        if processed:
            combined = cv2.hconcat(processed)
            Image.fromarray(combined).show()


# 保持向后兼容的别名
AlOcr = PaddleOcrEngine
>>>>>>> Stashed changes
