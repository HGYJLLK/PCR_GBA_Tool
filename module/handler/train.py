"""
训练场自动化 Handler
"""

import time
import sys
import re
from threading import Thread, Lock
from queue import Queue, Empty

from module.ui.ui import UI
from module.train.combat import TrainCombat
from module.logger import logger
from module.ui.page import page_train
from module.train.assets import *
from module.base.timer import Timer
from module.character.selector import CharacterSelector

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


class TrainHandler(UI, TrainCombat):
    def __init__(self, config, device=None):
        super().__init__(config, device)
        # TODO: 从配置中读取目标角色
        self.character_selector = CharacterSelector(main=self, target_characters={})
        self.time_travel_count = 0
        self.current_char_state = set()

    def run(self):
        """
        执行训练场任务
        """
        logger.hr("Train Task", level=1)
        
        # 1. 导航到训练场
        self.ui_ensure(page_train)
        
        # 2. 交互流程 (Physical Test -> Simple Mode -> Challenge)
        self.handle_train_interaction()
        
        # 3. 角色选择 (目前MVP版本跳过，后续可集成CharacterSelector)
        # self.character_selector.ensure_characters_selected()
        
        # 4. 战斗准备
        self.combat_preparation_with_ui_click()
        
        # 5. 监控战斗
        self._start_battle_monitoring()

    def handle_train_interaction(self, slow_mode=False):
        """
        处理训练场界面交互流程
        """
        logger.hr("Handle train interaction", level=2)

        if slow_mode:
            delay_multiplier = 10
        else:
            delay_multiplier = 1

        # 清空记录
        self.device.stuck_record_clear()
        self.device.click_record_clear()

        # 步骤 1: 点击 Physical Test
        if self.appear(WULI_TEST, interval=5):
            self.device.click(WULI_TEST)
            time.sleep(2.0 * delay_multiplier)

        # 步骤 2: 点击 Simple Mode
        if self.appear(EZ_BUTTON, interval=5):
            self.device.click(EZ_BUTTON)
            time.sleep(2.0 * delay_multiplier)

        # 步骤 3: 点击 Challenge
        if self.appear(GO_BUTTON, interval=5):
            self.device.click(GO_BUTTON)
            time.sleep(2.0 * delay_multiplier)

        # 步骤 4: 等待进入角色选择界面 (等待 CANCEL 按钮出现)
        confirm_timer = Timer(1.5, count=4).start()
        while 1:
            self.device.screenshot()
            if self.appear(CANCEL, offset=(30, 30)):
                if confirm_timer.reached():
                    break
            else:
                confirm_timer.reset()
            
            # 补救措施：如果卡在中间步骤
            if self.appear(GO_BUTTON, interval=2):
                 self.device.click(GO_BUTTON)

            time.sleep(0.3 * delay_multiplier)

        logger.info("已进入角色选择界面")

    def _start_battle_monitoring(self):
        """
        开始战斗监控
        """
        from module.ocr.models import OCR_MODEL
        ocr_engine = OCR_MODEL.pcr
        ocr_engine.init()
        
        # 使用配置决定截图方式
        use_droidcast = self.config.Emulator_ScreenshotMethod == "DroidCast_raw"
        
        self._monitor_battle_timer(ocr_engine, use_droidcast=use_droidcast)

    def _monitor_battle_timer(self, ocr_engine, use_droidcast=False, timeline=None):
        """
        监控战斗倒计时
        """
        logger.hr("Monitor battle timer", level=2)

        # 倒计时区域 (x1, y1, x2, y2)
        timer_area = (1078, 24, 1120, 48)
        alphabet = "0123456789:"

        # 创建异步 OCR
        async_ocr = AsyncOCR(ocr_engine, alphabet=alphabet)

        # 选择截图方式
        if use_droidcast:
            if not hasattr(self.device, 'droidcast_init'):
                 # 如果设备对象不支持droidcast_init (可能是MockDevice)，降级处理
                 logger.warning("设备不支持 DroidCast 初始化，尝试直接使用")
            else:
                 self.device.droidcast_init()
            
            async_screenshot = AsyncScreenshotDroidCast(
                self.device, crop_area=timer_area
            )
            screenshot_mode = "DroidCast"
        else:
            # 尝试使用 NemuIpc
            try:
                from module.device.method.nemu_ipc import NemuIpcImpl
                # 需要获取模拟器路径，这里简化处理，如果配置中有
                # 或者直接使用 ADB 截图 (降级)
                if self.config.Emulator_ScreenshotMethod == "NemuIpc":
                     nemu_folder = r"C:\Program Files\Netease\MuMu Player 12" # TODO: 从配置读取
                     nemu = NemuIpcImpl(nemu_folder, instance_id=0)
                     nemu.connect()
                     async_screenshot = AsyncScreenshotNemuIpc(nemu, crop_area=timer_area)
                     screenshot_mode = "NemuIpc"
                else:
                     # 默认使用 DroidCast (兼容性好)
                     async_screenshot = AsyncScreenshotDroidCast(self.device, crop_area=timer_area)
                     screenshot_mode = "DroidCast(Fallback)"
            except:
                async_screenshot = AsyncScreenshotDroidCast(self.device, crop_area=timer_area)
                screenshot_mode = "DroidCast(Fallback)"

        logger.info(f"开始监控倒计时 ({screenshot_mode})")

        # 统计变量
        last_valid_timer_time = None
        last_valid_detection_time = time.time()
        
        timer_threshold_reached = False
        should_check_button = False

        start_time = time.time()
        last_image = None

        async_screenshot.start()
        async_ocr.start()

        try:
            while True:
                # 获取截图
                image, screenshot_time = async_screenshot.get_image()
                if image is None:
                    time.sleep(0.01)
                    continue

                if image is not last_image:
                    last_image = image
                    async_ocr.submit(image)

                text_result, ocr_image, ocr_time = async_ocr.get_result()
                current_time = time.time()

                if not timer_threshold_reached and text_result:
                    total_seconds = parse_time_string(text_result.strip())
                    if total_seconds is not None and 0 <= total_seconds <= 90:
                        # 简单验证
                        last_valid_timer_time = total_seconds
                        last_valid_detection_time = current_time
                        
                        if last_valid_timer_time <= 1:
                            timer_threshold_reached = True
                            should_check_button = True
                            logger.info(f"倒计时 {total_seconds}s ≤ 1s，开始检测结算")

                # 检查倒计时消失
                if current_time - last_valid_detection_time > 3.0:
                    should_check_button = True

                if should_check_button:
                    # 使用 ADB 截图全屏检测
                    self.device.screenshot()
                    if self.appear(REPORT, interval=2):
                        logger.info("检测到 REPORT 按钮，战斗结束")
                        self.device.click(REPORT)
                        break

                time.sleep(0.1)

        finally:
            async_screenshot.stop()
            async_ocr.stop()
            logger.info("监控结束")
