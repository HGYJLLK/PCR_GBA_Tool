#!/usr/bin/env python3
"""
PCR截图性能基准测试
"""

import sys
import os
import time
import numpy as np
from rich.table import Table
from rich.text import Text
from rich.console import Console

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "."))

from module.config.config import PriconneConfig
from module.device.device import Device
from module.logger import logger

console = Console()


def float2str(n, decimal=3):
    """格式化浮点数为字符串"""
    if not isinstance(n, (float, int)):
        return str(n)
    else:
        return f"{n:.{decimal}f}s"


def evaluate_screenshot(cost):
    """
    评估截图速度
    """
    if not isinstance(cost, (float, int)):
        return Text(str(cost), style="bold bright_red")

    if cost < 0.025:
        return Text("Insane Fast", style="bold bright_green")
    if cost < 0.100:
        return Text("Ultra Fast", style="bold bright_green")
    if cost < 0.200:
        return Text("Very Fast", style="bright_green")
    if cost < 0.300:
        return Text("Fast", style="green")
    if cost < 0.500:
        return Text("Medium", style="yellow")
    if cost < 0.750:
        return Text("Slow", style="red")
    if cost < 1.000:
        return Text("Very Slow", style="bright_red")
    return Text("Ultra Slow", style="bold bright_red")


class ScreenshotBenchmark:
    """截图性能基准测试类"""

    TEST_TOTAL = 15  # 总测试次数
    TEST_BEST = 12  # 取最好的12次计算平均值

    def __init__(self, config):
        self.config = config
        self.device = Device(config)

    def benchmark_test(self, func, *args, **kwargs):
        """
        测试函数性能

        Args:
            func: 要测试的函数
            *args: 传递给func的参数
            **kwargs: 传递给func的关键字参数

        Returns:
            float: 平均耗时（秒）
        """
        logger.hr(f"Testing: {func.__name__}", level=2)
        record = []

        for n in range(1, self.TEST_TOTAL + 1):
            start = time.time()

            try:
                result = func(*args, **kwargs)
                # 验证截图有效
                if result is None or (hasattr(result, "shape") and result.size == 0):
                    logger.warning(f"Invalid screenshot returned")
                    return "Failed"
            except Exception as e:
                logger.error(f"Test failed: {e}")
                return "Failed"

            cost = time.time() - start
            logger.attr(
                f'{str(n).rjust(2, "0")}/{self.TEST_TOTAL}', f"{float2str(cost)}"
            )
            record.append(cost)

        # 排序后取最好的TEST_BEST个结果的平均值
        average = float(np.mean(np.sort(record)[: self.TEST_BEST]))
        logger.info(
            f"Average: {float2str(average)} (best {self.TEST_BEST} out of {self.TEST_TOTAL} tests)"
        )
        return average

    def show_results(self, results):
        """
        显示测试结果表格

        Args:
            results: [(方法名, 耗时), ...]
        """
        logger.hr("Benchmark Results", level=1)

        table = Table(show_lines=True)
        table.add_column(
            "Screenshot", header_style="bright_cyan", style="cyan", no_wrap=True
        )
        table.add_column("Time", style="magenta")
        table.add_column("Speed", style="green")

        # 添加数据行
        for method, cost in results:
            table.add_row(
                method,
                float2str(cost),
                evaluate_screenshot(cost),
            )

        # 居中对齐
        console.print(table, justify="center")

        # 推荐方法
        valid_results = [(m, c) for m, c in results if isinstance(c, (int, float))]
        if valid_results:
            fastest = min(valid_results, key=lambda x: x[1])
            logger.info(
                f"Recommend screenshot method: {fastest[0]} ({float2str(fastest[1])})"
            )
            return fastest[0]
        return None

    def run(self):
        """运行基准测试"""
        logger.hr("PCR Screenshot Benchmark", level=1)

        # 测试方法列表
        screenshot_methods = [
            ("ADB", self.device.screenshot_adb),
            ("DroidCast_raw", self.device.screenshot_droidcast_raw),
        ]

        results = []

        # 初始化DroidCast服务
        logger.hr("Initializing DroidCast", level=2)
        try:
            self.device.droidcast_init()
            logger.info("DroidCast initialized successfully")
        except Exception as e:
            logger.error(f"DroidCast initialization failed: {e}")
            # 从测试列表中移除DroidCast
            screenshot_methods = [
                m for m in screenshot_methods if "DroidCast" not in m[0]
            ]

        # 执行测试
        for method_name, method_func in screenshot_methods:
            logger.hr(f"Testing {method_name}", level=1)
            cost = self.benchmark_test(method_func)
            results.append((method_name, cost))

        # 显示结果
        fastest = self.show_results(results)

        return fastest


def run_quick_benchmark():
    """快速基准测试"""
    logger.hr("PCR Quick Screenshot Benchmark", level=1)

    config = PriconneConfig(config_name="maple")
    device = Device(config)

    # 快速测试配置
    TEST_TOTAL = 5
    TEST_BEST = 3

    results = []

    # 初始化DroidCast
    logger.info("Initializing DroidCast...")
    try:
        device.droidcast_init()
    except Exception as e:
        logger.error(f"DroidCast init failed: {e}")

    # 测试ADB
    logger.hr("Testing ADB", level=2)
    adb_times = []
    for i in range(TEST_TOTAL):
        start = time.time()
        try:
            _ = device.screenshot_adb()
            cost = time.time() - start
            adb_times.append(cost)
            logger.info(f"Test {i+1}: {float2str(cost)}")
        except Exception as e:
            logger.error(f"ADB failed: {e}")
            adb_times.append(999)

    adb_avg = np.mean(np.sort(adb_times)[:TEST_BEST])
    results.append(("ADB", adb_avg))

    # 测试DroidCast_raw
    logger.hr("Testing DroidCast_raw", level=2)
    dc_times = []
    for i in range(TEST_TOTAL):
        start = time.time()
        try:
            _ = device.screenshot_droidcast_raw()
            cost = time.time() - start
            dc_times.append(cost)
            logger.info(f"Test {i+1}: {float2str(cost)}")
        except Exception as e:
            logger.error(f"DroidCast_raw failed: {e}")
            dc_times.append(999)

    dc_avg = np.mean(np.sort(dc_times)[:TEST_BEST])
    results.append(("DroidCast_raw", dc_avg))

    logger.hr("Quick Benchmark Results", level=1)

    table = Table(show_lines=True)
    table.add_column(
        "Screenshot", header_style="bright_cyan", style="cyan", no_wrap=True
    )
    table.add_column("Time", style="magenta")
    table.add_column("Speed", style="green")

    for method, cost in results:
        table.add_row(
            method,
            float2str(cost),
            evaluate_screenshot(cost),
        )

    console.print(table, justify="center")

    # 性能提升计算
    if len(results) == 2 and all(isinstance(c, (int, float)) for _, c in results):
        improvement = ((results[0][1] - results[1][1]) / results[0][1]) * 100
        if improvement > 0:
            logger.info(f"DroidCast_raw is {improvement:.1f}% faster than ADB")
        else:
            logger.info(f"ADB is {-improvement:.1f}% faster than DroidCast_raw")


if __name__ == "__main__":
    try:
        # 选择测试模式
        import sys

        if len(sys.argv) > 1 and sys.argv[1] == "quick":
            # 快速测试模式
            run_quick_benchmark()
        else:
            # 完整测试模式
            config = PriconneConfig()
            benchmark = ScreenshotBenchmark(config)
            benchmark.run()

    except KeyboardInterrupt:
        logger.info("Benchmark interrupted by user")
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
