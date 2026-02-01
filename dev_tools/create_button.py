#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量按钮创建工具

功能:
1. 自动截图当前游戏界面
2. 在浏览器中打开HTML工具让你框选按钮区域
3. 在网页中输入按钮名称，生成JSON
4. 复制JSON到控制台，自动提取按钮并保存到 assets/train/
5. 可以连续创建多个按钮
6. 直接回车退出，自动将所有按钮写入 module/train/assets.py

用法:
    python dev_tools/create_button.py

工作流程:
    1. 脚本截图并打开网页
    2. 在网页框选按钮区域 → 输入名称 → 复制JSON
    3. 粘贴JSON到控制台 → 回车
    4. 重复步骤2-3创建更多按钮
    5. 控制台直接回车退出并保存所有按钮
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
        self.created_buttons = []  # 存储所有创建的按钮定义

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
        logger.info("正在准备HTML选择工具...")

        # 读取原始HTML模板
        with open("./dev_tools/button_creator.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        # 将截图转换为Base64格式
        # 重要：使用OpenCV重新编码PNG，避免浏览器进行颜色空间转换
        import base64
        import cv2
        from module.base.utils import load_image

        # 使用load_image加载（已经是RGB格式的numpy数组）
        img_array = load_image(self.screenshot_path)

        # 使用cv2编码为PNG字节流（不包含颜色配置文件和sRGB chunk）
        # cv2编码的PNG是原始像素值，不会添加颜色管理信息
        success, encoded_image = cv2.imencode(
            ".png", cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        )

        if not success:
            logger.error("Failed to encode image")
            return False

        base64_image = base64.b64encode(encoded_image.tobytes()).decode("utf-8")

        # 创建临时HTML文件，包含Base64图像数据
        temp_html_path = "./temp_button_creator.html"

        # 使用更可靠的替换方式：替换图片源
        # 直接替换 img.src 的赋值语句
        html_content = html_content.replace(
            'img.src = "../temp_screenshot.png?t=" + new Date().getTime();',
            f'img.src = "data:image/png;base64,{base64_image}";',
        )

        # 写入临时HTML文件
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 打开浏览器
        html_path = os.path.abspath(temp_html_path)
        try:
            # macOS上使用open命令
            if sys.platform == "darwin":
                os.system(f'open "{html_path}"')
            else:
                webbrowser.open(f"file:///{html_path}")
            logger.info("✓ 已在浏览器中打开选择工具")
        except Exception as e:
            logger.warning(f"自动打开浏览器失败: {e}")
            logger.info(f"请手动打开此文件: {html_path}")

        logger.info("")
        logger.info("请在浏览器中:")
        logger.info("  1. 在图片上拖动鼠标框选按钮区域")
        logger.info("  2. 输入按钮名称")
        logger.info("  3. 复制生成的JSON数据")
        logger.info("")

        return True

    def parse_json_input(self, json_str):
        """
        解析JSON输入

        Args:
            json_str: JSON字符串，格式: {"name": "BUTTON_NAME", "coords": [x1, y1, x2, y2]}

        Returns:
            dict: 按钮数据，或None（如果解析失败）
        """
        try:
            data = json.loads(json_str)
            button_name = data["name"]
            coords = data["coords"]

            # 英文自动转换为大写，中文保持不变
            try:
                if button_name.isalnum():
                    button_name = button_name.upper()
            except:
                pass

            return {"name": button_name, "coords": tuple(coords)}
        except Exception as e:
            logger.error(f"JSON解析失败: {e}")
            return None

    def get_button_info_from_json(self):
        """
        从JSON输入获取按钮信息（循环模式）

        Returns:
            bool: True表示继续，False表示退出
        """
        logger.hr("等待输入", level=1)
        logger.info("请从网页复制JSON数据并粘贴（直接回车退出）:")

        json_input = input().strip()

        # 空输入表示退出
        if not json_input:
            return False

        # 解析JSON
        self.button_data = self.parse_json_input(json_input)

        if self.button_data is None:
            logger.warning("输入格式错误，请重新输入")
            return True  # 继续循环

        x1, y1, x2, y2 = self.button_data["coords"]
        logger.info(f"✓ 按钮名称: {self.button_data['name']}")
        logger.info(f"✓ 坐标: ({x1}, {y1}, {x2}, {y2})")

        return True

    def extract_and_save_button(self):
        """提取按钮并保存为黑色背景图片"""
        logger.hr("Step 4: 提取并保存按钮", level=1)

        import numpy as np
        from PIL import Image
        from module.base.utils import load_image, get_color

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

        # 计算按钮区域的平均颜色
        color = get_color(image=screenshot, area=(x1, y1, x2, y2))
        color = tuple(np.rint(color).astype(int))
        self.button_data["color"] = color

        # 保存，使用PIL替代CV2以支持中文路径
        output_path = os.path.abspath(f"./assets/train/{self.button_data['name']}.png")
        # 将numpy数组转换为PIL Image
        pil_image = Image.fromarray(result.astype("uint8"))
        pil_image.save(output_path, "PNG")

        logger.info(f"✓ 已保存按钮图片: {output_path}")
        logger.info(f"  尺寸: {x2-x1} × {y2-y1}")

        return output_path

    def collect_button_definition(self):
        """收集按钮定义（暂不写入文件）"""
        x1, y1, x2, y2 = self.button_data["coords"]
        button_name = self.button_data["name"]
        color = self.button_data["color"]

        # 生成 Button 定义
        button_def = f'{button_name} = Button(area=({x1}, {y1}, {x2}, {y2}), color={color}, button=({x1}, {y1}, {x2}, {y2}), file="./assets/train/{button_name}.png")'

        self.created_buttons.append(button_def)

        logger.info("生成的 Button 定义:")
        logger.info(f"  {button_def}")

        return True

    def write_all_buttons_to_file(self):
        """将所有按钮定义追加到 module/train/assets.py"""
        if not self.created_buttons:
            logger.warning("没有创建任何按钮")
            return False

        logger.hr("写入 assets.py", level=1)

        assets_file = "./module/train/assets.py"

        # 确保文件存在
        if not os.path.exists(assets_file):
            # 创建新文件
            with open(assets_file, "w", encoding="utf-8") as f:
                f.write(
                    """from module.base.button import Button
from module.base.template import Template

# This file was automatically generated by dev_tools/button_extract.py.
# Don't modify it manually.

"""
                )

        # 追加新按钮（在文件末尾）
        with open(assets_file, "a", encoding="utf-8") as f:
            for button_def in self.created_buttons:
                f.write(button_def + "\n")

        logger.info(f"✓ 已写入 {len(self.created_buttons)} 个按钮到 {assets_file}")
        for button_def in self.created_buttons:
            logger.info(f"  • {button_def.split('=')[0].strip()}")

        return True

    def cleanup(self):
        """清理临时文件"""
        if os.path.exists(self.screenshot_path):
            os.remove(self.screenshot_path)
            logger.info(f"✓ 已删除临时截图: {self.screenshot_path}")

        # 清理临时HTML文件
        temp_html_path = "./temp_button_creator.html"
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
            logger.info(f"✓ 已删除临时HTML文件: {temp_html_path}")

    def run(self):
        """运行完整流程（批量创建模式）"""
        logger.hr("批量按钮创建工具", level=0)

        try:
            # 1. 截图
            self.capture_screenshot()

            # 2. 打开HTML工具
            self.open_html_selector()

            logger.hr("开始批量创建", level=0)
            logger.info("从网页框选按钮并复制JSON到这里")
            logger.info("直接回车退出并保存所有按钮")
            logger.info("")

            # 3. 循环接收JSON输入
            while True:
                # 获取按钮信息（从JSON）
                should_continue = self.get_button_info_from_json()

                if not should_continue:
                    # 用户输入空行，退出循环
                    break

                if self.button_data is None:
                    # 解析失败，继续下一轮
                    continue

                # 4. 提取并保存按钮
                try:
                    output_path = self.extract_and_save_button()
                    logger.info(f"✓ 按钮图片已保存: {output_path}")

                    # 5. 收集按钮定义
                    self.collect_button_definition()
                    logger.info("✓ 按钮定义已收集")
                    logger.info("")

                except Exception as e:
                    logger.error(f"处理按钮时出错: {e}")
                    import traceback

                    traceback.print_exc()
                    continue

            # 6. 写入所有按钮到 assets.py
            if self.created_buttons:
                self.write_all_buttons_to_file()

            # 7. 清理临时文件
            self.cleanup()

            logger.hr("完成!", level=0)
            logger.info(f"✓ 共创建 {len(self.created_buttons)} 个按钮")
            logger.info("✓ 临时文件已清理")

        except KeyboardInterrupt:
            logger.warning("用户取消操作")
            # 即使取消也要保存已创建的按钮
            if self.created_buttons:
                logger.info("正在保存已创建的按钮...")
                self.write_all_buttons_to_file()
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
