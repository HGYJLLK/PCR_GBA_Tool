#!/usr/bin/env python3
"""
测试PCR DroidCast_raw截图功能
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "."))

try:
    from module.config.config import PriconneConfig
    from module.device.device import Device
    import cv2
    import time

    print("=" * 60)
    print("PCR DroidCast_raw截图功能测试")
    print("=" * 60)

    # 初始化配置
    print("\n[1/6] 初始化配置...")
    config = PriconneConfig(config_name="cwj")

    # 初始化设备
    print("[2/6] 连接设备...")
    device = Device(config)

    # 初始化DroidCast服务
    print("[3/6] 初始化DroidCast服务...")
    device.droidcast_init()

    # 等待服务完全启动
    print("[4/6] 等待服务启动...")
    time.sleep(2)

    # 测试截图
    print("[5/6] 执行DroidCast_raw截图...")
    start_time = time.time()
    image = device.screenshot_droidcast_raw()
    # 计算耗时，单位为秒
    elapsed = time.time() - start_time

    print(f"✓ 截图成功!")
    # 将耗时格式化为保留三位小数的秒
    print(f"  - 耗时: {elapsed:.3f}s")
    print(f"  - 图像尺寸: {image.shape[1]}x{image.shape[0]}")
    print(f"  - 颜色格式: RGB" if image.shape[2] == 3 else "  - 颜色格式: 未知")
    print(f"  - 数据类型: {image.dtype}")

    # 保存截图
    print("[6/6] 保存截图...")
    output_path = "test_droidcast_raw.png"
    # 转换回BGR格式保存
    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_path, image_bgr)
    print(f"✓ 截图已保存: {output_path}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    # # 性能对比测试
    # print("\n" + "=" * 60)
    # print("性能对比测试 (10次截图)")
    # print("=" * 60)

    # # DroidCast_raw性能测试
    # print("\n测试DroidCast_raw截图性能...")
    # times = []
    # for i in range(10):
    #     start = time.time()
    #     _ = device.screenshot_droidcast_raw()
    #     # 计算耗时，单位为秒
    #     elapsed = time.time() - start
    #     times.append(elapsed)
    #     # 将耗时格式化为保留三位小数的秒
    #     print(f"  第{i+1}次: {elapsed:.3f}s")

    # avg = sum(times) / len(times)
    # # 将结果格式化为保留三位小数的秒
    # print(f"\n平均耗时: {avg:.3f}s")
    # print(f"最快: {min(times):.3f}s")
    # print(f"最慢: {max(times):.3f}s")

except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
