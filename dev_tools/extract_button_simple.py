"""
简化版按钮提取工具
直接从坐标提取按钮并保存

用法:
    python dev_tools/extract_button_simple.py
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, "./")

from module.base.utils import load_image
from module.logger import logger

def extract_button(screenshot_path, button_name, coords):
    """
    从截图中提取按钮并保存为黑色背景图片
    
    Args:
        screenshot_path: 截图路径
        button_name: 按钮名称
        coords: 坐标 (x1, y1, x2, y2)
    """
    logger.info(f"提取按钮: {button_name}")
    logger.info(f"  截图: {screenshot_path}")
    logger.info(f"  坐标: {coords}")
    
    # 加载截图
    screenshot = load_image(screenshot_path)
    h, w = screenshot.shape[:2]
    
    # 创建黑色背景
    result = np.zeros((h, w, 3), dtype=np.uint8)
    
    # 提取按钮区域
    x1, y1, x2, y2 = coords
    button_region = screenshot[y1:y2, x1:x2]
    
    # 复制到黑色背景
    result[y1:y2, x1:x2] = button_region
    
    # 保存
    output_path = f"./assets/train/{button_name}.png"
    cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    
    logger.info(f"✓ 已保存: {output_path}")
    logger.info(f"  尺寸: {x2-x1} × {y2-y1}")
    
    # 生成代码
    code = f'{button_name} = Button(area=({x1}, {y1}, {x2}, {y2}), color=(100, 150, 200), button=({x1}, {y1}, {x2}, {y2}), file="./assets/train/{button_name}.png")'
    logger.info("")
    logger.info("生成的代码:")
    logger.info(f"  {code}")
    
    return output_path

def main():
    logger.hr("按钮提取工具", level=0)
    
    # 你的按钮信息
    button_name = "PHYSICAL_TEST"
    screenshot_path = "./temp_screenshot.png"
    coords = (636, 186, 1208, 303)
    
    if not os.path.exists(screenshot_path):
        logger.error(f"找不到截图: {screenshot_path}")
        return
    
    extract_button(screenshot_path, button_name, coords)
    
    logger.hr("完成!", level=0)
    logger.info("请将上面的代码添加到 module/train/assets.py")

if __name__ == "__main__":
    main()
