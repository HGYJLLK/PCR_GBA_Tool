"""
简单测试 CnOCR 识别效果
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module.ocr.models import OCR_MODEL
from module.logger import logger
import cv2
import numpy as np


def test_with_image(image_path):
    """测试单张图片"""
    if not os.path.exists(image_path):
        logger.error(f"Image not found: {image_path}")
        return

    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Failed to read image: {image_path}")
        return

    logger.info(f"Testing image: {image_path}")
    logger.info(f"Image shape: {img.shape}")

    # 使用 CnOCR 识别
    ocr = OCR_MODEL.pcr
    result = ocr.atomic_ocr_for_single_lines([img], cand_alphabet="0123456789:")

    if result and result[0]:
        text = ''.join(result[0])
        logger.info(f"Recognition result: {text}")
    else:
        logger.warning("No text recognized")


def test_with_synthetic_images():
    """测试合成图片"""
    # 测试图片路径（使用之前训练数据中的图片）
    test_dir = r"c:\Users\wdnmd\Desktop\cnocr\train_data"
    test_images = [
        os.path.join(test_dir, "timer_manual_20251129_143812/images/002.png"),
        os.path.join(test_dir, "timer_manual_20251129_143812/images/269.png"),
        os.path.join(test_dir, "synth_20251130_002229/images/synth_00000.png"),
    ]

    logger.info("=" * 50)
    logger.info("Testing CnOCR with sample images")
    logger.info("=" * 50)

    for img_path in test_images:
        test_with_image(img_path)
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 测试指定的图片
        test_with_image(sys.argv[1])
    else:
        # 测试示例图片
        test_with_synthetic_images()
