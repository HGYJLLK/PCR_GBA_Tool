"""
战斗监控模块
负责：进入战斗后开启"全set（立即发动）"、监控OCR倒计时、战斗结束后点击伤害报告
"""

import sys
import re
import time
from threading import Thread, Lock
from queue import Queue, Empty

from module.logger import logger
from module.train.assets import (
    MENU,
    REPORT,
    立即发动OFF,
    立即发动ON,
)

# ANSI 转义码
CLEAR_LINE = "\033[K"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
# 异步截图器
# ──────────────────────────────────────────────

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
                if self.crop_area:
                    x1, y1, x2, y2 = self.crop_area
                    cropped = image[y1:y2, x1:x2].copy()
                else:
                    cropped = image
                with self.lock:
                    self.latest_image = image
                    self.latest_cropped = cropped
                    self.screenshot_time = time.time() - t0
            except Exception:
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
            except Exception:
                pass

    def get_image(self):
        with self.lock:
            return self.latest_cropped, self.screenshot_time

    def get_full_image(self):
        with self.lock:
            return self.latest_image


# ──────────────────────────────────────────────
# 异步 OCR
# ──────────────────────────────────────────────

class AsyncOCR:
    """异步 OCR - 在后台线程持续识别（接收已裁剪的小图）"""

    def __init__(self, ocr_engine, alphabet=None):
        self.ocr_engine = ocr_engine
        self.alphabet = alphabet
        self.input_queue = Queue(maxsize=2)
        self.result = None
        self.ocr_image = None
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
                results = self.ocr_engine.atomic_ocr_for_single_lines(
                    [cropped_image], self.alphabet
                )
                text = "".join(results[0]) if results and results[0] else ""
                with self.lock:
                    self.result = text
                    self.ocr_image = cropped_image
                    self.ocr_time = time.time() - t0
            except Empty:
                pass
            except Exception:
                pass

    def submit(self, cropped_image):
        try:
            if self.input_queue.full():
                try:
                    self.input_queue.get_nowait()
                except Empty:
                    pass
            self.input_queue.put_nowait(cropped_image)
        except Exception:
            pass

    def get_result(self):
        with self.lock:
            return self.result, self.ocr_image, self.ocr_time


# ──────────────────────────────────────────────
# 战斗监控主类 (Mixin)
# ──────────────────────────────────────────────

class BattleMonitor:
    """
    战斗监控 Mixin。
    依赖宿主类提供：self.device、self.appear()、self.match_template_color()
    """

    # 倒计时 OCR 裁剪区域
    TIMER_AREA = (1078, 24, 1120, 48)

    def enable_full_set(self):
        """
        进入战斗后，如果"立即发动"处于 OFF 状态则点击开启（全set模式）。
        最多等待 5 秒检测。
        """
        logger.hr("Enable Full Set (立即发动)", level=1)

        timeout = time.time() + 5.0
        while time.time() < timeout:
            self.device.screenshot()

            # 如果已经是 ON，无需操作
            if self.appear(立即发动ON, offset=(10, 10)):
                logger.info("✓ 立即发动已是 ON，无需操作")
                return True

            # 检测到 OFF，点击开启
            if self.appear(立即发动OFF, offset=(10, 10)):
                logger.info("检测到 立即发动 OFF，点击开启...")
                self.device.click(立即发动OFF)
                time.sleep(0.5)
                # 验证是否成功切换为 ON
                self.device.screenshot()
                if self.appear(立即发动ON, offset=(10, 10)):
                    logger.info("✓ 立即发动已切换为 ON")
                    return True
                else:
                    logger.warning("  切换后未检测到 ON，将重试...")
                continue

            time.sleep(0.3)

        logger.warning("⚠️  超时：未能检测到 立即发动 按钮，跳过全set开启")
        return False

    def _save_debug_image(self, image, text_result, reason):
        """保存 OCR 错误截图"""
        import cv2
        import os
        import numpy as np

        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_text = str(text_result).replace(":", "_")
            filename = f"{timestamp}_{reason}_{safe_text}.png"
            save_dir = "./logs/ocr_errors"
            os.makedirs(save_dir, exist_ok=True)
            filepath = os.path.join(save_dir, filename)
            if isinstance(image, np.ndarray):
                cv2.imwrite(filepath, image)
                logger.info(f"  [DEBUG] 错误截图已保存: {filepath}")
            else:
                logger.warning("  [DEBUG] 无法保存截图: 格式不支持")
        except Exception as e:
            logger.error(f"  保存调试截图失败: {e}")

    def monitor_until_end(self, use_droidcast=False, timeline=None):
        """
        监控战斗倒计时，战斗结束后点击伤害报告按钮。

        Args:
            use_droidcast: 是否使用 DroidCast 截图（默认 NemuIpc）
            timeline: Timeline 对象，定义时间轴动作（可选）

        Returns:
            True 表示正常完成（点击了 REPORT），False 表示被中断
        """
        logger.hr("Monitor battle timer", level=1)

        # ── 初始化 OCR 引擎 ──
        from module.ocr.models import OCR_MODEL
        ocr_engine = OCR_MODEL.pcr
        ocr_engine.init()

        alphabet = "0123456789:"
        async_ocr = AsyncOCR(ocr_engine, alphabet=alphabet)

        # ── 选择截图后端 ──
        if use_droidcast:
            logger.info("使用 DroidCast 截图模式...")
            self.device.droidcast_init()
            time.sleep(1)
            async_screenshot = AsyncScreenshotDroidCast(
                self.device, crop_area=self.TIMER_AREA
            )
            screenshot_mode = "DroidCast"
        else:
            logger.info("使用 NemuIpc 截图模式（极速）...")
            from module.device.method.nemu_ipc import get_nemu_ipc
            nemu = get_nemu_ipc(serial=self.device.serial)
            async_screenshot = AsyncScreenshotNemuIpc(nemu, crop_area=self.TIMER_AREA)
            screenshot_mode = "NemuIpc"

        logger.info(f"开始监控倒计时 (异步双缓冲 + {screenshot_mode})")
        logger.info(f"目标: 检测到倒计时≤0:01时停止")
        logger.info("=" * 70)

        # ── 统计 & 状态 ──
        last_valid_timer_time = None
        last_valid_detection_time = time.time()
        detection_count = 0
        self.current_char_state = set()
        timer_threshold_reached = False
        should_check_button = False
        self.time_travel_count = 0

        sys.stdout.write(HIDE_CURSOR)
        sys.stdout.flush()

        start_time = time.time()
        last_image = None

        # ── 初始化时间轴 ──
        if timeline:
            timeline.reset()
            logger.info(f"时间轴已加载: {timeline.name} ({len(timeline.actions)} 个动作)")
            for action in sorted(timeline.actions, key=lambda x: x.time_seconds, reverse=True):
                logger.info(f"  - {action.time_str}: {action.description}")
        else:
            logger.info("未使用时间轴，仅监控倒计时")

        # ── 启动异步线程 ──
        async_screenshot.start()
        async_ocr.start()

        # 等待第一张截图就绪
        while async_screenshot.get_image()[0] is None:
            time.sleep(0.01)

        result = False
        try:
            while True:
                loop_start = time.time()

                # ── 获取截图并提交 OCR ──
                image, screenshot_time = async_screenshot.get_image()
                if image is not None and image is not last_image:
                    last_image = image
                    async_ocr.submit(image)

                # ── 读取 OCR 结果 ──
                text_result, ocr_image, ocr_time = async_ocr.get_result()

                current_time = time.time()
                elapsed = current_time - start_time

                # ── 解析倒计时 ──
                if not timer_threshold_reached and text_result:
                    total_seconds = parse_time_string(text_result.strip())

                    if total_seconds is not None and 0 <= total_seconds <= 90:
                        is_valid = True
                        if last_valid_timer_time is not None:
                            time_since_last = current_time - last_valid_detection_time
                            expected_time = last_valid_timer_time - time_since_last
                            tolerance = 2.0

                            if total_seconds > last_valid_timer_time:
                                self.time_travel_count += 1
                                if self.time_travel_count > 3:
                                    logger.warning(
                                        f"  [OCR修正] 连续倒流，强制接受: {last_valid_timer_time} -> {total_seconds}"
                                    )
                                    is_valid = True
                                    self.time_travel_count = 0
                                else:
                                    logger.warning(
                                        f"  [OCR滤除] 时间倒流: {last_valid_timer_time} -> {total_seconds} (连续{self.time_travel_count}次)"
                                    )
                                    is_valid = False
                                    self._save_debug_image(ocr_image, text_result, "time_travel")

                            elif total_seconds < (expected_time - tolerance):
                                logger.warning(
                                    f"  [OCR滤除] 异常跳变: 上次{last_valid_timer_time}s, 逝去{time_since_last:.1f}s, 预期~{expected_time:.1f}s, 实际{total_seconds}s"
                                )
                                is_valid = False
                                self._save_debug_image(ocr_image, text_result, "huge_drop")
                                self.time_travel_count = 0
                            else:
                                self.time_travel_count = 0

                        if is_valid:
                            last_valid_timer_time = total_seconds
                            last_valid_detection_time = current_time
                            detection_count += 1

                            # 执行时间轴动作
                            if timeline:
                                action = timeline.get_next_action(last_valid_timer_time)
                                if action and not action.executed:
                                    self._execute_timeline_action(action)
                                    action.executed = True

                        minutes = total_seconds // 60
                        seconds = total_seconds % 60
                        time_str = f"{minutes}:{seconds:02d}"
                        val_str = "有效" if is_valid else "无效"
                        status = f"\r{CLEAR_LINE}[{elapsed:>5.1f}s] 倒计时: {time_str} ({val_str}) | 检测: {detection_count}"
                        sys.stdout.write(status)
                        sys.stdout.flush()

                        if is_valid and last_valid_timer_time <= 1:
                            timer_threshold_reached = True
                            should_check_button = True
                            logger.info(f"\n[触发] 倒计时 {time_str} ≤ 1s，等待结算界面...")
                    else:
                        detection_count += 1
                        status = f"\r{CLEAR_LINE}[{elapsed:>5.1f}s] OCR无效: '{text_result}' | 检测: {detection_count}"
                        sys.stdout.write(status)
                        sys.stdout.flush()

                # ── 检查计时器消失 ──
                timer_missing_duration = current_time - last_valid_detection_time
                if timer_missing_duration > 3.0:
                    if timer_missing_duration > 5.0 and not timer_threshold_reached:
                        should_check_button = True
                    if timer_threshold_reached:
                        should_check_button = True
                    if int(timer_missing_duration) % 2 == 0 and int(timer_missing_duration) != int(timer_missing_duration - 0.1):
                        logger.info(f"\n 倒计时消失 {timer_missing_duration:.1f}s，检测结算按钮...")

                # ── 检测结算按钮 ──
                if should_check_button:
                    self.device.screenshot()
                    if self.match_template_color(REPORT, interval=2):
                        debug_path = "./logs/debug_report_detected.png"
                        self.device.image_save(debug_path)
                        logger.info(f"\n 检测到 REPORT 按钮！(运行: {elapsed:.1f}s)")
                        self.device.click(REPORT)
                        time.sleep(1.0)
                        logger.info("  已点击 REPORT，战斗结束")
                        result = True
                        break

                # ── 控制循环频率 ──
                loop_time = time.time() - loop_start
                if loop_time < 0.1:
                    time.sleep(0.1 - loop_time)

        except KeyboardInterrupt:
            logger.info("\n 用户停止")
        finally:
            async_screenshot.stop()
            async_ocr.stop()
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.write("\n")
            sys.stdout.flush()

            elapsed = time.time() - start_time
            logger.info("=" * 70)
            logger.info(f"监控统计 ({screenshot_mode} 模式)")
            logger.info("=" * 70)
            logger.info(f"  运行时间: {elapsed:.1f}s")
            logger.info(f"  总检测次数: {detection_count}")
            if last_valid_timer_time is not None:
                m = last_valid_timer_time // 60
                s = last_valid_timer_time % 60
                logger.info(f"  最后识别倒计时: {m}:{s:02d}")
            else:
                logger.info("  最后识别倒计时: 无")
            logger.info("=" * 70)

        return result
