"""
测试截图各阶段耗时
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import numpy as np
import cv2
import requests

def test_screenshot_timing():
    """测试 DroidCast_raw 截图各阶段耗时"""
    from module.device.device import Device
    from module.config.config import Config

    config = Config()
    device = Device(config)

    # 预热
    print("预热中...")
    for _ in range(5):
        device.screenshot_droidcast_raw()

    # 测试次数
    N = 50

    http_times = []
    decode_times = []
    total_times = []

    # 获取 session 和 URL
    session = device.droidcast_session
    url = device.droidcast_raw_url()
    shape = (720, 1280)

    print(f"测试 {N} 次截图...")
    print(f"URL: {url}")

    for i in range(N):
        t0 = time.perf_counter()

        # HTTP 请求
        response = session.get(url, timeout=3)
        image_data = response.content
        t1 = time.perf_counter()

        # 解码 RGB565 -> RGB888
        arr = np.frombuffer(image_data, dtype=np.uint16).reshape(shape)

        r = cv2.bitwise_and(arr, 0b1111100000000000)
        r = cv2.convertScaleAbs(r, alpha=0.00390625)
        m = cv2.convertScaleAbs(r, alpha=0.03125)
        cv2.add(r, m, dst=r)

        g = cv2.bitwise_and(arr, 0b0000011111100000)
        g = cv2.convertScaleAbs(g, alpha=0.125)
        m = cv2.convertScaleAbs(g, alpha=0.015625, dst=m)
        cv2.add(g, m, dst=g)

        b = cv2.bitwise_and(arr, 0b0000000000011111)
        b = cv2.convertScaleAbs(b, alpha=8)
        m = cv2.convertScaleAbs(b, alpha=0.03125, dst=m)
        cv2.add(b, m, dst=b)

        image = cv2.merge([r, g, b])
        t2 = time.perf_counter()

        http_time = (t1 - t0) * 1000
        decode_time = (t2 - t1) * 1000
        total_time = (t2 - t0) * 1000

        http_times.append(http_time)
        decode_times.append(decode_time)
        total_times.append(total_time)

        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{N} 完成")

    print("\n" + "="*50)
    print("截图耗时分析")
    print("="*50)
    print(f"HTTP请求 (含模拟器截屏+传输):")
    print(f"  平均: {np.mean(http_times):.1f}ms")
    print(f"  最小: {np.min(http_times):.1f}ms")
    print(f"  最大: {np.max(http_times):.1f}ms")
    print(f"  标准差: {np.std(http_times):.1f}ms")

    print(f"\nRGB565解码:")
    print(f"  平均: {np.mean(decode_times):.1f}ms")
    print(f"  最小: {np.min(decode_times):.1f}ms")
    print(f"  最大: {np.max(decode_times):.1f}ms")

    print(f"\n总计:")
    print(f"  平均: {np.mean(total_times):.1f}ms")
    print(f"  理论 FPS: {1000/np.mean(total_times):.1f}")

    print("\n" + "="*50)
    print("数据传输分析")
    print("="*50)
    data_size = len(image_data)
    print(f"数据大小: {data_size} 字节 ({data_size/1024/1024:.2f} MB)")
    print(f"分辨率: {shape[1]}x{shape[0]}")

    # 计算网络带宽
    avg_http_time = np.mean(http_times) / 1000  # 秒
    bandwidth = data_size / avg_http_time / 1024 / 1024  # MB/s
    print(f"平均传输带宽: {bandwidth:.1f} MB/s")

    print("\n" + "="*50)
    print("优化建议")
    print("="*50)
    http_ratio = np.mean(http_times) / np.mean(total_times) * 100
    print(f"HTTP请求占比: {http_ratio:.1f}%")

    if http_ratio > 90:
        print("\n瓶颈在 HTTP 请求（模拟器截屏+网络传输）")
        print("建议:")
        print("  1. 使用 MuMu 共享内存截图 (nemu 接口)")
        print("  2. 降低模拟器分辨率")
        print("  3. 尝试 minicap")
    else:
        print("\n解码占用较多时间，可考虑优化解码算法")


if __name__ == "__main__":
    test_screenshot_timing()
