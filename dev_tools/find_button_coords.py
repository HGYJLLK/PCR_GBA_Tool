"""
自动查找按钮坐标工具
使用模板匹配在全屏截图中找到按钮的位置

用法:
    python dev_tools/find_button_coords.py
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, "./")

from module.base.utils import load_image

def find_button_location(screenshot_path, button_path):
    """
    在截图中查找按钮位置
    
    Args:
        screenshot_path: 全屏截图路径
        button_path: 按钮图片路径
        
    Returns:
        tuple: (x1, y1, x2, y2) 或 None
    """
    if not os.path.exists(screenshot_path):
        print(f"✗ 找不到截图: {screenshot_path}")
        return None
    
    if not os.path.exists(button_path):
        print(f"✗ 找不到按钮图片: {button_path}")
        return None
    
    # 加载图片
    screenshot = load_image(screenshot_path)
    button = load_image(button_path)
    
    # 模板匹配
    result = cv2.matchTemplate(screenshot, button, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    
    if max_val > 0.6:  # 相似度阈值
        h, w = button.shape[:2]
        x1, y1 = max_loc
        x2, y2 = x1 + w, y1 + h
        
        print(f"✓ 找到按钮!")
        print(f"  相似度: {max_val:.2%}")
        print(f"  位置: ({x1}, {y1}, {x2}, {y2})")
        print(f"  尺寸: {w}×{h}")
        print(f"  中心点: ({x1 + w//2}, {y1 + h//2})")
        
        return (x1, y1, x2, y2)
    else:
        print(f"✗ 未找到按钮 (最高相似度: {max_val:.2%})")
        return None

def main():
    print("=" * 70)
    print("自动查找按钮坐标工具")
    print("=" * 70)
    print()
    
    # 查找三个按钮
    buttons = [
        ("Physical Test", "./screenshot_physical_test.png", "./assets/train/PHYSICAL_TEST.png"),
        ("Simple Mode", "./screenshot_simple_mode.png", "./assets/train/SIMPLE_MODE.png"),
        ("Challenge", "./screenshot_challenge.png", "./assets/train/CHALLENGE.png"),
    ]
    
    results = {}
    
    for name, screenshot, button in buttons:
        print(f"[{name}]")
        coords = find_button_location(screenshot, button)
        if coords:
            results[name] = coords
        print()
    
    # 生成 Button 定义代码
    if results:
        print("=" * 70)
        print("生成的 Button 定义:")
        print("=" * 70)
        print()
        
        for name, coords in results.items():
            button_name = name.upper().replace(" ", "_")
            file_path = f"./assets/train/{button_name}.png"
            
            # 简化的颜色(可以后续优化)
            color = (100, 150, 200)
            
            print(f'{button_name} = Button(area={coords}, color={color}, button={coords}, file="{file_path}")')
        
        print()
        print("复制上面的代码到 module/train/assets.py 中")

if __name__ == "__main__":
    main()
