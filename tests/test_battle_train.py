"""
Test Battle Train - 测试战斗训练场
自动导航到训练场，开始战斗，监控倒计时到 0:01 后停止
用法:
    python tests/test_battle_train.py
    python tests/test_battle_train.py --droidcast  # 使用 DroidCast 截图
"""

import sys
import time
import re
import argparse
from threading import Thread, Lock
from queue import Queue, Empty

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.logger import logger
from module.ui.ui import UI
from module.ui.page import page_train
from module.train.combat import TrainCombat
from module.train.assets import *
from module.character.assets import *
from module.base.timer import Timer


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
        self.ocr_image = None  # Store image for debug
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
                    self.ocr_image = cropped_image
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
            return self.result, self.ocr_image, self.ocr_time



class BattleTrainTest(UI, TrainCombat):
    """
    战斗训练场测试类
    """

    def __init__(self, config, device=None):
        """
        Args:
            config: 配置对象
            device: 设备对象
        """
        super().__init__(config, device)

    def _on_monitor_loop(self, async_screenshot, current_time, timer_threshold_reached):
        """子类可重写此方法，在战斗监控循环中执行额外逻辑"""
        pass

    def ensure_in_train_page(self):
        """
        确保在训练场页面，如果不在则导航过去
        """
        logger.hr("Ensure in train page", level=1)
        self.ui_ensure(page_train)
        logger.info("✓ 已在训练场页面")

    def handle_train_interaction(self, slow_mode=False):
        """
        处理训练场界面交互流程
        新流程: Physical Test -> Simple Mode -> Challenge

        Args:
            slow_mode: 是否启用慢速调试模式(10倍延时)
        """
        logger.hr("Handle train interaction", level=1)

        if slow_mode:
            logger.warning("⚠️  慢速调试模式已启用 (10倍延时)")
            delay_multiplier = 10
        else:
            delay_multiplier = 1

        # 清空记录
        logger.info("清空设备记录...")
        self.device.stuck_record_clear()
        self.device.click_record_clear()
        time.sleep(0.5 * delay_multiplier)

        # 步骤 1: 点击 Physical Test (物理测试)
        logger.hr("Step 1: Click Physical Test", level=2)
        logger.info("点击 Physical Test 按钮...")
        self.device.screenshot()
        self.device.click(WULI_TEST)
        logger.info("✓ 已点击 Physical Test")
        time.sleep(2.0 * delay_multiplier)

        # 步骤 2: 点击 Simple Mode (简单模式)
        logger.hr("Step 2: Click Simple Mode", level=2)
        logger.info("点击 Simple Mode 按钮...")
        self.device.screenshot()
        self.device.click(EZ_BUTTON)
        logger.info("✓ 已点击 Simple Mode")
        time.sleep(2.0 * delay_multiplier)

        # 步骤 3: 点击 Challenge (挑战)
        logger.hr("Step 3: Click Challenge", level=2)
        logger.info("点击 Challenge 按钮...")
        self.device.screenshot()
        self.device.click(GO_BUTTON)
        logger.info("✓ 已点击 Challenge")
        time.sleep(2.0 * delay_multiplier)

        # 步骤 4: 等待进入角色选择界面
        logger.hr("Step 4: Wait for character selection", level=2)
        logger.info("等待角色选择界面...")
        confirm_timer = Timer(1.5, count=4).start()

        while 1:
            self.device.screenshot()

            if self.appear(CANCEL, offset=(30, 30)):
                if confirm_timer.reached():
                    logger.info("✓ 已进入角色选择界面")
                    break
            else:
                confirm_timer.reset()

            time.sleep(0.3 * delay_multiplier)

        logger.info("✓ 训练场交互完成!")
        return True

    def _is_interaction_complete(self) -> bool:
        """
        检查训练场交互是否完成

        Returns:
            bool: 是否完成交互
        """
        return self.appear(CANCEL, offset=(30, 30))

    def _execute_timeline_action(self, action):
        """
        执行时间轴动作（点击角色，自动处理SET状态切换）
        
        Args:
            action: TimelineAction 对象
        """
        from module.train.character_positions import CHARACTER_POSITIONS
        
        # 换行显示时间轴动作（避免覆盖倒计时显示）
        sys.stdout.write("\n")
        logger.info(f"[时间轴] {action.time_str}: {action.description}")
        logger.info(f"  目标状态: {action.characters} | 当前状态: {sorted(list(self.current_char_state))}")
        
        # 计算需要点击的角色（状态不一致的需要点击切换）
        target_set = set(action.characters)
        to_click = target_set.symmetric_difference(self.current_char_state)
        
        if not to_click:
            logger.info("  状态一致，无需点击")
            return

        for char_id in sorted(list(to_click)):
            if char_id in CHARACTER_POSITIONS:
                x, y = CHARACTER_POSITIONS[char_id]
                action_type = "开启" if char_id in target_set else "关闭"
                logger.info(f"  {action_type} {char_id}号位 (点击 {x}, {y})")
                # 使用 click_adb 直接点击坐标
                self.device.click_adb(x, y)
                time.sleep(0.15)  # 短暂延迟，避免点击过快
            else:
                logger.warning(f"  无效的角色ID: {char_id}")
        
        # 更新当前状态
        self.current_char_state = target_set

    def _save_debug_image(self, image, text_result, reason):
        """
        保存 OCR 错误截图
        """
        import cv2
        import os
        import numpy as np

        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            # Replace invalid char in text_result
            safe_text = str(text_result).replace(":", "_")
            filename = f"{timestamp}_{reason}_{safe_text}.png"
            
            save_dir = "./logs/ocr_errors"
            os.makedirs(save_dir, exist_ok=True)
            
            filepath = os.path.join(save_dir, filename)
            
            # Ensure image is valid for cv2
            if isinstance(image, np.ndarray):
                cv2.imwrite(filepath, image)
                logger.info(f"  [DEBUG] 错误截图已保存: {filepath}")
            else:
                 logger.warning("  [DEBUG] 无法保存截图: 格式不支持")

        except Exception as e:
            logger.error(f"  保存调试截图失败: {e}")

    def start_battle_and_monitor(self, use_droidcast=False, slow_mode=False, timeline=None):
        """
        完整流程:初始化OCR -> 训练场交互 -> 角色选择 -> 开始战斗 -> 监控倒计时

        Args:
            use_droidcast: 是否使用 DroidCast 截图
            slow_mode: 是否启用慢速调试模式
            timeline: Timeline 对象，定义时间轴动作（可选）
        """
        logger.hr("Start Battle and Monitor", level=0)

        # ========== 步骤 0: 初始化并预热 OCR ==========
        logger.hr("Step 0: Initialize and Warm up OCR", level=1)
        logger.info("初始化 OCR 引擎...")

        from module.train.assets import (
            AUTO,
            CANCEL,
            CHANGE,
            END,
            EZ_BUTTON,
            GO_BUTTON,
            MENU,
            SETTINGS,
            TEAM,
            WULI_TEST,
            REPORT,
        )
        from module.ocr.models import OCR_MODEL

        ocr_engine = OCR_MODEL.pcr

        logger.info("预热 OCR 模型...")
        ocr_engine.init()
        logger.info("✓ OCR 模型预热完成")

        # ========== 步骤 1: 训练场交互 ==========
        logger.hr("Step 1: Train Interaction", level=1)
        self.handle_train_interaction(slow_mode=slow_mode)

        # ========== 步骤 2: 角色选择 ==========
        logger.hr("Step 2: Character Selection", level=1)
        logger.info("跳过角色选择,使用默认队伍...")
        # TODO: 如果需要选择特定角色,在这里实现

        # ========== 步骤 3: 开始战斗 ==========
        logger.hr("Step 3: Start Battle", level=1)
        logger.info("点击开始战斗...")
        self.combat_preparation_with_ui_click()
        logger.info("✓ 已进入战斗")

        # 等待战斗界面稳定
        time.sleep(2.0)

        # ========== 步骤 4: 监控战斗倒计时 ==========
        logger.hr("Step 4: Monitor Battle Timer", level=1)
        self._monitor_battle_timer(ocr_engine, use_droidcast, timeline=timeline)

        # ========== 完成 ==========
        logger.hr("Battle Complete", level=0)
        logger.info("✓ 训练场战斗流程完成")
        logger.info("程序即将退出...")

        # 退出程序
        import sys

        sys.exit(0)

    def _monitor_battle_timer(self, ocr_engine, use_droidcast=False, timeline=None):
        """
        监控战斗倒计时,检测到 0:01 且连续失败后停止

        Args:
            ocr_engine: 已初始化的OCR引擎
            use_droidcast: 是否使用 DroidCast 截图
            timeline: Timeline 对象，定义时间轴动作（可选）
        """
        logger.hr("Monitor battle timer", level=1)

        # 倒计时区域 (x1, y1, x2, y2)
        timer_area = (1078, 24, 1120, 48)
        alphabet = "0123456789:"

        # 创建异步 OCR
        async_ocr = AsyncOCR(ocr_engine, alphabet=alphabet)

        # 选择截图方式
        if use_droidcast:
            logger.info("使用 DroidCast 截图模式...")
            logger.info("初始化 DroidCast 服务...")
            self.device.droidcast_init()
            time.sleep(1)
            logger.info("DroidCast 服务就绪")
            async_screenshot = AsyncScreenshotDroidCast(
                self.device, crop_area=timer_area
            )
            screenshot_mode = "DroidCast"
        else:
            logger.info("使用 NemuIpc 截图模式（极速）...")
            from module.device.method.nemu_ipc import get_nemu_ipc
            nemu = get_nemu_ipc(serial=self.device.serial)
            async_screenshot = AsyncScreenshotNemuIpc(nemu, crop_area=timer_area)
            screenshot_mode = "NemuIpc"

        logger.info(f"开始监控倒计时 (异步双缓冲 + {screenshot_mode})")
        logger.info(f"目标: 检测到倒计时≤0:01时停止")
        logger.info(f"{'='*70}")

        # 统计变量
        last_valid_timer_time = None  # 上次识别到的有效倒计时时间（秒数）
        last_valid_detection_time = time.time()  # 上次有效识别的时间戳
        detection_count = 0  # 检测次数
        
        # 状态变量
        self.current_char_state = set() # 当前开启SET的角色集合
        timer_threshold_reached = False # 是否已到达0:01阈值
        should_check_button = False     # 是否检测按钮
        self.time_travel_count = 0      # 连续时间倒流计数（用于错误自纠正）

        # 隐藏光标
        sys.stdout.write(HIDE_CURSOR)
        sys.stdout.flush()

        start_time = time.time()
        last_image = None  # 防止重复提交同一图片

        # 启动异步线程
        async_screenshot.start()
        async_ocr.start()

        # 初始化时间轴
        if timeline:
            timeline.reset()
            logger.info(f"时间轴已加载: {timeline.name} ({len(timeline.actions)} 个动作)")
            for action in sorted(timeline.actions, key=lambda x: x.time_seconds, reverse=True):
                logger.info(f"  - {action.time_str}: {action.description}")
        else:
            logger.info("未使用时间轴，仅监控倒计时")

        # 等待第一张截图
        while async_screenshot.get_image()[0] is None:
            time.sleep(0.01)

        try:
            while True:
                loop_start = time.time()

                # ========== 获取裁剪后的截图 ==========
                image, screenshot_time = async_screenshot.get_image()

                # ========== 如果是新图片，提交给 OCR 处理 ==========
                if image is not None and image is not last_image:
                    last_image = image
                    async_ocr.submit(image)

                # ========== 获取 OCR 结果 ==========
                text_result, ocr_image, ocr_time = async_ocr.get_result()

                current_time = time.time()
                elapsed = current_time - start_time

                # ========== 解析 OCR 结果 ==========
                # 解析时间字符串
                if not timer_threshold_reached and text_result:
                    total_seconds = parse_time_string(text_result.strip())

                    if total_seconds is not None and 0 <= total_seconds <= 90:
                        # ========== OCR 结果验证 ==========
                        is_valid = True
                        if last_valid_timer_time is not None:
                            # 计算预期时间窗口
                            time_since_last = current_time - last_valid_detection_time
                            expected_time = last_valid_timer_time - time_since_last
                            
                            # 允许的误差范围 (秒)
                            tolerance = 2.0
                            
                            # 1. 严格禁止倒流 (但包含错误自纠正机制)
                            # 如果新时间比上次大 (例如上次误读为30，这次正确读为32)
                            if total_seconds > last_valid_timer_time:
                                self.time_travel_count += 1
                                if self.time_travel_count > 3:
                                    logger.warning(f"  [OCR修正] 检测到连续的时间倒流，判定上次值为误读: {last_valid_timer_time} -> {total_seconds}")
                                    # 强制接受新值，并重置计数
                                    is_valid = True
                                    self.time_travel_count = 0
                                else:
                                    logger.warning(f"  [OCR滤除] 时间倒流: {last_valid_timer_time} -> {total_seconds} (连续{self.time_travel_count}次)")
                                    is_valid = False
                                    self._save_debug_image(ocr_image, text_result, "time_travel")
                                
                            # 2. 基于流逝时间的偏差检查
                            # 判定: 实际值不能比 (预期值 - 容差) 更小
                            elif total_seconds < (expected_time - tolerance):
                                logger.warning(f"  [OCR滤除] 异常跳变: 上次{last_valid_timer_time}s, 逝去{time_since_last:.1f}s, 预期~{expected_time:.1f}s, 实际{total_seconds}s")
                                is_valid = False
                                self._save_debug_image(ocr_image, text_result, "huge_drop")
                                
                                # 异常跳变不重置 time_travel_count，也不增加 (保持原样? 或者重置?)
                                # 这里重置它，因为不是倒流
                                self.time_travel_count = 0
                            else:
                                # 正常递减
                                self.time_travel_count = 0
                        

                        if is_valid:
                            # ========== OCR 识别成功 ==========
                            last_valid_timer_time = total_seconds
                            last_valid_detection_time = current_time
                            detection_count += 1

                            # 执行时间轴动作 (仅在有效识别时执行)
                            if timeline:
                                action = timeline.get_next_action(last_valid_timer_time)
                                if action and not action.executed:
                                    self._execute_timeline_action(action)
                                    action.executed = True

                        minutes = total_seconds // 60
                        seconds = total_seconds % 60
                        time_str = f"{minutes}:{seconds:02d}"

                        # 显示状态
                        val_str = "有效" if is_valid else "无效"
                        status = f"\r{CLEAR_LINE}[{elapsed:>5.1f}s] 倒计时: {time_str} ({val_str}) | 检测: {detection_count}"
                        sys.stdout.write(status)
                        sys.stdout.flush()

                        # 判断是否触发按钮检测：倒计时 ≤ 1 秒
                        if is_valid and last_valid_timer_time <= 1:
                            timer_threshold_reached = True
                            should_check_button = True
                            logger.info(f"\n[触发] 倒计时 {time_str} ≤ 1s，停止OCR检测，专心检测结算按钮...")
                    else:
                        # OCR 返回了无效的时间格式
                        detection_count += 1
                        status = f"\r{CLEAR_LINE}[{elapsed:>5.1f}s] OCR无效: '{text_result}' | 检测: {detection_count}"
                        sys.stdout.write(status)
                        sys.stdout.flush()

                # ========== 检查倒计时是否消失 ==========
                timer_missing_duration = current_time - last_valid_detection_time
                
                # 如果倒计时消失超过 3 秒，也触发按钮检测
                if timer_missing_duration > 3.0:
                    # 如果超时太久，可能是OCR一直失败，强制进入结束检测模式
                    if timer_missing_duration > 5.0 and not timer_threshold_reached:
                         # 只有在还没进入结束模式时才修改
                         should_check_button = True
                    
                    if timer_threshold_reached:
                        should_check_button = True

                    if int(timer_missing_duration) % 2 == 0 and int(timer_missing_duration) != int(timer_missing_duration - 0.1):
                        logger.info(f"\n 倒计时消失 {timer_missing_duration:.1f}s，检测结算按钮...")

                # ========== 检测结算按钮 ==========
                if should_check_button:
                    self.device.screenshot()
                    
                    # 检测 TEAM 按钮（结算界面标志）
                    # if self.appear(TEAM):
                    # if self.appear(REPORT):
                    if self.match_template_color(REPORT,interval=2):
                        debug_path = "./logs/debug_report_detected.png"
                        self.device.image_save(debug_path)
                        # logger.info(f"\n 检测到 TEAM 按钮！(运行: {elapsed:.1f}s)")
                        logger.info(f"\n 检测到 REPORT 按钮！(运行: {elapsed:.1f}s)")
                        logger.info(f"  截图已保存: {debug_path}")
                        # logger.info("  点击 TEAM 按钮...")
                        logger.info("  点击 REPORT 按钮...")
                        # self.device.click(TEAM)
                        self.device.click(REPORT)
                        time.sleep(1.0)
                        # logger.info("  已点击 TEAM")
                        logger.info("  已点击 REPORT")
                        break

                # ========== 子类钩子 ==========
                self._on_monitor_loop(async_screenshot, current_time, timer_threshold_reached)

                # ========== 控制循环频率 ==========
                loop_time = time.time() - loop_start
                if loop_time < 0.1:
                    time.sleep(0.1 - loop_time)
                    
        except KeyboardInterrupt:
            logger.info("\n 用户停止")
        finally:
            # 停止异步线程
            async_screenshot.stop()
            async_ocr.stop()

            # 恢复光标
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.write("\n")
            sys.stdout.flush()

            # 输出统计信息
            elapsed = time.time() - start_time
            logger.info("=" * 70)
            logger.info(f"监控统计 ({screenshot_mode} 模式)")
            logger.info("=" * 70)
            logger.info(f"  运行时间: {elapsed:.1f}s")
            logger.info(f"  总检测次数: {detection_count}")
            if last_valid_timer_time is not None:
                minutes = last_valid_timer_time // 60
                seconds = last_valid_timer_time % 60
                logger.info(f"  最后识别倒计时: {minutes}:{seconds:02d}")
            else:
                logger.info(f"  最后识别倒计时: 无")
            logger.info("=" * 70)


def main():
    """
    主测试函数
    """
    parser = argparse.ArgumentParser(description="测试战斗训练场")
    parser.add_argument(
        "--droidcast", action="store_true", help="使用 DroidCast 截图（较慢）"
    )
    parser.add_argument(
        "--slow", action="store_true", help="启用慢速调试模式 (10倍延时)"
    )
    parser.add_argument(
        "--timeline", action="store_true", help="启用时间轴自动点击角色"
    )
    args = parser.parse_args()

    # 初始化配置和设备
    config = PriconneConfig("maple", "Pcr")
    device = Device(config)
    # 禁用卡死检测
    device.disable_stuck_detection()

    # 实例化测试类
    battle_train_test = BattleTrainTest(config=config, device=device)

    # 创建时间轴（如果启用）
    timeline = None
    if args.timeline:
        from module.train.timeline import Timeline
        
        logger.hr("创建时间轴", level=1)
        
        # ========== 在这里自定义你的时间轴 ==========
        timeline = Timeline("1-D3-14764w")
        timeline.add_action("1:24", [1, 3, 4], "开UB")
        timeline.add_action("1:06", [1, 3], "开UB")
        timeline.add_action("0:58", [1, 3, 4], "开UB")
        timeline.add_action("0:49", [1, 2, 3], "开UB")
        timeline.add_action("0:34", [1, 3, 4], "开UB")
        timeline.add_action("0:29", [1, 2, 4], "开UB")
        timeline.add_action("0:19", [1, 2], "开UB")
        timeline.add_action("0:15", [1, 2, 3], "开UB")
        timeline.add_action("0:09", [1, 3, 4, 5], "开UB")
        # ==========================================
        
        logger.info(f"时间轴已创建: {timeline.name}")
        logger.info(f"共 {len(timeline.actions)} 个动作:")
        for action in sorted(timeline.actions, key=lambda x: x.time_seconds, reverse=True):
            logger.info(f"  - {action.time_str}: {action.description}")

    # # 1. 确保在训练场
    # battle_train_test.ensure_in_train_page()

    # 2. 开始战斗并监控倒计时
    battle_train_test.start_battle_and_monitor(
        use_droidcast=args.droidcast, 
        slow_mode=args.slow,
        timeline=timeline
    )

    logger.info("✓ 测试完成！程序即将退出...")
    sys.exit(0)  # 正常退出程序


if __name__ == "__main__":
    main()
