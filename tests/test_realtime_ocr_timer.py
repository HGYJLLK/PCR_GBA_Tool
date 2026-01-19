"""
实时倒计时识别测试
使用异步双缓冲：截图和 OCR 并行执行

用法:
    python tests/test_realtime_ocr_timer.py
    python tests/test_realtime_ocr_timer.py --droidcast  # 使用 DroidCast（较慢）
"""

import sys
import time
import os
import re
import argparse
from collections import deque
from threading import Thread, Lock
from queue import Queue, Empty

sys.path.insert(0, "./")


# ANSI 转义码
CLEAR_LINE = "\033[K"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def parse_time_string(s):
    """解析时间字符串，返回总秒数"""
    if not s:
        return None

    # M:SS 格式 (如 "1:30")
    match = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if match:
        minutes, seconds = int(match.group(1)), int(match.group(2))
        return minutes * 60 + seconds

    # 纯数字 (当作秒数，如 "31")
    match = re.match(r"^(\d{1,3})$", s)
    if match:
        seconds = int(match.group(1))
        if seconds <= 90:
            return seconds

    return None


class AsyncScreenshotNemuIpc:
    """异步截图器 - 使用 NemuIpc（极速）"""

    def __init__(self, nemu_ipc, crop_area=None):
        self.nemu_ipc = nemu_ipc
        self.crop_area = crop_area  # (x1, y1, x2, y2)
        self.latest_image = None
        self.latest_cropped = None
        self.lock = Lock()
        self.running = False
        self.thread = None
        self.screenshot_time = 0

    def start(self):
        self.running = True
        self.thread = Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _capture_loop(self):
        while self.running:
            t0 = time.time()
            try:
                image = self.nemu_ipc.screenshot()
                # 提前裁剪，减少传输和处理的数据量
                if self.crop_area:
                    x1, y1, x2, y2 = self.crop_area
                    cropped = image[y1:y2, x1:x2].copy()
                else:
                    cropped = image
                with self.lock:
                    self.latest_image = image
                    self.latest_cropped = cropped
                    self.screenshot_time = time.time() - t0
            except Exception as e:
                pass

    def get_image(self):
        """获取裁剪后的图像"""
        with self.lock:
            return self.latest_cropped, self.screenshot_time

    def get_full_image(self):
        """获取完整截图（用于保存错误截图）"""
        with self.lock:
            return self.latest_image


class AsyncScreenshotDroidCast:
    """异步截图器 - 使用 DroidCast（兼容模式）"""

    def __init__(self, device, crop_area=None):
        self.device = device
        self.crop_area = crop_area
        self.latest_image = None
        self.latest_cropped = None
        self.lock = Lock()
        self.running = False
        self.thread = None
        self.screenshot_time = 0

    def start(self):
        self.running = True
        self.thread = Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _capture_loop(self):
        while self.running:
            t0 = time.time()
            try:
                image = self.device.screenshot_droidcast_raw()
                if self.crop_area:
                    x1, y1, x2, y2 = self.crop_area
                    cropped = image[y1:y2, x1:x2].copy()
                else:
                    cropped = image
                with self.lock:
                    self.latest_image = image
                    self.latest_cropped = cropped
                    self.screenshot_time = time.time() - t0
            except Exception as e:
                pass

    def get_image(self):
        with self.lock:
            return self.latest_cropped, self.screenshot_time

    def get_full_image(self):
        with self.lock:
            return self.latest_image


class AsyncOCR:
    """异步 OCR - 在后台线程持续识别（接收已裁剪的小图）"""

    def __init__(self, ocr_engine, alphabet=None):
        self.ocr_engine = ocr_engine  # CnOcrEngine 实例
        self.alphabet = alphabet
        self.input_queue = Queue(maxsize=2)
        self.result = None
        self.lock = Lock()
        self.running = False
        self.thread = None
        self.ocr_time = 0

    def start(self):
        self.running = True
        self.thread = Thread(target=self._ocr_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _ocr_loop(self):
        while self.running:
            try:
                cropped_image = self.input_queue.get(timeout=0.1)
                t0 = time.time()
                # 直接对裁剪后的小图进行 OCR
                results = self.ocr_engine.atomic_ocr_for_single_lines(
                    [cropped_image], self.alphabet
                )
                text = "".join(results[0]) if results and results[0] else ""
                with self.lock:
                    self.result = text
                    self.ocr_time = time.time() - t0
            except Empty:
                pass
            except Exception as e:
                pass

    def submit(self, cropped_image):
        try:
            if self.input_queue.full():
                try:
                    self.input_queue.get_nowait()
                except Empty:
                    pass
            self.input_queue.put_nowait(cropped_image)
        except:
            pass

    def get_result(self):
        with self.lock:
            return self.result, self.ocr_time


def main():
    parser = argparse.ArgumentParser(description="实时倒计时识别测试")
    parser.add_argument("--droidcast", action="store_true", help="使用 DroidCast 截图（较慢）")
    args = parser.parse_args()

    # 倒计时区域 (x1, y1, x2, y2)
    timer_area = (1078, 24, 1120, 48)
    alphabet = "0123456789:"

    # 选择截图方式
    if args.droidcast:
        print("使用 DroidCast 截图模式...")
        from module.config.config import PriconneConfig
        from module.device.device import Device

        config = PriconneConfig("cwj", "Pcr")
        device = Device(config)
        device.disable_stuck_detection()

        print("初始化 DroidCast 服务...")
        device.droidcast_init()
        time.sleep(1)
        print("DroidCast 服务就绪")

        async_screenshot = AsyncScreenshotDroidCast(device, crop_area=timer_area)
        screenshot_mode = "DroidCast"
    else:
        print("使用 NemuIpc 截图模式（极速）...")
        from module.device.method.nemu_ipc import NemuIpcImpl

        nemu_folder = r"C:\Program Files\Netease\MuMu Player 12"
        nemu = NemuIpcImpl(nemu_folder, instance_id=0)
        nemu.connect()
        print(f"NemuIpc 已连接，分辨率: {nemu.width}x{nemu.height}")

        async_screenshot = AsyncScreenshotNemuIpc(nemu, crop_area=timer_area)
        screenshot_mode = "NemuIpc"

    # 获取 OCR 引擎
    from module.ocr.models import OCR_MODEL
    ocr_engine = OCR_MODEL.pcr

    # 预热 OCR 模型
    print("预热 OCR 模型...")
    ocr_engine.init()

    # 创建异步 OCR
    async_ocr = AsyncOCR(ocr_engine, alphabet=alphabet)

    print(f"\n{'='*70}")
    print(f"PCR 倒计时实时同步 (异步双缓冲 + {screenshot_mode})")
    print(f"{'='*70}")
    print(f"按 Ctrl+C 停止\n")

    # 统计
    prev_seconds = None
    count = 0
    error_count = 0
    loop_count = 0
    start_time = time.time()

    # 性能统计
    screenshot_times = deque(maxlen=50)
    ocr_times = deque(maxlen=50)
    loop_times = deque(maxlen=50)
    current_result = "等待..."

    # 状态栏
    status_line = ""

    def update_status():
        nonlocal status_line
        elapsed = int(time.time() - start_time)
        avg_screenshot = sum(screenshot_times) / len(screenshot_times) * 1000 if screenshot_times else 0
        avg_ocr = sum(ocr_times) / len(ocr_times) * 1000 if ocr_times else 0
        # 有效 FPS = 取决于较慢的那个（瓶颈）
        bottleneck = max(avg_screenshot, avg_ocr)
        effective_fps = 1000 / bottleneck if bottleneck > 0 else 0

        status_line = (
            f"\r{CLEAR_LINE}"
            f"[{elapsed:>4}s] {current_result:>5} | "
            f"截图:{avg_screenshot:>3.0f}ms | OCR:{avg_ocr:>2.0f}ms | "
            f"FPS:{effective_fps:>5.1f} | 变化:{count:>3} | 错误:{error_count}"
        )
        sys.stdout.write(status_line)
        sys.stdout.flush()

    def print_log(msg):
        sys.stdout.write(f"\r{CLEAR_LINE}{msg}\n")
        sys.stdout.write(status_line)
        sys.stdout.flush()

    # 隐藏光标
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    # 启动异步线程
    async_screenshot.start()
    async_ocr.start()

    # 等待第一张截图
    while async_screenshot.get_image()[0] is None:
        time.sleep(0.01)

    last_image = None

    try:
        while True:
            loop_start = time.time()

            # 获取最新截图
            image, screenshot_time = async_screenshot.get_image()

            if image is not None and image is not last_image:
                last_image = image
                screenshot_times.append(screenshot_time)

                # 提交给 OCR 处理
                async_ocr.submit(image)

            # 获取 OCR 结果
            text_result, ocr_time = async_ocr.get_result()

            if ocr_time > 0:
                ocr_times.append(ocr_time)

            loop_count += 1

            if text_result:
                # 解析时间字符串
                total_seconds = parse_time_string(text_result)

                if total_seconds is not None and 0 <= total_seconds <= 5400:
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    current_result = f"{minutes}:{seconds:02d}"

                    if prev_seconds != total_seconds:
                        if prev_seconds is None or (prev_seconds - total_seconds) in [1, 2]:
                            print_log(f"[{count:04d}] {current_result} ({total_seconds:3d}s)")
                            count += 1
                        elif (prev_seconds - total_seconds) > 2:
                            print_log(f"[{count:04d}] {current_result} ({total_seconds:3d}s) [切换]")
                            count += 1
                        prev_seconds = total_seconds
                elif total_seconds is not None:
                    error_count += 1

            # 记录循环时间
            loop_times.append(time.time() - loop_start)

            # 更新状态栏
            update_status()

            # 短暂休眠，避免主线程空转
            time.sleep(0.005)

    except KeyboardInterrupt:
        pass
    finally:
        # 停止异步线程
        async_screenshot.stop()
        async_ocr.stop()

        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.write("\n\n")
        sys.stdout.flush()

        elapsed = time.time() - start_time
        print("=" * 70)
        print(f"统计 ({screenshot_mode} 模式)")
        print("=" * 70)
        print(f"运行时间: {elapsed:.1f}s")
        print(f"总循环次数: {loop_count}")
        print(f"时间变化次数: {count}")
        print(f"错误次数: {error_count}")

        if screenshot_times and ocr_times:
            avg_screenshot = sum(screenshot_times) / len(screenshot_times) * 1000
            avg_ocr = sum(ocr_times) / len(ocr_times) * 1000
            bottleneck = max(avg_screenshot, avg_ocr)
            effective_fps = 1000 / bottleneck if bottleneck > 0 else 0
            print(f"平均耗时: 截图 {avg_screenshot:.1f}ms | OCR {avg_ocr:.0f}ms")
            print(f"瓶颈: {'截图' if avg_screenshot >= avg_ocr else 'OCR'} ({bottleneck:.1f}ms)")
            print(f"有效 FPS: {effective_fps:.1f} (理论最大: {1000/bottleneck:.1f})")


if __name__ == "__main__":
    main()
