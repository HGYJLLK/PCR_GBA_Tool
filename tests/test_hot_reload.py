#!/usr/bin/env python3
"""
公主连结配置热更新测试
"""

import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "."))
from module.config.config import PriconneConfig


def wait_until_future_with_reload_check(config, future):
    """
    等待，同时检查配置是否需要重新加载

    Args:
        config: PriconneConfig实例
        future: 目标时间

    Returns:
        bool: 如果等待完成返回True，如果配置发生变化返回False
    """
    future = future + timedelta(seconds=1)
    config.start_watching()

    while True:
        if datetime.now() > future:
            return True

        # 检查停止事件
        if config.stop_event is not None and config.stop_event.is_set():
            print("收到停止信号")
            return True

        time.sleep(5)

        if config.should_reload():
            print("检测到配置文件变化，需要重新加载")
            return False


def demo_hot_reload():
    """
    热更新功能
    """
    print("=== 公主连结配置热更新 ===")

    # 初始化配置
    try:
        config = PriconneConfig("pcr")
        print(f"已加载配置: {config.config_name}")
    except Exception as e:
        print(f"初始化配置失败: {e}")
        print("检查config/pcr.json文件是否存在")
        return

    # 配置监控
    print("开始监控配置文件变化...")
    print("请修改config/pcr.json文件来测试热更新功能")
    print("按Ctrl+C退出程序")

    try:
        while True:
            # 模拟等待10秒
            future_time = datetime.now() + timedelta(seconds=10)
            print(f"等待10秒至 {future_time.strftime('%H:%M:%S')}，同时监控配置文件...")

            # 等待并检查配置变化
            wait_result = wait_until_future_with_reload_check(config, future_time)

            if not wait_result:
                # 配置发生了变化，重新加载
                print("重新加载配置...")
                config.load()
                print("配置重新加载完成")
            else:
                print("等待完成，无配置变化")

    except KeyboardInterrupt:
        print("\n程序已退出")


def demo_config_operations():
    """
    配置操作
    """
    print("=== 配置操作 ===")

    try:
        config = PriconneConfig("pcr")

        # 配置读取
        print("当前配置数据:")
        for key, value in config.data.items():
            print(f"  {key}: {value}")

        # 配置监控
        print(f"\n开始监控配置 {config.config_name}")
        config.start_watching()

        original_mtime = config.get_mtime()
        print(f"配置文件当前修改时间: {original_mtime}")

        # 检查是否需要重新加载
        should_reload = config.should_reload()
        print(f"是否需要重新加载: {should_reload}")

    except Exception as e:
        print(f"配置操作失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ops":
        demo_config_operations()
    else:
        demo_hot_reload()
