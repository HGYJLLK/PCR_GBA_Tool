"""
使用 NemuIpc 持续截图并选择角色的测试文件
基于 test_battle_train.py 的 NemuIpc 实现模式
"""
import sys
import time

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.base.timer import Timer
from module.logger import logger
from module.ui.ui import UI
from module.ui.page import page_train
from module.train.assets import *
from module.character.assets import *
from module.ui.scroll import Scroll
from module.base.mask import Mask
from module.character.selector import Selector
from module.train.combat import TrainCombat


class NemuIpcSelectorTest(UI, TrainCombat):
    """
    使用 NemuIpc 截图的角色选择测试类
    """

    def __init__(self, config, device=None):
        """
        Args:
            config: 配置对象
            device: 设备对象
        """
        super().__init__(config, device)

        # 目标角色
        self.target_characters = {
            "CHUNJIAN": TEMPLATE_CHUNJIAN,
            "QINGBING": TEMPLATE_QINGBING,
            "SHUIMA": TEMPLATE_SHUIMA,
            "TIANJIE": TEMPLATE_TIANJIE,
            "SHUISHENGMU": TEMPLATE_SHUISHENGMU,
        }

        # 创建角色选择器
        self.character_selector = Selector(
            main=self,
            target_characters=self.target_characters,
            clear_button_position=(706, 601),  # 清空按钮坐标
        )

    def continuous_screenshot_test(self, nemu_ipc, duration=10):
        """
        持续截图性能测试

        Args:
            nemu_ipc: NemuIpcImpl 实例
            duration: 持续时间（秒）
        """
        logger.hr("Continuous Screenshot Test with NemuIpc", level=1)
        logger.info(f"将持续截图 {duration} 秒")

        start_time = time.time()
        screenshot_count = 0

        while time.time() - start_time < duration:
            try:
                # 使用 NemuIpc 直接截图
                image = nemu_ipc.screenshot()
                screenshot_count += 1
                
                # 每50次截图输出一次统计
                if screenshot_count % 50 == 0:
                    elapsed = time.time() - start_time
                    fps = screenshot_count / elapsed
                    logger.info(f"已截图 {screenshot_count} 次 | 平均帧率: {fps:.2f} FPS")
                
                time.sleep(0.01)  # 10ms 间隔
            except Exception as e:
                logger.error(f"截图失败: {e}")
                break

        elapsed = time.time() - start_time
        logger.info(f"截图测试完成，共截图 {screenshot_count} 次")
        logger.info(f"平均帧率: {screenshot_count / elapsed:.2f} FPS")

    def handle_train_interaction(self):
        """
        处理训练场界面交互流程
        """
        logger.hr("Handle train interaction", level=1)

        confirm_timer = Timer(1.5, count=4).start()
        interaction_success = False

        # 清空记录
        self.device.stuck_record_clear()
        self.device.click_record_clear()

        while 1:
            self.device.screenshot()

            if self._is_interaction_complete():
                if confirm_timer.reached():
                    logger.info("Train interaction completed")
                    break
            else:
                confirm_timer.reset()

            # 检测是否开启无敌
            if self.appear(SETTINGS, interval=5, offset=(30, 30)):
                logger.info("SETTINGS button detected - clicking")
                self.device.click(SETTINGS)
                continue

            # 检测并处理 CHANGE 按钮
            if self.appear(CHANGE, interval=5, offset=(30, 30)):
                logger.info("CHANGE button detected - clicking")
                self.device.click(CHANGE)
                if not interaction_success:
                    logger.info("Interaction success - button clicked")
                    interaction_success = True
                continue

            self.device.click_adb(922, 278)

        return True

    def _is_interaction_complete(self) -> bool:
        """
        检查训练场交互是否完成

        Returns:
            bool: 是否完成交互
        """
        return self.appear(CANCEL, offset=(30, 30))


def main():
    """
    主测试函数
    """
    # 创建配置
    config = PriconneConfig("maple", "Pcr")
    
    logger.info(f"截图方式: {config.Emulator_ScreenshotMethod}")
    logger.info(f"控制方式: {config.Emulator_ControlMethod}")
    
    device = Device(config)
    # 禁用卡死检测
    device.disable_stuck_detection()
    
    # 实例化测试类
    test = NemuIpcSelectorTest(config=config, device=device)

    # 初始化 NemuIpc（参考 test_battle_train.py）
    logger.hr("Initialize NemuIpc", level=0)
    from module.device.method.nemu_ipc import NemuIpcImpl
    
    # 自动检测 MuMu 路径
    import os
    nemu_folder = None
    search_paths = [
        r"C:\Program Files\Netease\MuMu Player 12",
        r"C:\Program Files\Netease\MuMuPlayer-12.0",
        r"D:\Program Files\Netease\MuMu Player 12",
        r"D:\Program Files\Netease\MuMuPlayer-12.0",
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            nemu_folder = path
            logger.info(f"找到 MuMu12 安装路径: {nemu_folder}")
            break
    
    if not nemu_folder:
        logger.error("未找到 MuMu12 安装路径")
        sys.exit(1)
    
    # 创建 NemuIpc 实例
    nemu = NemuIpcImpl(nemu_folder, instance_id=0)
    nemu.connect()
    logger.info("✓ NemuIpc 连接成功")

    # 测试1: 持续截图性能测试
    logger.hr("Test 1: Screenshot Performance", level=0)
    test.continuous_screenshot_test(nemu, duration=5)

    # 测试2: 导航到训练场
    logger.hr("Test 2: Navigate to Train Page", level=0)
    test.ui_ensure(page_train)
    logger.info("成功进入训练场！")

    # 测试3: 处理训练场界面交互
    logger.hr("Test 3: Train Interaction", level=0)
    test.handle_train_interaction()
    logger.info("训练场交互处理完成！")

    # 测试4: 角色选择（使用常规截图方法）
    logger.hr("Test 4: Character Selection", level=0)
    changed = test.character_selector.ensure_characters_selected()

    if changed:
        logger.info("✓ 角色选择已完成（进行了重选）")
    else:
        logger.info("✓ 角色选择已跳过（已正确）")

    # 测试5: 开始战斗
    logger.hr("Test 5: Start Battle", level=0)
    test.combat_preparation_with_ui_click()

    # 清理
    nemu.disconnect()
    logger.hr("All Tests Completed", level=0)


if __name__ == "__main__":
    main()
