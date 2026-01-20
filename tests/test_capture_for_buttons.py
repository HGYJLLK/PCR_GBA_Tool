"""
截图工具 - 用于捕获训练场界面的全屏截图
然后可以用这些截图来提取按钮坐标

用法:
    python tests/test_capture_for_buttons.py
    
会生成三张截图:
    1. screenshot_physical_test.png - 物理测试界面
    2. screenshot_simple_mode.png - 简单模式选择界面  
    3. screenshot_challenge.png - 挑战按钮界面
"""

import sys
import time

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.logger import logger

def main():
    """
    主函数 - 捕获三个界面的截图
    """
    config = PriconneConfig("maple", "Pcr")
    device = Device(config)
    device.disable_stuck_detection()
    
    logger.hr("Screenshot Capture Tool", level=0)
    logger.info("这个工具会帮你捕获训练场的三个界面截图")
    logger.info("请按照提示操作...")
    
    # 截图 1: Physical Test 界面
    logger.hr("Step 1: Physical Test 界面", level=1)
    input("请导航到训练场主界面(有物理测试按钮的界面)，然后按 Enter...")
    device.screenshot()
    screenshot_path = "./screenshot_physical_test.png"
    device.image_save(screenshot_path)
    logger.info(f"✓ 已保存截图: {screenshot_path}")
    
    # 截图 2: Simple Mode 界面
    logger.hr("Step 2: Simple Mode 界面", level=1)
    input("请点击物理测试，进入难度选择界面(有简单按钮的界面)，然后按 Enter...")
    device.screenshot()
    screenshot_path = "./screenshot_simple_mode.png"
    device.image_save(screenshot_path)
    logger.info(f"✓ 已保存截图: {screenshot_path}")
    
    # 截图 3: Challenge 界面
    logger.hr("Step 3: Challenge 界面", level=1)
    input("请选择简单模式，进入挑战界面(有挑战按钮的界面)，然后按 Enter...")
    device.screenshot()
    screenshot_path = "./screenshot_challenge.png"
    device.image_save(screenshot_path)
    logger.info(f"✓ 已保存截图: {screenshot_path}")
    
    logger.hr("完成!", level=0)
    logger.info("已保存三张截图:")
    logger.info("  1. screenshot_physical_test.png")
    logger.info("  2. screenshot_simple_mode.png")
    logger.info("  3. screenshot_challenge.png")
    logger.info("")
    logger.info("下一步:")
    logger.info("  1. 打开这些截图，找到按钮的坐标(x1, y1, x2, y2)")
    logger.info("  2. 使用 dev_tools/template_extract.py 提取按钮")
    logger.info("  3. 或者直接告诉我坐标，我帮你提取")

if __name__ == "__main__":
    main()
