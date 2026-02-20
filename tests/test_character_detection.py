"""
角色头像识别可视化测试
对选角色界面截图，识别所有可见角色并用绿框标注角色名
"""

import sys
import os

sys.path.insert(0, "./")

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import module.character.assets as char_assets
from module.base.template import Template
from module.base.mask import Mask
from module.config.config import PriconneConfig
from module.device.device import Device
from module.logger import logger

# ===================== 配置 =====================
SIMILARITY_THRESHOLD = 0.85
OUTPUT_DIR = "./tests/output"
OUTPUT_FILE = "character_detection_result.png"

# 尝试加载支持中文的字体
FONT_PATHS = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/SimHei.ttf",
]
FONT_SIZE = 16


# ===================== 获取全部模板 =====================
def get_all_templates():
    """
    从 character/assets.py 动态读取所有 TEMPLATE_* 对象

    Returns:
        dict: {显示名称: Template对象}
    """
    templates = {}
    for attr_name in dir(char_assets):
        if not attr_name.startswith("TEMPLATE_"):
            continue
        obj = getattr(char_assets, attr_name)
        if isinstance(obj, Template):
            display_name = attr_name[len("TEMPLATE_"):]  # 去掉前缀
            templates[display_name] = obj
    return templates


# ===================== 识别 =====================
def detect_characters(image, templates):
    """
    在给定图像中匹配所有角色模板

    Args:
        image: numpy array (RGB)，截图（已应用遮罩）
        templates: dict {名称: Template}

    Returns:
        list of (name, area, sim)
            area: (x1, y1, x2, y2)
            sim:  相似度 0-1
    """
    results = []
    for name, template in templates.items():
        try:
            sim, button = template.match_result(image, name=name)
            if sim >= SIMILARITY_THRESHOLD:
                results.append((name, button.area, sim))
        except Exception as e:
            logger.error(f"匹配 {name} 出错: {e}")
    return results


# ===================== 可视化 =====================
def draw_detections(image, detections):
    """
    在原始截图上绘制绿色边框和角色名

    Args:
        image: numpy array (RGB)，原始截图（未应用遮罩）
        detections: list of (name, area, sim)

    Returns:
        numpy array (RGB)，标注后的图像
    """
    pil_image = Image.fromarray(image)
    draw = ImageDraw.Draw(pil_image)

    # 加载字体
    font = None
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, FONT_SIZE)
                logger.info(f"字体加载成功: {path}")
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()
        logger.warning("未找到中文字体，使用默认字体（中文可能显示为方块）")

    for name, area, sim in detections:
        x1, y1, x2, y2 = area

        # 绿色边框
        draw.rectangle([x1, y1, x2, y2], outline=(0, 220, 0), width=2)

        # 角色名 + 相似度
        label = f"{name} {sim:.2f}"

        # 文字背景（半透明黑色矩形）
        text_bbox = draw.textbbox((x1, y1), label, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        text_y = y1 - text_h - 4
        if text_y < 0:
            text_y = y2 + 2  # 框下方显示

        bg_x1 = x1
        bg_y1 = text_y - 2
        bg_x2 = x1 + text_w + 4
        bg_y2 = text_y + text_h + 2
        draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(0, 0, 0))

        # 文字
        draw.text((x1 + 2, text_y), label, fill=(0, 255, 0), font=font)

    return np.array(pil_image)


# ===================== 主流程 =====================
def run_detection_test(device):
    """
    执行完整的角色识别可视化测试

    Args:
        device: Device 对象
    """
    logger.hr("角色识别可视化测试", level=0)

    # 1. 截图
    logger.info("截图中...")
    device.screenshot()
    original_image = device.image.copy()
    logger.info(f"截图尺寸: {original_image.shape[1]}x{original_image.shape[0]}")

    # 2. 应用遮罩（只识别角色列表区域）
    try:
        mask = Mask(file="./assets/mask/MASK_CHARACTER_LIST.png")
        masked_image = mask.apply(original_image)
        logger.info("角色列表遮罩应用成功")
    except Exception as e:
        logger.warning(f"遮罩加载失败，使用原图: {e}")
        masked_image = original_image

    # 3. 加载所有角色模板
    templates = get_all_templates()
    logger.info(f"共加载 {len(templates)} 个角色模板")

    # 4. 识别
    logger.hr("开始识别", level=1)
    detections = detect_characters(masked_image, templates)

    # 5. 输出结果
    logger.hr("识别结果", level=1)
    if detections:
        # 按相似度排序
        detections.sort(key=lambda x: x[2], reverse=True)
        logger.info(f"共识别到 {len(detections)} 个角色:")
        for i, (name, area, sim) in enumerate(detections, 1):
            logger.info(f"  {i:2d}. {name:<12}  相似度: {sim:.3f}  位置: {area}")
    else:
        logger.warning("未识别到任何角色（请确认当前界面为角色选择界面）")

    # 6. 绘制可视化结果
    result_image = draw_detections(original_image, detections)

    # 7. 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    Image.fromarray(result_image).save(output_path)
    logger.info(f"结果图像已保存: {os.path.abspath(output_path)}")

    return detections


# ===================== 入口 =====================
def main():
    config = PriconneConfig("maple", "Pcr")
    device = Device(config)
    device.disable_stuck_detection()

    run_detection_test(device)


if __name__ == "__main__":
    main()
