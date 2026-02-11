"""
实时倒计时识别测试 (方案四：视觉 + 多帧一致性 + 逻辑锚点)
"""

import sys
import time
import os
import re
import argparse
import cv2
import numpy as np
from collections import deque
from threading import Thread, Lock
from queue import Queue, Empty

sys.path.insert(0, "./")

# =============================================================================
# 核心参数调整
# =============================================================================
CONFIRM_FRAMES = 3          # 连续 N 帧一致才采纳
SIMILARITY_THRESHOLD = 0.70 # 视觉相似度阈值

# [新增] 最大允许丢帧数
# 允许：40 -> 39 (diff 1), 40 -> 38 (diff 2), 40 -> 37 (diff 3)
# 拒绝：40 -> 31 (diff 9) -> 这种会被视为 OCR 误识别，直接丢弃
MAX_DROP_TOLERANCE = 3 

# [新增] 场景切换阈值
# 如果 diff > 15，说明可能是切场景了（比如 40s 直接变成 0s 结算，或者重置到 90s）
# 这种情况下我们才允许大跳跃
SCENE_CHANGE_THRESHOLD = 15

# =============================================================================

# ANSI 转义码
CLEAR_LINE = "\033[K"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

def parse_time_string(s):
    if not s: return None
    match = re.match(r"^(\d{1,2})[:：](\d{2})$", s)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    match = re.match(r"^(\d{1,3})$", s)
    if match:
        sec = int(match.group(1))
        if sec <= 90: return sec
    return None

def calculate_image_similarity(img1, img2):
    if img1 is None or img2 is None: return 0.0
    try:
        g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        hist1 = cv2.calcHist([g1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([g2], [0], None, [256], [0, 256])
        cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
        return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    except: return 0.0

# --- 截图类 (保持不变) ---
class AsyncScreenshotNemuIpc:
    def __init__(self, nemu_ipc, crop_area=None):
        self.nemu_ipc = nemu_ipc
        self.crop_area = crop_area
        self.latest_cropped = None
        self.lock = Lock()
        self.running = False
        self.thread = None
    def start(self):
        self.running = True
        self.thread = Thread(target=self._loop, daemon=True)
        self.thread.start()
    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=1)
    def _loop(self):
        while self.running:
            try:
                img = self.nemu_ipc.screenshot()
                if self.crop_area:
                    x1, y1, x2, y2 = self.crop_area
                    res = img[y1:y2, x1:x2].copy()
                else: res = img
                with self.lock: self.latest_cropped = res
            except: pass
    def get_image(self):
        with self.lock: return self.latest_cropped

class AsyncScreenshotDroidCast:
    def __init__(self, device, crop_area=None):
        self.device = device
        self.crop_area = crop_area
        self.latest_cropped = None
        self.lock = Lock()
        self.running = False
        self.thread = None
    def start(self):
        self.running = True
        self.thread = Thread(target=self._loop, daemon=True)
        self.thread.start()
    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=1)
    def _loop(self):
        while self.running:
            try:
                img = self.device.screenshot_droidcast_raw()
                if self.crop_area:
                    x1, y1, x2, y2 = self.crop_area
                    res = img[y1:y2, x1:x2].copy()
                else: res = img
                with self.lock: self.latest_cropped = res
            except: pass
    def get_image(self):
        with self.lock: return self.latest_cropped

# --- OCR 类 (保持不变) ---
class AsyncOCR:
    def __init__(self, ocr_engine, alphabet=None):
        self.ocr_engine = ocr_engine
        self.alphabet = alphabet
        self.input_queue = Queue(maxsize=2)
        self.result = None
        self.processed_img = None
        self.lock = Lock()
        self.running = False
        self.thread = None
    def start(self):
        self.running = True
        self.thread = Thread(target=self._loop, daemon=True)
        self.thread.start()
    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=1)
    def _loop(self):
        while self.running:
            try:
                img = self.input_queue.get(timeout=0.1)
                res = self.ocr_engine.atomic_ocr_for_single_lines([img], self.alphabet)
                txt = "".join(res[0]) if res and res[0] else ""
                with self.lock:
                    self.result = txt
                    self.processed_img = img
            except Empty: pass
            except: pass
    def submit(self, img):
        try:
            if self.input_queue.full(): self.input_queue.get_nowait()
            self.input_queue.put_nowait(img)
        except: pass
    def get_result(self):
        with self.lock: return self.result, self.processed_img

# -----------------------------------------------------------------------------
# 主程序
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--droidcast", action="store_true")
    args = parser.parse_args()

    timer_area = (1078, 24, 1120, 48)
    alphabet = "0123456789:"

    if args.droidcast:
        print("Mode: DroidCast")
        from module.config.config import PriconneConfig
        from module.device.device import Device
        config = PriconneConfig("maple", "Pcr")
        device = Device(config)
        device.disable_stuck_detection()
        device.droidcast_init()
        time.sleep(1)
        async_screenshot = AsyncScreenshotDroidCast(device, crop_area=timer_area)
    else:
        print("Mode: NemuIpc")
        from module.device.method.nemu_ipc import NemuIpcImpl
        nemu_folder = r"C:\Program Files\Netease\MuMu Player 12"
        nemu = NemuIpcImpl(nemu_folder, instance_id=0)
        nemu.connect()
        async_screenshot = AsyncScreenshotNemuIpc(nemu, crop_area=timer_area)

    from module.ocr.models import OCR_MODEL
    ocr_engine = OCR_MODEL.pcr
    print("Pre-heating OCR...")
    ocr_engine.init()
    async_ocr = AsyncOCR(ocr_engine, alphabet=alphabet)

    prev_seconds = None         
    last_stable_image = None    
    candidate_queue = deque(maxlen=CONFIRM_FRAMES)
    
    count = 0
    start_time = time.time()
    
    status_line = ""
    def print_log(msg):
        sys.stdout.write(f"\r{CLEAR_LINE}{msg}\n")
        sys.stdout.write(status_line)
        sys.stdout.flush()

    sys.stdout.write(HIDE_CURSOR)
    async_screenshot.start()
    async_ocr.start()
    
    while async_screenshot.get_image() is None: time.sleep(0.01)
    last_image = None

    try:
        while True:
            image = async_screenshot.get_image()
            if image is not None and image is not last_image:
                last_image = image
                async_ocr.submit(image)

            text_result, processed_img = async_ocr.get_result()
            
            # 1. 视觉检测
            is_vfx = False
            sim = 0.0
            if last_stable_image is not None and processed_img is not None:
                sim = calculate_image_similarity(last_stable_image, processed_img)
                if sim < SIMILARITY_THRESHOLD:
                    is_vfx = True
            
            # 2. 解析
            current_val = parse_time_string(text_result)

            # 3. 队列管理
            if not is_vfx and current_val is not None and 0 <= current_val <= 5400:
                candidate_queue.append(current_val)
            else:
                candidate_queue.clear()

            # 4. 确认逻辑
            if len(candidate_queue) == CONFIRM_FRAMES:
                first = candidate_queue[0]
                if all(x == first for x in candidate_queue):
                    confirmed_time = first
                    
                    # --- 初始化 ---
                    if prev_seconds is None:
                        prev_seconds = confirmed_time
                        last_stable_image = processed_img
                        print_log(f"[{count:04d}] {confirmed_time//60}:{confirmed_time%60:02d} ({confirmed_time}s) [初始] | Sim:{sim:.4f}")
                        count += 1
                    
                    # --- 运行中 ---
                    else:
                        diff = prev_seconds - confirmed_time
                        
                        # [关键修改]：逻辑锚点检测
                        # -------------------------------------------------
                        
                        # 情况 1: 完美同步 (diff == 1)
                        if diff == 1:
                            prev_seconds = confirmed_time
                            last_stable_image = processed_img
                            print_log(f"[{count:04d}] {confirmed_time//60}:{confirmed_time%60:02d} ({confirmed_time:3d}s) | Sim:{sim:.4f}")
                            count += 1
                            
                        # 情况 2: 合理的回正 (1 < diff <= 3)
                        # 允许丢失 2-3 帧，认为这是 OCR 暂时没跟上，现在跟上了
                        elif 1 < diff <= MAX_DROP_TOLERANCE:
                            prev_seconds = confirmed_time
                            last_stable_image = processed_img
                            print_log(f"[{count:04d}] {confirmed_time//60}:{confirmed_time%60:02d} ({confirmed_time:3d}s) [回正 丢{diff-1}s] | Sim:{sim:.4f}")
                            count += 1
                        
                        # 情况 3: 恐怖的异常跳跃 (3 < diff <= 15)
                        # 比如 40 -> 31 (diff=9)
                        # 即使 Sim=0.89 且 连续 3 帧确认，这在物理上也是不可能的。
                        # 我们坚定地认为这是 OCR 误识别（把9看成了1），拒绝更新！
                        elif MAX_DROP_TOLERANCE < diff <= SCENE_CHANGE_THRESHOLD:
                             # 只是打印调试信息，但不更新 prev_seconds
                             # 这样脚本会继续坚守在 40s，等待真正的 39s 或 38s 出现
                            debug_msg = f"[逻辑拦截] 拒绝: {confirmed_time}s (Diff {diff}s > Limit {MAX_DROP_TOLERANCE}) | Sim:{sim:.4f}"
                            # status_line 会显示这个错误
                            pass

                        # 情况 4: 场景切换 (diff > 15)
                        # 比如 40 -> 0 或 40 -> 90
                        elif diff > SCENE_CHANGE_THRESHOLD:
                            prev_seconds = confirmed_time
                            last_stable_image = processed_img
                            print_log(f"[{count:04d}] {confirmed_time//60}:{confirmed_time%60:02d} ({confirmed_time:3d}s) [场景切换] | Sim:{sim:.4f}")
                            count += 1
                            
                        # 情况 5: 时间倒流 (diff < 0) 
                        # 比如 40 -> 41，通常是误识别或者重置
                        else:
                            pass

            # 状态显示
            elapsed = int(time.time() - start_time)
            queue_display = [str(x) for x in candidate_queue]
            status_line = f"\r{CLEAR_LINE}[{elapsed}s] 队列:{str(queue_display):<15} Sim:{sim:.4f} | 上次:{prev_seconds}"
            sys.stdout.write(status_line)
            sys.stdout.flush()
            
            time.sleep(0.005)

    except KeyboardInterrupt:
        pass
    finally:
        async_screenshot.stop()
        async_ocr.stop()
        sys.stdout.write(SHOW_CURSOR)
        print("\nDone.")

if __name__ == "__main__":
    main()