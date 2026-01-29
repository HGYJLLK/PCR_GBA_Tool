#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一体化按钮提取工具

功能:
1. 自动截图当前游戏界面
2. 在浏览器中打开HTML工具让你框选按钮
3. 输入按钮名称
4. 自动提取按钮并保存到 assets/train/ 目录(黑色背景)
5. 自动更新 module/train/assets.py

用法:
    python dev_tools/create_button.py
"""

import sys
import os
import time
import webbrowser
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.logger import logger

class ButtonCreator:
    def __init__(self):
        self.config = PriconneConfig("maple", "Pcr")
        self.device = Device(self.config)
        self.device.disable_stuck_detection()
        self.screenshot_path = "./temp_screenshot.png"
        self.button_data = None
    
    def capture_screenshot(self):
        """捕获当前游戏界面截图"""
        logger.hr("Step 1: 截图", level=1)
        input("请确保游戏界面显示你要提取的按钮,然后按 Enter...")
        
        self.device.screenshot()
        self.device.image_save(self.screenshot_path)
        logger.info(f"✓ 已保存截图: {self.screenshot_path}")
        return True
    
    def open_html_selector(self):
        """在浏览器中打开HTML选择工具"""
        logger.hr("Step 2: 选择按钮区域", level=1)
        logger.info("正在打开浏览器...")
        
        # 创建临时HTML文件,包含截图路径
        html_path = "./dev_tools/button_creator.html"
        
        # 打开浏览器
        webbrowser.open(f"file:///{os.path.abspath(html_path)}")
        logger.info("✓ 已在浏览器中打开选择工具")
        logger.info("")
        logger.info("请在浏览器中:")
        logger.info("  1. 点击'选择截图'按钮,选择 temp_screenshot.png")
        logger.info("  2. 在图片上拖动鼠标框选按钮区域")
        logger.info("  3. 记下显示的坐标")
        logger.info("")
        
        return True
    
    def get_button_info(self):
        """获取按钮信息"""
        logger.hr("Step 3: 输入按钮信息", level=1)
        
        button_name = input("请输入按钮名称 (例如: PHYSICAL_TEST，中文直接输入): ").strip()
        # 英文自动转换为大写，中文保持不变
        try:
            # 检查是否全为英文和数字
            if button_name.isalnum():
                button_name = button_name.upper()
        except:
            # 处理中文等特殊字符
            pass
        
        print("请输入按钮坐标 (从HTML工具中复制):")
        x1 = int(input("  左上角 X: "))
        y1 = int(input("  左上角 Y: "))
        x2 = int(input("  右下角 X: "))
        y2 = int(input("  右下角 Y: "))
        
        self.button_data = {
            "name": button_name,
            "coords": (x1, y1, x2, y2)
        }
        
        logger.info(f"✓ 按钮名称: {button_name}")
        logger.info(f"✓ 坐标: ({x1}, {y1}, {x2}, {y2})")
        
        return True
    
    def extract_and_save_button(self):
        """提取按钮并保存为黑色背景图片"""
        logger.hr("Step 4: 提取并保存按钮", level=1)
        
        import numpy as np
        from PIL import Image
        from module.base.utils import load_image
        
        # 加载截图
        screenshot = load_image(self.screenshot_path)
        h, w = screenshot.shape[:2]
        
        # 创建黑色背景
        result = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 提取按钮区域
        x1, y1, x2, y2 = self.button_data["coords"]
        button_region = screenshot[y1:y2, x1:x2]
        
        # 复制到黑色背景
        result[y1:y2, x1:x2] = button_region
        
        # 保存，使用PIL替代CV2以支持中文路径
        output_path = os.path.abspath(f"./assets/train/{self.button_data['name']}.png")
        # 将numpy数组转换为PIL Image
        pil_image = Image.fromarray(result.astype('uint8'))
        pil_image.save(output_path, 'PNG')
        
        logger.info(f"✓ 已保存按钮图片: {output_path}")
        logger.info(f"  尺寸: {x2-x1} × {y2-y1}")
        
        return output_path
    
    def update_assets_file(self):
        """更新 module/train/assets.py"""
        logger.hr("Step 5: 更新 assets.py", level=1)
        
        x1, y1, x2, y2 = self.button_data["coords"]
        button_name = self.button_data["name"]
        
        # 生成 Button 定义
        button_def = f'{button_name} = Button(area=({x1}, {y1}, {x2}, {y2}), color=(100, 150, 200), button=({x1}, {y1}, {x2}, {y2}), file="./assets/train/{button_name}.png")'
        
        logger.info("生成的 Button 定义:")
        logger.info(f"  {button_def}")
        logger.info("")
        logger.info("请手动将上面的代码添加到:")
        logger.info("  module/train/assets.py")
        
        return True
    
    def cleanup(self):
        """清理临时文件"""
        if os.path.exists(self.screenshot_path):
            os.remove(self.screenshot_path)
            logger.info(f"✓ 已删除临时截图: {self.screenshot_path}")
    
    def run(self):
        """运行完整流程"""
        logger.hr("按钮提取工具", level=0)
        
        try:
            # 1. 截图
            self.capture_screenshot()
            
            # 2. 打开HTML工具
            self.open_html_selector()
            
            # 3. 获取按钮信息
            self.get_button_info()
            
            # 4. 提取并保存
            output_path = self.extract_and_save_button()
            
            # 5. 更新assets文件
            self.update_assets_file()
            
            # 6. 清理临时文件
            self.cleanup()
            
            logger.hr("完成!", level=0)
            logger.info(f"✓ 按钮已成功创建: {output_path}")
            logger.info("✓ 临时文件已清理")
            
        except KeyboardInterrupt:
            logger.warning("用户取消操作")
            self.cleanup()
        except Exception as e:
            logger.error(f"发生错误: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()

def main():
    creator = ButtonCreator()
    creator.run()

if __name__ == "__main__":
    main()