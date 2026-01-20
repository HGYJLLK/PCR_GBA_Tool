import sys

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.base.timer import Timer
from module.base.template import Template
from module.base.mask import Mask
from module.logger import logger
from module.ui.ui import UI
from module.ui.page import page_train
from module.ui.scroll import Scroll
from module.train.assets import *
from module.character.assets import *


class TemplateMatchTest(UI):

    def __init__(self, config, device=None):
        """
        Args:
            config: 配置对象
            device: 设备对象
        """
        super().__init__(config, device)

    def test_match(self):
        count = 0
        while count < 10:
            count += 1
            self.device.screenshot()
            # if self.appear(
            #     NULL_FIVE, interval=5, threshold=30, offset=(20, 20), similarity=0.75
            # ):
            if self.appear(NULL_FIVE, threshold=30, similarity=0.75):
                logger.info("NULL_FIVE button appear")
                self.device.click(NULL_FIVE)
            logger.info(f"Loop {count}")

    def test_select_characters_with_mask(self):
        """
        实战测试：滚动列表选择5个角色
        """
        logger.hr("实战测试：滚动列表选择5个角色", level=1)

        # ==================== 初始化滚动控制 ====================
        scroll = Scroll(
            area=DOCK_SCROLL.area,
            color=(102, 149, 224),
            name="CHARACTER_SCROLL",
            swipe_area=(781, 200, 781, 385),
        )

        # ==================== 定义遮罩 ====================
        try:
            MASK_CHARACTER_LIST = Mask(file="./assets/mask/MASK_CHARACTER_LIST.png")
            use_mask = True
            logger.info("遮罩加载成功")
        except:
            use_mask = False
            logger.warning("遮罩文件不存在，跳过遮罩应用（占位符测试）")

        # ==================== 定义目标角色模板 ====================
        target_templates = {
            "CHUNJIAN": TEMPLATE_CHUNJIAN,
            "QINGBING": TEMPLATE_QINGBING,
            "SHUIMA": TEMPLATE_SHUIMA,
            "TIANJIE": TEMPLATE_TIANJIE,
            "SHUISHENGMU": TEMPLATE_SHUISHENGMU,
        }

        logger.info(f"目标角色: {len(target_templates)} 个")
        for name in target_templates.keys():
            logger.info(f"  - {name}")

        # ==================== 清空记录 ====================
        self.device.stuck_record_clear()
        self.device.click_record_clear()

        selected_names = set()  # 已选中的角色名称
        selected_count = 0

        # ==================== 滚动到底部（起始位置）====================
        logger.hr("滚动到底部（起始位置）", level=2)
        scroll.set_bottom(main=self, skip_first_screenshot=False)
        self.device.sleep(1)

        if scroll.at_bottom(main=self):
            logger.info("成功滚动到底部")

        # ==================== 逐页搜索角色 ====================
        logger.hr("开始逐页搜索角色", level=2)
        swipe_count = 0

        while selected_count < 5:
            swipe_count += 1
            logger.hr(f"搜索第 {swipe_count} 页", level=3)
            logger.info(f"已选: {selected_count}/5")

            # 获取截图
            self.device.screenshot()
            image = self.device.image

            # 应用遮罩
            if use_mask:
                image = MASK_CHARACTER_LIST.apply(image)
                logger.info("遮罩应用成功")

            # 一次性检测所有目标角色
            all_matches = []

            for char_name, template in target_templates.items():
                # 跳过已选中的角色
                if char_name in selected_names:
                    continue

                try:
                    sim, button = template.match_result(image, name=char_name)
                    #  检查相似度阈值
                    if sim >= 0.85:
                        logger.info(f" 找到 {char_name}: 相似度 {sim:.3f}")
                        all_matches.append((char_name, button))
                    else:
                        logger.debug(f" {char_name} 相似度不足: {sim:.3f} < 0.85")

                except Exception as e:
                    logger.error(f"匹配 {char_name} 出错: {e}")

            # 批量点击
            logger.info(f"本页找到: {len(all_matches)} 个匹配")

            for char_name, button in all_matches:
                # 检查是否已选满
                if selected_count >= 5:
                    logger.info("5 个角色已选满！")
                    break

                # 跳过已选中的角色（防止重复）
                if char_name in selected_names:
                    continue

                # 点击角色
                logger.info(f"点击 {char_name} at {button.button}")
                self.device.click(button, control_check=False)
                self.device.sleep((0.5, 0.8))  # 随机延迟

                # 标记已选中
                selected_names.add(char_name)
                selected_count += 1
                logger.info(f"   已选 {selected_count}/5")

            # 检查是否完成
            if selected_count >= 5:
                logger.info("已选满 5 个角色，完成！")
                break

            # 检查是否到达顶部
            if scroll.at_top(main=self):
                logger.warning("已到达列表顶部")
                if selected_count < 5:
                    logger.warning(f"仅找到 {selected_count}/5 个角色")
                break

            # 向上翻页继续搜索
            logger.info("向上翻页...")
            scroll.next_page(main=self, skip_first_screenshot=False)
            self.device.sleep(0.8)

        # ==================== 结果统计 ====================
        logger.hr("角色选择完成", level=1)
        logger.info(f"成功选择: {selected_count}/5 个角色")

        if selected_names:
            logger.info("已选角色:")
            for i, name in enumerate(selected_names, 1):
                logger.info(f"  {i}. {name}")

        not_selected = set(target_templates.keys()) - selected_names
        if not_selected:
            logger.warning(f"未找到的角色 ({len(not_selected)} 个):")
            for name in not_selected:
                logger.warning(f"  - {name}")

        # ==================== 架构说明 ====================
        logger.hr("架构核心特性", level=2)
        logger.info("  1. Mask.apply() - 遮罩过滤 UI 元素")
        logger.info("  2. match_multi() - 一次性检测 + 自动聚类")
        logger.info("  3. 数量限制 - 防止误识别（matches[:3]）")
        logger.info("  4. control_check=False - 禁用点击检查")
        logger.info("  5. 随机延迟 - (0.5, 0.8) 秒")
        logger.info("  6. 集合跟踪 - 避免重复选择")

        return selected_count >= 5


def main():
    """
    主测试函数
    """
    config = PriconneConfig("maple", "Pcr")
    device = Device(config)
    # 禁用卡死检测
    device.disable_stuck_detection()
    # 实例化测试类
    test = TemplateMatchTest(config=config, device=device)

    # 选择要运行的测试
    import sys

    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "characters":
            logger.info("运行测试：实战 - 滚动列表选择角色")
            test.test_select_characters_with_mask()
        elif test_name == "basic":
            logger.info("运行测试：基础模板匹配")
            test.test_match()
        else:
            logger.error(f"未知测试: {test_name}")
            logger.info("可用测试: basic, mask, advanced, characters")
    else:
        # 默认运行基础测试
        logger.info("运行测试：基础模板匹配（默认）")
        logger.info("提示：使用参数指定测试类型")
        logger.info("  python tests/test_template_match.py basic      - 基础测试")
        logger.info("  python tests/test_template_match.py characters - 实战：选择角色")
        test.test_match()


if __name__ == "__main__":
    main()
