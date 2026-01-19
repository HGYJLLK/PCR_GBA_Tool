"""
测试 PaddleOCR 模型加载和识别
"""
import sys
import os
import numpy as np
import cv2

sys.path.insert(0, "./")

from module.ocr.al_ocr import PaddleOcrEngine
from module.ocr.models import PCR_TIMER_MODEL_PATH
from module.logger import logger


def create_test_image():
    """创建一个测试图像，包含数字 1:30"""
    # 创建白色背景
    img = np.ones((32, 100, 3), dtype=np.uint8) * 255

    # 在图像上绘制黑色文字 "1:30"
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, "1:30", (10, 25), font, 0.8, (0, 0, 0), 2)

    return img


def main():
    logger.info("=" * 60)
    logger.info("PaddleOCR 模型测试")
    logger.info("=" * 60)

    # 检查模型路径
    logger.info(f"模型路径: {PCR_TIMER_MODEL_PATH}")
    logger.info(f"模型路径存在: {os.path.exists(PCR_TIMER_MODEL_PATH)}")

    # 列出模型文件
    if os.path.exists(PCR_TIMER_MODEL_PATH):
        files = os.listdir(PCR_TIMER_MODEL_PATH)
        logger.info(f"模型文件: {files}")

    # 创建 OCR 引擎
    logger.info("")
    logger.info("创建 OCR 引擎...")
    engine = PaddleOcrEngine(
        model_dir=PCR_TIMER_MODEL_PATH,
        name="test_pcr_timer",
        use_gpu=False,  # 强制使用 CPU 测试
    )

    # 初始化模型
    logger.info("初始化模型...")
    engine.init()

    logger.info("")
    logger.info("模型信息:")
    logger.info(f"  - 字符集: {''.join(engine._alphabet[1:])}")
    logger.info(f"  - 图像尺寸: {engine._img_shape}")
    logger.info(f"  - 模型格式: {engine._model_format}")

    # 创建测试图像
    logger.info("")
    logger.info("创建测试图像...")
    test_img = create_test_image()

    # 保存测试图像
    test_img_path = "tests/test_timer_image.png"
    cv2.imwrite(test_img_path, test_img)
    logger.info(f"测试图像已保存: {test_img_path}")

    # 执行 OCR 识别
    logger.info("")
    logger.info("执行 OCR 识别...")
    result = engine.ocr_for_single_line(test_img)
    logger.info(f"识别结果: '{result}'")

    # 测试批量识别
    logger.info("")
    logger.info("测试批量识别...")
    results = engine.ocr_for_single_lines([test_img, test_img])
    logger.info(f"批量识别结果: {results}")

    # 测试带字符限制的识别
    logger.info("")
    logger.info("测试带字符限制的识别 (只允许 0123456789:)...")
    results = engine.atomic_ocr_for_single_lines([test_img], cand_alphabet="0123456789:")
    logger.info(f"限制字符识别结果: {results}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("测试完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
