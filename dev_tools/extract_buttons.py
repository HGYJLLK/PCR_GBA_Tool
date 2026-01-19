"""
从全屏截图中提取按钮并保存为黑色背景图片

用法:
    python dev_tools/extract_buttons.py

会从你之前保存的截图中提取三个按钮,并保存为黑色背景的图片
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, "./")

from module.base.utils import load_image

def extract_button_with_black_background(screenshot_path, coords, output_path):
    """
    从截图中提取按钮区域,其他部分设为黑色
    
    Args:
        screenshot_path: 全屏截图路径
        coords: 按钮坐标 (x1, y1, x2, y2)
        output_path: 输出图片路径
    """
    # 加载截图
    screenshot = load_image(screenshot_path)
    h, w = screenshot.shape[:2]
    
    # 创建黑色背景图片
    result = np.zeros((h, w, 3), dtype=np.uint8)
    
    # 提取按钮区域
    x1, y1, x2, y2 = coords
    button_region = screenshot[y1:y2, x1:x2]
    
    # 将按钮区域复制到黑色背景上
    result[y1:y2, x1:x2] = button_region
    
    # 保存
    cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
    print(f"✓ 已保存: {output_path}")
    print(f"  区域: ({x1}, {y1}, {x2}, {y2})")
    print(f"  尺寸: {x2-x1} × {y2-y1}")
    print()

def main():
    print("=" * 70)
    print("按钮提取工具 - 黑色背景模式")
    print("=" * 70)
    print()
    
    # 按钮定义
    buttons = [
        {
            "name": "PHYSICAL_TEST",
            "screenshot": "./screenshot_physical_test.png",
            "coords": (636, 188, 1206, 302),
            "output": "./assets/train/PHYSICAL_TEST.png"
        },
        {
            "name": "SIMPLE_MODE",
            "screenshot": "./screenshot_simple_mode.png",
            "coords": (857, 268, 1072, 315),
            "output": "./assets/train/SIMPLE_MODE.png"
        },
        {
            "name": "CHALLENGE",
            "screenshot": "./screenshot_challenge.png",
            "coords": (1006, 580, 1223, 647),
            "output": "./assets/train/CHALLENGE.png"
        }
    ]
    
    # 提取每个按钮
    for button in buttons:
        print(f"[{button['name']}]")
        
        if not os.path.exists(button['screenshot']):
            print(f"✗ 找不到截图: {button['screenshot']}")
            print()
            continue
        
        extract_button_with_black_background(
            button['screenshot'],
            button['coords'],
            button['output']
        )
    
    print("=" * 70)
    print("完成!")
    print("=" * 70)
    print()
    print("现在可以运行测试:")
    print("  python tests/test_battle_train.py")

if __name__ == "__main__":
    main()
