"""
异步 OCR 模块
在后台线程持续消费图片队列，供实时识别场景使用（如战斗倒计时）
"""

import time
from threading import Thread, Lock
from queue import Queue, Empty


class AsyncOCR:
    """
    异步 OCR 识别器。
    主线程通过 submit() 投递图片，后台线程负责识别，主线程通过 get_result() 取结果。
    使用有界队列 (maxsize=2) 自动丢弃过旧的帧，保持结果新鲜度。
    """

    def __init__(self, ocr_engine, alphabet=None):
        """
        Args:
            ocr_engine: PaddleOcrEngine / CnOcrEngine 实例，需有 atomic_ocr_for_single_lines()
            alphabet (str | None): 候选字符白名单，传给 OCR 引擎
        """
        self.ocr_engine = ocr_engine
        self.alphabet = alphabet
        self._queue = Queue(maxsize=2)
        self._lock = Lock()
        self._result = None       # 最新识别文本
        self._ocr_image = None    # 对应的输入图像（用于调试）
        self._ocr_time = 0.0      # 上次识别耗时(秒)
        self.running = False
        self.thread = None

    # ─── 生命周期 ────────────────────────────────────────────────────────

    def start(self):
        """启动后台识别线程"""
        self.running = True
        self.thread = Thread(target=self._ocr_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止后台识别线程"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    # ─── 主线程接口 ──────────────────────────────────────────────────────

    def submit(self, image):
        """
        投递一张图片到识别队列（非阻塞）。
        如队列已满，丢弃最旧的帧再插入，确保最新帧总能进入队列。

        Args:
            image (np.ndarray): 待识别图像
        """
        try:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except Empty:
                    pass
            self._queue.put_nowait(image)
        except Exception:
            pass

    def get_result(self):
        """
        获取最新识别结果（线程安全，非阻塞）。

        Returns:
            (str | None, np.ndarray | None, float): (识别文本, 对应图像, 识别耗时)
        """
        with self._lock:
            return self._result, self._ocr_image, self._ocr_time

    # ─── 后台线程 ────────────────────────────────────────────────────────

    def _ocr_loop(self):
        while self.running:
            try:
                image = self._queue.get(timeout=0.1)
                t0 = time.time()
                results = self.ocr_engine.atomic_ocr_for_single_lines(
                    [image], self.alphabet
                )
                text = "".join(results[0]) if results and results[0] else ""
                elapsed = time.time() - t0
                with self._lock:
                    self._result = text
                    self._ocr_image = image
                    self._ocr_time = elapsed
            except Empty:
                pass
            except Exception:
                pass
