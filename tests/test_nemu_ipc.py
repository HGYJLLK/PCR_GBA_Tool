"""
测试 MuMu12 nemu IPC 截图速度
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def test_nemu_ipc():
    """测试 nemu IPC 截图"""
    from module.device.method.nemu_ipc import NemuIpcImpl

    # MuMu12 安装路径和实例 ID
    nemu_folder = r"C:\Program Files\Netease\MuMu Player 12"
    instance_id = 0  # 第一个模拟器实例

    print(f"MuMu 路径: {nemu_folder}")
    print(f"实例 ID: {instance_id}")

    # 直接创建实例（不使用缓存）
    print("初始化 NemuIpc...")
    nemu = NemuIpcImpl(nemu_folder, instance_id)
    nemu.connect()
    print(f"分辨率: {nemu.width}x{nemu.height}")

    # 预热
    print("预热中...")
    for _ in range(5):
        nemu.screenshot()

    # 测试截图速度
    N = 100
    print(f"\n测试 {N} 次截图...")

    times = []
    for i in range(N):
        t0 = time.perf_counter()
        image = nemu.screenshot()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{N} 完成")

    print("\n" + "=" * 50)
    print("NemuIpc 截图性能测试结果")
    print("=" * 50)
    print(f"图像尺寸: {image.shape}")
    print(f"平均耗时: {np.mean(times):.1f}ms")
    print(f"最小耗时: {np.min(times):.1f}ms")
    print(f"最大耗时: {np.max(times):.1f}ms")
    print(f"标准差: {np.std(times):.1f}ms")
    print(f"理论 FPS: {1000 / np.mean(times):.1f}")

    # 对比 DroidCast
    print("\n" + "=" * 50)
    print("与 DroidCast_raw 对比")
    print("=" * 50)
    print("NemuIpc: 通过共享内存直接读取显存")
    print("DroidCast_raw: 通过 HTTP 传输 RGB565 数据")
    print(f"\n预期提升: 如果 DroidCast 约 80ms，NemuIpc 约 {np.mean(times):.0f}ms")
    print(f"速度提升: {80 / np.mean(times):.1f}x")


def compare_with_droidcast():
    """对比 NemuIpc 和 DroidCast_raw 速度"""
    from module.device.method.nemu_ipc import get_nemu_ipc, NemuIpcImpl
    from module.device.device import Device
    from module.config.config import PriconneConfig

    serial = "127.0.0.1:16384"

    # 初始化 DroidCast
    print("初始化 DroidCast...")
    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)
    device.droidcast_init()
    time.sleep(1)

    # 初始化 NemuIpc
    print("初始化 NemuIpc...")
    nemu = get_nemu_ipc(serial=serial)

    N = 50

    # 测试 DroidCast
    print(f"\n测试 DroidCast_raw {N} 次...")
    droidcast_times = []
    for i in range(N):
        t0 = time.perf_counter()
        device.screenshot_droidcast_raw()
        droidcast_times.append((time.perf_counter() - t0) * 1000)
    print(f"  DroidCast_raw 平均: {np.mean(droidcast_times):.1f}ms")

    # 测试 NemuIpc
    print(f"\n测试 NemuIpc {N} 次...")
    nemu_times = []
    for i in range(N):
        t0 = time.perf_counter()
        nemu.screenshot()
        nemu_times.append((time.perf_counter() - t0) * 1000)
    print(f"  NemuIpc 平均: {np.mean(nemu_times):.1f}ms")

    print("\n" + "=" * 50)
    print("对比结果")
    print("=" * 50)
    print(f"DroidCast_raw: {np.mean(droidcast_times):.1f}ms ({1000/np.mean(droidcast_times):.1f} FPS)")
    print(f"NemuIpc:       {np.mean(nemu_times):.1f}ms ({1000/np.mean(nemu_times):.1f} FPS)")
    print(f"速度提升: {np.mean(droidcast_times) / np.mean(nemu_times):.2f}x")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", action="store_true", help="与 DroidCast 对比")
    args = parser.parse_args()

    if args.compare:
        compare_with_droidcast()
    else:
        test_nemu_ipc()
