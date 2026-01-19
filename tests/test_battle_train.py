"""
Test Battle Train - 测试战斗训练场

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

    def start_battle_and_monitor(self, use_droidcast=False, slow_mode=False):
        """
        完整流程:初始化OCR -> 训练场交互 -> 角色选择 -> 开始战斗 -> 监控倒计时
        
        Args:
            use_droidcast: 是否使用 DroidCast 截图
            slow_mode: 是否启用慢速调试模式
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
        self._monitor_battle_timer(ocr_engine, use_droidcast)
        
        # ========== 完成 ==========
        logger.hr("Battle Complete", level=0)
        logger.info("✓ 训练场战斗流程完成")
        logger.info("程序即将退出...")
        
        # 退出程序
        import sys
        sys.exit(0)

    def _monitor_battle_timer(self, ocr_engine, use_droidcast=False):
        """
        监控战斗倒计时,检测到 0:01 且连续失败后停止
        
        Args:
            ocr_engine: 已初始化的OCR引擎
            use_droidcast: 是否使用 DroidCast 截图
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
            async_screenshot = AsyncScreenshotDroidCast(self.device, crop_area=timer_area)
            screenshot_mode = "DroidCast"
        else:
            logger.info("使用 NemuIpc 截图模式（极速）...")
            from module.device.method.nemu_ipc import NemuIpcImpl

            nemu_folder = r"C:\Program Files\Netease\MuMu Player 12"
            nemu = NemuIpcImpl(nemu_folder, instance_id=0)
            nemu.connect()
            async_screenshot = AsyncScreenshotNemuIpc(nemu, crop_area=timer_area)
            screenshot_mode = "NemuIpc"
            
        logger.info(f"开始监控倒计时 (异步双缓冲 + {screenshot_mode})")
        logger.info(f"目标: 检测到倒计时≤0:01时停止")
        logger.info(f"{'='*70}")

        # 统计
        consecutive_failures = 0  # 连续识别失败次数
        target_reached = False  # 是否已到达目标时间 0:01
        last_valid_time = None  # 上次有效识别的时间
        detection_count = 0  # 检测次数

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
        start_time = time.time()

        try:
            while True:
                loop_start = time.time()

                # 1. 先获取并处理 OCR 倒计时
                image, screenshot_time = async_screenshot.get_image()

                if image is not None and image is not last_image:
                    last_image = image
                    # 提交给 OCR 处理
                    async_ocr.submit(image)

                # 获取 OCR 结果
                text_result, ocr_time = async_ocr.get_result()

                if text_result:
                    # 解析时间字符串
                    total_seconds = parse_time_string(text_result)

                    if total_seconds is not None and 0 <= total_seconds <= 90:
                        # 识别成功
                        consecutive_failures = 0
                        last_valid_time = total_seconds
                        detection_count += 1

                        minutes = total_seconds // 60
                        seconds = total_seconds % 60
                        time_str = f"{minutes}:{seconds:02d}"

                        # 更新状态
                        elapsed = int(time.time() - start_time)
                        status = f"\r{CLEAR_LINE}[{elapsed:>4}s] 当前时间: {time_str} | 检测次数: {detection_count:>3}"
                        sys.stdout.write(status)
                        sys.stdout.flush()
                    else:
                        # 识别失败（无效时间）
                        consecutive_failures += 1
                        detection_count += 1

                        # 更新状态
                        elapsed = int(time.time() - start_time)
                        status = f"\r{CLEAR_LINE}[{elapsed:>4}s] 识别失败 | 检测次数: {detection_count:>3} | 连续失败: {consecutive_failures}"
                        sys.stdout.write(status)
                        sys.stdout.flush()

                # 2. 通用型战斗结束检测策略 (去除了所有硬编码的时间限制)
                # 核心逻辑:
                # 1. 记录"最后一次看到有效倒计时"的时间 (last_valid_timer_time)
                # 2. 如果当前有倒计时且 <= 3秒 -> 触发检测 (战斗即将结束)
                # 3. 如果当前没有倒计时, 且距离上次看到有效倒计时已经过了3秒 -> 触发检测 (倒计时消失意味着战斗结束)
                
                # 初始化变量 (放在循环外, 这里只是注释说明)
                if "_last_valid_timer_time" not in locals():
                    locals()["_last_valid_timer_time"] = time.time()
                
                should_check_button = False
                current_time = time.time()
                
                if text_result:
                    # 读取到倒计时
                    total_seconds = parse_time_string(text_result)
                    if total_seconds is not None:
                         # 更新最后有效时间
                         locals()["_last_valid_timer_time"] = current_time
                         
                         if total_seconds <= 3:
                             # 倒计时即将归零
                             should_check_button = True
                             logger.info(f"倒计时剩余 {total_seconds}s, 准备检测结算按钮...")
                else:
                    # 读取不到倒计时 (可能是消失了, 也可能是偶尔识别失败)
                    # 计算"倒计时丢失时长"
                    missing_duration = current_time - locals()["_last_valid_timer_time"]
                    
                    # 只有当倒计时连续丢失超过3秒, 才认为是真的消失了(战斗结束)
                    if missing_duration > 3.0:
                        should_check_button = True
                        if int(missing_duration) % 5 == 0: # 避免日志刷屏
                             logger.info(f"倒计时消失已持续 {missing_duration:.1f}s, 尝试检测结算按钮...")

                if should_check_button:
                    self.device.screenshot()
                    
                    # 检测TEAM按钮 (结算界面标志)
                    if self.appear(TEAM, offset=30, similarity=0.98):
                        elapsed = time.time() - start_time
                        debug_path = "./logs/debug_team_detected.png"
                        self.device.image_save(debug_path)
                        logger.info(f"\n✓ 检测到TEAM按钮! (运行时间: {elapsed:.1f}s)")
                        logger.info(f"  调试截图已保存: {debug_path}")
                        logger.info("点击TEAM按钮...")
                        self.device.click(TEAM)
                        time.sleep(1.0)
                        logger.info("✓ 已点击TEAM按钮")
                        break
                    else:
                        pass # 没检测到就继续循环等待
                else:
                    # 战斗进行中日志
                    if int(elapsed) % 30 == 0 and int(elapsed) > 0 and "_last_log_time" not in locals():
                         logger.info(f"  战斗进行中... (倒计时: {text_result if text_result else '未知'}, 运行: {elapsed:.0f}s)")
                         locals()["_last_log_time"] = int(elapsed)
                    elif int(elapsed) % 30 != 0 and "_last_log_time" in locals():
                        del locals()["_last_log_time"]

                # 控制循环频率
                loop_time = time.time() - loop_start
                if loop_time < 0.1:
                    time.sleep(0.1 - loop_time)
        except KeyboardInterrupt:
            logger.info("\n用户中断")
        finally:
            # 停止异步线程
            async_screenshot.stop()
            async_ocr.stop()

            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.write("\n")
            sys.stdout.flush()

            elapsed = time.time() - start_time
            logger.info("=" * 70)
            logger.info(f"监控统计 ({screenshot_mode} 模式)")
            logger.info("=" * 70)
            logger.info(f"运行时间: {elapsed:.1f}s")
            logger.info(f"总检测次数: {detection_count}")
            logger.info(f"最后有效时间: {last_valid_time}s" if last_valid_time else "最后有效时间: 无")
            logger.info(f"是否到达目标: {'是' if target_reached else '否'}")


def main():
    """
    主测试函数
    """
    parser = argparse.ArgumentParser(description="测试战斗训练场")
    parser.add_argument("--droidcast", action="store_true", help="使用 DroidCast 截图（较慢）")
    parser.add_argument("--slow", action="store_true", help="启用慢速调试模式 (10倍延时)")
    args = parser.parse_args()

    # 初始化配置和设备
    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)
    # 禁用卡死检测
    device.disable_stuck_detection()

    # 实例化测试类
    battle_train_test = BattleTrainTest(config=config, device=device)

    # 1. 确保在训练场
    battle_train_test.ensure_in_train_page()

    # 2. 开始战斗并监控倒计时
    battle_train_test.start_battle_and_monitor(
        use_droidcast=args.droidcast,
        slow_mode=args.slow
    )

    logger.info("✓ 测试完成！程序即将退出...")
    sys.exit(0)  # 正常退出程序


if __name__ == "__main__":
    main()
