"""
监控模块
"""

import sys
import time

from module.device.async_screenshot import create_async_screenshot
from module.logger import logger
from module.ocr.async_ocr import AsyncOCR
from module.ocr.models import OCR_MODEL
from module.ocr.ocr import Duration
from module.train.assets import REPORT, 立即发动OFF, 立即发动ON

# ANSI 转义码（倒计时行内原地刷新）
_CLEAR_LINE = "\033[K"
_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"

# 倒计时 OCR 裁剪区域
_TIMER_CROP = (1078, 24, 1120, 48)
_TIMER_ALPHABET = "0123456789:"


class BattleMonitor:
    """
    战斗监控类
    """

    # ─── 全 set 开关 ──────────────────────────────────────────────────────

    def enable_full_set(self, timeout=5.0):
        logger.hr("Enable Full Set (立即发动)", level=1)
        deadline = time.time() + timeout

        while time.time() < deadline:
            self.device.screenshot()

            if self.appear(立即发动ON, offset=(10, 10)):
                logger.info(" 立即发动已是 ON，无需操作")
                return True

            if self.appear(立即发动OFF, offset=(10, 10)):
                logger.info("检测到 立即发动 OFF，点击开启...")
                self.device.click(立即发动OFF)
                time.sleep(0.5)
                self.device.screenshot()
                if self.appear(立即发动ON, offset=(10, 10)):
                    logger.info(" 立即发动已切换为 ON")
                    return True
                logger.warning("  切换后未检测到 ON，将重试...")
                continue

            time.sleep(0.3)

        logger.warning("  超时：未能检测到 立即发动 按钮，跳过全set开启")
        return False

    # ─── 主监控循环 ───────────────────────────────────────────────────────

    def monitor_until_end(self, use_droidcast=False, timeline=None):
        logger.hr("Monitor battle timer", level=1)

        mode = "DroidCast" if use_droidcast else "NemuIpc"
        logger.info(f"截图方式: {mode}")

        # ── 初始化 OCR 引擎 ──
        ocr_engine = OCR_MODEL.pcr
        ocr_engine.init()
        async_ocr = AsyncOCR(ocr_engine, alphabet=_TIMER_ALPHABET)

        # ── 创建异步截图实例 ──
        async_screenshot = create_async_screenshot(
            self.device, mode=mode, crop_area=_TIMER_CROP
        )

        logger.info("开始监控倒计时")
        logger.info("=" * 70)

        # ── 统计 & 状态变量 ──
        last_valid_seconds = None          # 上次有效的倒计时秒数
        last_valid_ts = time.time()        # 上次有效识别的时间戳
        detection_count = 0                # 有效识别次数
        time_travel_count = 0             # 连续时间倒流计数（用于 OCR 自纠正）
        self.current_char_state = set()   # 当前 SET 激活的角色集合
        timer_threshold_reached = False   # 是否已到达 ≤1s 阈值
        should_check_button = False       # 是否开始检测结算按钮

        # ── 初始化时间轴 ──
        if timeline:
            timeline.reset()
            logger.info(f"时间轴: {timeline.name}，共 {len(timeline.actions)} 个动作")
            for a in sorted(timeline.actions, key=lambda x: x.time_seconds, reverse=True):
                logger.info(f"  {a.time_str}: {a.description}")
        else:
            logger.info("未使用时间轴，仅监控倒计时")

        sys.stdout.write(_HIDE_CURSOR)
        sys.stdout.flush()

        start_ts = time.time()
        last_image = None
        result = False

        async_screenshot.start()
        async_ocr.start()

        # 等待第一帧
        while async_screenshot.get_image()[0] is None:
            time.sleep(0.01)

        try:
            while True:
                loop_start = time.time()

                # 异步截图期间 device.screenshot() 不会被调用，需手动 reset stuck timer
                self.device.stuck_record_clear()
                image, _ = async_screenshot.get_image()
                if image is not None and image is not last_image:
                    last_image = image
                    async_ocr.submit(image)

                text, ocr_image, _ = async_ocr.get_result()
                current_ts = time.time()
                elapsed = current_ts - start_ts

                # ── 解析倒计时 ──
                if not timer_threshold_reached and text:
                    td = Duration.parse_time(text.strip())
                    total_seconds = int(td.total_seconds()) if td else None

                    if total_seconds is not None and 0 <= total_seconds <= 90:
                        is_valid = True

                        if last_valid_seconds is not None:
                            time_since = current_ts - last_valid_ts
                            expected = last_valid_seconds - time_since

                            if total_seconds > last_valid_seconds:
                                # 时间倒流（OCR 误读）
                                time_travel_count += 1
                                if time_travel_count > 3:
                                    logger.warning(f"  [OCR修正] 连续倒流，强制接受: {last_valid_seconds} -> {total_seconds}")
                                    time_travel_count = 0
                                else:
                                    logger.warning(f"  [OCR滤除] 时间倒流: {last_valid_seconds} -> {total_seconds} ({time_travel_count}次)")
                                    is_valid = False
                                    self._save_debug_image(ocr_image, text, "time_travel")
                            elif total_seconds < (expected - 2.0):
                                # 异常跳变
                                logger.warning(f"  [OCR滤除] 异常跳变: 上次{last_valid_seconds}s 预期~{expected:.1f}s 实际{total_seconds}s")
                                is_valid = False
                                self._save_debug_image(ocr_image, text, "huge_drop")
                                time_travel_count = 0
                            else:
                                time_travel_count = 0

                        if is_valid:
                            last_valid_seconds = total_seconds
                            last_valid_ts = current_ts
                            detection_count += 1
                            # 执行时间轴动作
                            if timeline:
                                action = timeline.get_next_action(last_valid_seconds)
                                if action and not action.executed:
                                    self._execute_timeline_action(action)
                                    action.executed = True

                        m, s = divmod(total_seconds, 60)
                        val = "有效" if is_valid else "无效"
                        sys.stdout.write(f"\r{_CLEAR_LINE}[{elapsed:>5.1f}s] 倒计时: {m}:{s:02d} ({val}) | 识别: {detection_count}")
                        sys.stdout.flush()

                        if is_valid and last_valid_seconds <= 1:
                            timer_threshold_reached = True
                            should_check_button = True
                            logger.info(f"\n[触发] 倒计时 ≤ 1s，等待结算界面...")
                    else:
                        sys.stdout.write(f"\r{_CLEAR_LINE}[{elapsed:>5.1f}s] OCR无效: '{text}'")
                        sys.stdout.flush()

                # ── 计时器消失检测 ──
                missing = current_ts - last_valid_ts
                if missing > 3.0:
                    if missing > 5.0 and not timer_threshold_reached:
                        should_check_button = True
                    if timer_threshold_reached:
                        should_check_button = True

                # ── 结算按钮检测 ──
                if should_check_button:
                    self.device.stuck_record_clear()  # 重置 stuck timer 再截图
                    self.device.screenshot()
                    if self.match_template_color(REPORT, interval=2):
                        debug_path = "./logs/debug_report_detected.png"
                        self.device.image_save(debug_path)
                        logger.info(f"\n 检测到 REPORT！(运行: {elapsed:.1f}s)")
                        self.device.click(REPORT)
                        time.sleep(1.0)
                        logger.info("  已点击 REPORT，战斗结束")
                        result = True
                        break

                # ── 循环限速 ──
                cost = time.time() - loop_start
                if cost < 0.1:
                    time.sleep(0.1 - cost)

        except KeyboardInterrupt:
            logger.info("\n 用户停止")
        finally:
            async_screenshot.stop()
            async_ocr.stop()
            sys.stdout.write(_SHOW_CURSOR)
            sys.stdout.write("\n")
            sys.stdout.flush()

            elapsed = time.time() - start_ts
            logger.info("=" * 70)
            logger.info(f"  运行时间: {elapsed:.1f}s | 识别次数: {detection_count} | 后端: {mode}")
            if last_valid_seconds is not None:
                m, s = divmod(last_valid_seconds, 60)
                logger.info(f"  最后识别倒计时: {m}:{s:02d}")
            logger.info("=" * 70)

        return result

    # ─── 内部工具方法 ─────────────────────────────────────────────────────

    def _execute_timeline_action(self, action):
        """执行时间轴动作（点击角色，处理 SET 状态切换）"""
        from module.character.position import CHARACTER_POSITIONS

        sys.stdout.write("\n")
        logger.info(f"[时间轴] {action.time_str}: {action.description}")
        logger.info(f"  目标: {action.characters} | 当前: {sorted(self.current_char_state)}")

        target_set = set(action.characters)
        to_click = target_set.symmetric_difference(self.current_char_state)

        if not to_click:
            logger.info("  状态一致，无需点击")
            return

        for char_id in sorted(to_click):
            if char_id in CHARACTER_POSITIONS:
                x, y = CHARACTER_POSITIONS[char_id]
                action_type = "开启" if char_id in target_set else "关闭"
                logger.info(f"  {action_type} {char_id}号位 ({x}, {y})")
                self.device.click_adb(x, y)
                time.sleep(0.15)
            else:
                logger.warning(f"  无效角色ID: {char_id}")

        self.current_char_state = target_set

    def _save_debug_image(self, image, text_result, reason):
        """保存 OCR 错误截图到 logs/ocr_errors/"""
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
                logger.info(f"  [DEBUG] 错误截图: {filepath}")
        except Exception as e:
            logger.error(f"  保存调试截图失败: {e}")
