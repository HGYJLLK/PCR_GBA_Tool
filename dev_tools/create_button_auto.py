"""
一体化按钮创建工具 - 终端版本

工作流程:
1. 运行此脚本,自动截图并打开HTML工具
2. 在HTML中框选按钮并输入名称
3. 复制HTML生成的JSON数据
4. 粘贴到此终端
5. 自动完成:提取按钮、保存图片、更新assets.py、清理临时文件

用法:
    python dev_tools/create_button_auto.py
"""

import sys
import os
import json
import webbrowser
import cv2
import numpy as np

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.logger import logger
from module.base.utils import load_image

class AutoButtonCreator:
    def __init__(self):
        self.config = PriconneConfig("maple", "Pcr")
        self.device = Device(self.config)
        self.device.disable_stuck_detection()
        self.screenshot_path = "./temp_screenshot.png"
    
    def capture_and_open_html(self):
        """截图并打开HTML工具"""
        logger.hr("Step 1: 截图并打开HTML工具", level=1)
        input("请确保游戏界面显示你要提取的按钮,然后按 Enter...")
        
        # 截图
        self.device.screenshot()
        self.device.image_save(self.screenshot_path)
        logger.info(f"✓ 已保存截图: {self.screenshot_path}")
        
        # 打开HTML
        html_path = os.path.abspath("./dev_tools/button_creator.html")
        webbrowser.open(f"file:///{html_path}")
        logger.info("✓ 已在浏览器中打开选择工具")
        logger.info("")
    
    def get_button_data(self):
        """从用户输入获取按钮数据"""
        logger.hr("Step 2: 粘贴按钮数据", level=1)
        logger.info("请在HTML中:")
        logger.info("  1. 框选按钮区域")
        logger.info("  2. 输入按钮名称")
        logger.info("  3. 点击'生成并下载按钮'")
        logger.info("  4. 复制生成的JSON数据")
        logger.info("")
        
        while True:
            data_str = input("请粘贴JSON数据 (或输入 'q' 退出): ").strip()
            
            if data_str.lower() == 'q':
                return None
            
            try:
                data = json.loads(data_str)
                button_name = data['name']
                coords = tuple(data['coords'])
                
                logger.info(f"✓ 按钮名称: {button_name}")
                logger.info(f"✓ 坐标: {coords}")
                
                return {"name": button_name, "coords": coords}
            except json.JSONDecodeError:
                logger.error("✗ JSON 格式错误,请重新复制粘贴")
            except KeyError:
                logger.error("✗ 数据格式错误,缺少必要字段")
    
    def extract_button(self, button_data):
        """提取按钮并保存"""
        logger.hr("Step 3: 提取并保存按钮", level=1)
        
        button_name = button_data['name']
        x1, y1, x2, y2 = button_data['coords']
        
        # 加载截图
        screenshot = load_image(self.screenshot_path)
        h, w = screenshot.shape[:2]
        
        # 创建黑色背景
        result = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 提取按钮区域
        button_region = screenshot[y1:y2, x1:x2]
        result[y1:y2, x1:x2] = button_region
        
        # 保存
        output_path = f"./assets/train/{button_name}.png"
        cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
        
        logger.info(f"✓ 已保存按钮图片: {output_path}")
        logger.info(f"  尺寸: {x2-x1} × {y2-y1}")
        
        return output_path, (x1, y1, x2, y2)
    
    def update_assets_file(self, button_name, coords):
        """更新 assets.py"""
        logger.hr("Step 4: 更新 assets.py", level=1)
        
        x1, y1, x2, y2 = coords
        button_def = f'{button_name} = Button(area=({x1}, {y1}, {x2}, {y2}), color=(100, 150, 200), button=({x1}, {y1}, {x2}, {y2}), file="./assets/train/{button_name}.png")'
        
        logger.info("生成的 Button 定义:")
        logger.info(f"  {button_def}")
        logger.info("")
        logger.info("✓ 请手动将上面的代码添加到: module/train/assets.py")
    
    def cleanup(self):
        """清理临时文件"""
        logger.hr("Step 5: 清理临时文件", level=1)
        
        if os.path.exists(self.screenshot_path):
            os.remove(self.screenshot_path)
            logger.info(f"✓ 已删除临时截图: {self.screenshot_path}")
    
    def run(self):
        """运行完整流程"""
        logger.hr("一体化按钮创建工具", level=0)
        
        try:
            # 1. 截图并打开HTML
            self.capture_and_open_html()
            
            # 2. 获取按钮数据
            button_data = self.get_button_data()
            if not button_data:
                logger.warning("用户取消操作")
                return
            
            # 3. 提取按钮
            output_path, coords = self.extract_button(button_data)
            
            # 4. 更新assets文件
            self.update_assets_file(button_data['name'], coords)
            
            # 5. 清理
            self.cleanup()
            
            logger.hr("完成!", level=0)
            logger.info(f"✓ 按钮已成功创建: {output_path}")
            logger.info("✓ 临时文件已清理")
            logger.info("")
            logger.info("下一步:")
            logger.info("  1. 将上面的代码添加到 module/train/assets.py")
            logger.info("  2. 运行测试: python tests/test_battle_train.py")
            
        except KeyboardInterrupt:
            logger.warning("\n用户取消操作")
            self.cleanup()
        except Exception as e:
            logger.error(f"发生错误: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()

def main():
    creator = AutoButtonCreator()
    creator.run()

if __name__ == "__main__":
    main()
