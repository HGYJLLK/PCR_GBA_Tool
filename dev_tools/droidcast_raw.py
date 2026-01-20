#!/usr/bin/env python3
"""
PCR DroidCast_raw截图
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "."))

try:
    from module.config.config import PriconneConfig
    from module.device.device import Device
    import cv2
    import time
    from datetime import datetime

    print("=" * 60)
    print("PCR DroidCast_raw截图")
    print("=" * 60)

    # 初始化配置
    print("\n 初始化配置...")
    config = PriconneConfig(config_name="cwj")

    # 初始化设备
    print(" 连接设备...")
    device = Device(config)

    # 初始化DroidCast服务
    print(" 初始化DroidCast服务...")
    device.droidcast_init()

    # 等待服务完全启动
    print(" 等待服务启动...")
    time.sleep(2)

    # 截图
    print(" 执行DroidCast_raw截图...")
    start_time = time.time()
    image = device.screenshot_droidcast_raw()
    # 计算耗时，单位为秒
    elapsed = time.time() - start_time

    print(f" 截图成功!")
    # 将耗时格式化为保留三位小数的秒
    print(f"  - 耗时: {elapsed:.3f}s")
    print(f"  - 图像尺寸: {image.shape[1]}x{image.shape[0]}")
    print(f"  - 颜色格式: RGB" if image.shape[2] == 3 else "  - 颜色格式: 未知")
    print(f"  - 数据类型: {image.dtype}")

    # 保存截图
    print(" 保存截图...")
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"logs/ui/screenshot_{timestamp}.png"
    # 确保目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # 转换回BGR格式保存
    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_path, image_bgr)
    print(f" 截图已保存: {output_path}")

    print("\n" + "=" * 60)

except Exception as e:
    print(f"\n 截图失败: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
