#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滚动条按钮创建工具

功能:
1. 自动截图当前游戏界面
2. 在浏览器中打开HTML工具，框选两次：
   - 第一次：滚动条轨道区域（整条滚动条的范围）
   - 第二次：滑块颜色区域（滑块当前所在的位置）
3. 自动提取颜色并生成 Button 定义 + Scroll() 实例化代码
4. 保存图片并写入指定模块的 assets.py

用法:
    python dev_tools/create_scroll.py
    python dev_tools/create_scroll.py --module character

工作流程:
    1. 输入目标模块名（默认 character）
    2. 脚本截图并打开网页
    3. 框选滚动条轨道区域 → 输入名称 → 复制JSON → 粘贴到控制台
    4. 框选滑块颜色区域 → 输入名称（随意，如 COLOR）→ 复制JSON → 粘贴到控制台
    5. 脚本自动生成定义并写入 assets.py
"""

import sys
import os
import webbrowser
import json
import argparse

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.logger import logger


class ScrollCreator:
    def __init__(self, module_name="character"):
        self.config = PriconneConfig("maple", "Pcr")
        self.device = Device(self.config)
        self.device.disable_stuck_detection()
        self.screenshot_path = "./temp_screenshot.png"
        self.module_name = module_name

        self.track_data = None   # 第一次框选：轨道区域
        self.color_data = None   # 第二次框选：滑块颜色区域
        self.created_scrolls = []

    def capture_screenshot(self):
        logger.hr("Step 1: 截图", level=1)
        input("请确保游戏界面显示滚动条，然后按 Enter...")
        self.device.screenshot()
        self.device.image_save(self.screenshot_path)
        logger.info(f"✓ 已保存截图: {self.screenshot_path}")

    def open_html_selector(self):
        logger.hr("Step 2: 打开选择工具", level=1)

        with open("./dev_tools/button_creator.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        import base64
        import cv2
        from module.base.utils import load_image

        img_array = load_image(self.screenshot_path)
        success, encoded_image = cv2.imencode(
            ".png", cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        )
        if not success:
            logger.error("Failed to encode image")
            return False

        base64_image = base64.b64encode(encoded_image.tobytes()).decode("utf-8")
        temp_html_path = "./temp_button_creator.html"
        html_content = html_content.replace(
            'img.src = "../temp_screenshot.png?t=" + new Date().getTime();',
            f'img.src = "data:image/png;base64,{base64_image}";',
        )
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        html_path = os.path.abspath(temp_html_path)
        if sys.platform == "darwin":
            os.system(f'open "{html_path}"')
        else:
            webbrowser.open(f"file:///{html_path}")

        logger.info("✓ 已在浏览器中打开选择工具")

    def get_json_input(self, prompt):
        """从控制台读取一条 JSON 输入，空行返回 None"""
        logger.info(prompt)
        raw = input().strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
            coords = tuple(data["coords"])
            name = data.get("name", "SCROLL")
            return {"name": name, "coords": coords}
        except Exception as e:
            logger.error(f"JSON解析失败: {e}")
            return None

    def extract_color(self, coords):
        """从截图指定区域提取平均颜色"""
        import numpy as np
        from module.base.utils import load_image, get_color

        screenshot = load_image(self.screenshot_path)
        x1, y1, x2, y2 = coords
        color = get_color(image=screenshot, area=(x1, y1, x2, y2))
        return tuple(int(c) for c in color)

    def save_track_image(self, name, coords):
        """将轨道区域截图保存到 assets/<module>/<name>.png"""
        import numpy as np
        from PIL import Image
        from module.base.utils import load_image

        screenshot = load_image(self.screenshot_path)
        h, w = screenshot.shape[:2]
        result = np.zeros((h, w, 3), dtype=np.uint8)
        x1, y1, x2, y2 = coords
        result[y1:y2, x1:x2] = screenshot[y1:y2, x1:x2]

        output_dir = f"./assets/{self.module_name}"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.abspath(f"{output_dir}/{name}.png")
        Image.fromarray(result.astype("uint8")).save(output_path, "PNG")
        logger.info(f"✓ 已保存轨道图片: {output_path}")
        return output_path

    def collect_scroll_definition(self, track_name, track_coords, track_color, handle_color):
        """生成 Button 定义 + Scroll 实例化建议，加入待写入列表"""
        x1, y1, x2, y2 = track_coords

        button_def = (
            f'{track_name} = Button('
            f'area=({x1}, {y1}, {x2}, {y2}), '
            f'color={track_color}, '
            f'button=({x1}, {y1}, {x2}, {y2}), '
            f'file="./assets/{self.module_name}/{track_name}.png")'
        )

        scroll_hint = (
            f'# Scroll(\n'
            f'#     area={track_name}.area,\n'
            f'#     color={handle_color},\n'
            f'#     name="{track_name}",\n'
            f'#     swipe_area=(...),\n'
            f'# )'
        )

        self.created_scrolls.append((button_def, scroll_hint))

        logger.info("生成的 Button 定义:")
        logger.info(f"  {button_def}")
        logger.info("对应 Scroll() 实例化参考:")
        for line in scroll_hint.splitlines():
            logger.info(f"  {line}")

    def write_all_to_file(self):
        if not self.created_scrolls:
            logger.warning("没有创建任何滚动条")
            return False

        logger.hr("写入 assets.py", level=1)
        assets_file = f"./module/{self.module_name}/assets.py"

        if not os.path.exists(assets_file):
            with open(assets_file, "w", encoding="utf-8") as f:
                f.write(
                    "from module.base.button import Button\n"
                    "from module.base.template import Template\n\n"
                    "# This file was automatically generated by dev_tools/button_extract.py.\n"
                    "# Don't modify it manually.\n\n"
                )

        with open(assets_file, "a", encoding="utf-8") as f:
            for button_def, scroll_hint in self.created_scrolls:
                f.write(button_def + "\n")
                for line in scroll_hint.splitlines():
                    f.write(line + "\n")
                f.write("\n")

        logger.info(f"✓ 已写入 {len(self.created_scrolls)} 个滚动条到 {assets_file}")

    def cleanup(self):
        for path in [self.screenshot_path, "./temp_button_creator.html"]:
            if os.path.exists(path):
                os.remove(path)

    def run_one(self):
        """完成一个滚动条的两步框选流程，返回 True 继续 / False 退出"""
        # ---- 第一步：轨道区域 ----
        logger.info("")
        logger.info("【第一步】框选滚动条轨道区域（整条滚动条的范围），输入名称，复制JSON后粘贴到这里")
        logger.info("（直接回车退出）")
        self.track_data = self.get_json_input("> ")
        if self.track_data is None:
            return False

        # ---- 第二步：滑块颜色区域 ----
        logger.info("")
        logger.info("【第二步】框选滑块的颜色区域（滑块当前所在的位置），随便取个名称，复制JSON后粘贴到这里")
        self.color_data = self.get_json_input("> ")
        if self.color_data is None:
            logger.warning("未提供颜色区域，跳过此滚动条")
            return True

        track_name = self.track_data["name"].upper()
        track_coords = self.track_data["coords"]
        track_color = self.extract_color(track_coords)
        handle_color = self.extract_color(self.color_data["coords"])

        self.save_track_image(track_name, track_coords)
        self.save_track_image(f"{track_name}_滑块", self.color_data["coords"])
        self.collect_scroll_definition(track_name, track_coords, track_color, handle_color)
        return True

    def run(self):
        logger.hr("滚动条创建工具", level=0)
        logger.info(f"目标模块: {self.module_name}")

        try:
            self.capture_screenshot()
            self.open_html_selector()

            logger.hr("开始创建滚动条", level=0)
            logger.info("在网页中框选区域并复制JSON到控制台")
            logger.info("每个滚动条需要框选两次：轨道区域 + 滑块颜色区域")
            logger.info("第一步直接回车退出")

            while True:
                if not self.run_one():
                    break

            if self.created_scrolls:
                self.write_all_to_file()

            self.cleanup()
            logger.hr("完成!", level=0)
            logger.info(f"✓ 共创建 {len(self.created_scrolls)} 个滚动条")

        except KeyboardInterrupt:
            logger.warning("用户取消操作")
            if self.created_scrolls:
                self.write_all_to_file()
            self.cleanup()
        except Exception as e:
            logger.error(f"发生错误: {e}")
            import traceback
            traceback.print_exc()
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(description="滚动条按钮创建工具")
    parser.add_argument(
        "--module", "-m",
        default=None,
        help="目标模块名，如 character / train / ghz（不指定则交互输入）"
    )
    args = parser.parse_args()

    module_name = args.module
    if not module_name:
        print("请输入目标模块名（如 character / train / ghz）: ", end="", flush=True)
        module_name = input().strip() or "character"

    creator = ScrollCreator(module_name=module_name)
    creator.run()


if __name__ == "__main__":
    main()
