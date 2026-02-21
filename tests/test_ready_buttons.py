"""
Test Ready Buttons - 战斗中auto出UB检测
运行 test_battle_train --timeline 的同时，持续检测五个角色位的auto UB状态
逻辑：同时检测到"满"+"就绪" → 两者同时消失 → 识别为auto出了UB

用法:
    python tests/test_ready_buttons.py            # 运行战斗+auto检测
    python tests/test_ready_buttons.py --single    # 单次截图检测
"""

import sys
import time
import argparse
import cv2

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.logger import logger
from module.train.assets import (
    一号位就绪,
    二号位就绪,
    三号位就绪,
    四号位就绪,
    五号位就绪,
    一号位满,
    二号位满,
    三号位满,
    四号位满,
    五号位满,
)
from tests.test_battle_train import BattleTrainTest


# (就绪按钮, 满按钮, 名称)
POSITION_BUTTONS = [
    (一号位就绪, 一号位满, "一号位"),
    (二号位就绪, 二号位满, "二号位"),
    (三号位就绪, 三号位满, "三号位"),
    (四号位就绪, 四号位满, "四号位"),
    (五号位就绪, 五号位满, "五号位"),
]


class ReadyButtonBattleTest(BattleTrainTest):
    """继承 BattleTrainTest，在战斗监控中加入auto出UB检测"""

    # 连续几帧都检测不到才判定为消失（防抖）
    DEBOUNCE_FRAMES = 3

    def __init__(self, config, device=None):
        super().__init__(config, device)
        self._last_full_image = None
        # 每个位置的状态: False=未蓄满, True=满+就绪同时存在
        self._charged = [False] * 5
        # 防抖计数器：连续检测不到的帧数
        self._gone_count = [0] * 5

    def _on_monitor_loop(self, async_screenshot, current_time, timer_threshold_reached):
        """每次循环检测auto出UB"""
        if timer_threshold_reached:
            return

        full_image = async_screenshot.get_full_image()
        if full_image is None or full_image is self._last_full_image:
            return
        self._last_full_image = full_image

        # AsyncScreenshotNemuIpc 返回 BGR，但 device.image 需要 RGB
        self.device.image = cv2.cvtColor(full_image, cv2.COLOR_BGR2RGB)

        for i, (ready_btn, full_btn, name) in enumerate(POSITION_BUTTONS):
            has_ready = self.appear(ready_btn, offset=(20, 20))
            has_full = self.appear(full_btn, offset=(20, 20))

            if has_ready and has_full:
                # 满+就绪同时存在，标记为蓄满
                self._gone_count[i] = 0
                if not self._charged[i]:
                    self._charged[i] = True
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    logger.info(f"[蓄力检测] {name} 满+就绪")
            elif self._charged[i] and not has_ready and not has_full:
                # 连续多帧都检测不到才判定为auto出
                self._gone_count[i] += 1
                if self._gone_count[i] >= self.DEBOUNCE_FRAMES:
                    self._charged[i] = False
                    self._gone_count[i] = 0
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    logger.info(f"[AUTO UB] 已识别到{name}auto出")
            else:
                # 只有一个消失或都不在但没charged，重置计数
                self._gone_count[i] = 0


def test_single_screenshot():
    """单次截图检测五个就绪按钮"""
    from module.ui.ui import UI

    config = PriconneConfig("maple", "Pcr")
    device = Device(config)
    device.disable_stuck_detection()

    class SingleTest(UI):
        pass

    test = SingleTest(config=config, device=device)
    logger.hr("单次截图检测就绪按钮", level=1)

    test.device.screenshot()
    image = test.device.image
    logger.info(f"截图尺寸: {image.shape}, dtype: {image.dtype}")

    from module.base.utils import crop

    for ready_btn, full_btn, name in POSITION_BUTTONS:
        for btn, label in [(ready_btn, "就绪"), (full_btn, "满")]:
            btn.ensure_template()
            template = btn.image
            logger.info(f"{name}{label} 模板尺寸: {template.shape}, 检测区域: {btn.area}")

            area = btn.area
            ox, oy = 20, 20
            search_area = (area[0]-ox, area[1]-oy, area[2]+ox, area[3]+oy)
            search_img = crop(image, search_area, copy=False)
            logger.info(f"  搜索区域: {search_area}, 裁剪尺寸: {search_img.shape}")

            res = cv2.matchTemplate(template, search_img, cv2.TM_CCOEFF_NORMED)
            _, sim, _, point = cv2.minMaxLoc(res)
            detected = test.appear(btn, offset=(20, 20))
            status = "已检测到" if detected else "未检测到"
            logger.info(f"  相似度: {sim:.4f} -> {status}")

    # 保存截图方便查看
    debug_path = "./logs/debug_ready_buttons.png"
    import os
    os.makedirs("./logs", exist_ok=True)
    test.device.image_save(debug_path)
    logger.info(f"截图已保存: {debug_path}")


def main():
    parser = argparse.ArgumentParser(description="战斗中就绪按钮检测")
    parser.add_argument("--single", action="store_true", help="仅单次截图检测")
    args = parser.parse_args()

    if args.single:
        test_single_screenshot()
        return

    # 初始化
    config = PriconneConfig("maple", "Pcr")
    device = Device(config)
    device.disable_stuck_detection()

    test = ReadyButtonBattleTest(config=config, device=device)

    # 创建时间轴
    from module.battle.timeline import Timeline

    logger.hr("创建时间轴", level=1)
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

    logger.info(f"时间轴: {timeline.name} ({len(timeline.actions)} 个动作)")

    # 运行战斗 + 就绪检测
    test.start_battle_and_monitor(timeline=timeline)


if __name__ == "__main__":
    main()
