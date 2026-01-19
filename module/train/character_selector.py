"""
角色选择模块
"""

from module.logger import logger
from module.base.timer import Timer
from module.ui.scroll import Scroll
from module.base.mask import Mask
import numpy as np
import cv2
from module.train.assets import *
from module.character.assets import *


class CharacterSelector:
    """
    角色选择器
    """

    # 相似度阈值
    SIMILARITY_THRESHOLD = 0.85

    def __init__(self, main, target_characters, clear_button_position=(706, 601)):
        """
        Args:
            main: UI 主类实例（用于 screenshot、click 等）
            target_characters: dict, {角色名: Template对象}
            clear_button_position: tuple, 清空按钮的坐标
        """
        self.main = main
        self.target_characters = (
            target_characters  # {'CHUNJIAN': TEMPLATE_CHUNJIAN, ...}
        )
        self.target_characters_null = {
            "NULL_ONE": NULL_ONE,
            "NULL_TWO": NULL_TWO,
            "NULL_THREE": NULL_THREE,
            "NULL_FOUR": NULL_FOUR,
            "NULL_FIVE": NULL_FIVE,
        }
        self.clear_position = clear_button_position

        # 初始化滚动控制
        self.scroll = Scroll(
            area=DOCK_SCROLL.area,
            color=(102, 149, 224),
            name="CHARACTER_SCROLL",
            swipe_area=(781, 200, 781, 385),
        )

        # 加载遮罩
        try:
            self.mask_list = Mask(file="./assets/mask/MASK_CHARACTER_LIST.png")
            self.use_mask = True
            logger.info("角色列表遮罩加载成功")
        except:
            self.use_mask = False
            logger.warning("遮罩文件不存在，跳过遮罩")

        # 加载已选区域遮罩
        try:
            self.mask_selected = Mask(file="./assets/mask/MASK_CHARACTER_RESULT.png")
            self.use_selected_mask = True
            logger.info("已选区域遮罩加载成功")
        except:
            self.use_selected_mask = False
            logger.warning("已选区域遮罩不存在")

    def _get_selected_area_image(self):
        """
        获取已选角色区域的截图

        Returns:
            np.ndarray: 已选区域的图像
        """
        image = self.main.device.image
        image = self.mask_selected.apply(image)
        return image

    def _verify_selected_characters(self):
        """
        验证已选的5个角色是否正确

        Returns:
            bool: True表示5个角色都正确，False表示需要重选
        """
        logger.hr("验证已选角色", level=2)

        # 获取已选区域的截图
        self.main.device.screenshot()
        selected_image = self._get_selected_area_image()

        matched_count = 0
        matched_names = []

        # 逐个验证目标角色
        for char_name, template in self.target_characters.items():
            try:
                # 在已选区域进行模板匹配
                sim, button = template.match_result(selected_image)

                if sim >= self.SIMILARITY_THRESHOLD:
                    logger.info(f" {char_name} 已正确选择 (相似度: {sim:.3f})")
                    matched_count += 1
                    matched_names.append(char_name)
                else:
                    logger.info(f" {char_name} 未找到或不正确 (相似度: {sim:.3f})")

            except Exception as e:
                logger.warning(f"验证 {char_name} 时出错: {e}")

        # 判断是否全部正确
        is_correct = matched_count == len(self.target_characters)

        if is_correct:
            logger.info(
                f" 已选角色验证通过 ({matched_count}/{len(self.target_characters)})"
            )
        else:
            logger.info(
                f" 已选角色不完整 ({matched_count}/{len(self.target_characters)})"
            )
            logger.info(f"   已匹配: {matched_names}")

        return is_correct

    def _has_selected_characters(self):
        """
        检查是否有已选角色

        Returns:
            bool: True表示有角色被选中，False表示已清空
        """
        # 检查是否有角色在已选区域
        try:
            if not self.main.appear(NULL_ONE, threshold=30, similarity=0.75):
                return True  # 找到了角色
        except:
            pass
        return False

    def _clear_selected_characters(self, skip_first_screenshot=True):
        """
        清空已选角色

        Args:
            skip_first_screenshot (bool): 是否跳过第一次截图
        """
        logger.hr("清空已选角色", level=2)

        click_timer = Timer(1)  # 1秒间隔
        confirm_timer = Timer(2).start()  # 无角色状态持续2秒 -> 确认清空

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.main.device.screenshot()

            has_chars = self._has_selected_characters()
            # 终止条件：没有已选角色
            if not has_chars:
                if confirm_timer.reached():
                    logger.info(" 已选角色已清空")
                    break
            else:
                confirm_timer.reset()

            if has_chars and click_timer.reached():
                self.main.device.click_adb(*self.clear_position)
                click_timer.reset()

            self.main.device.sleep(0.3)

    def _select_characters_from_list(self):
        """
        从列表中选择角色

        Returns:
            bool: 是否成功选择所有角色
        """
        logger.hr("开始从列表选择角色", level=2)

        # 清空记录
        self.main.device.stuck_record_clear()
        self.main.device.click_record_clear()

        selected_names = set()
        selected_count = 0

        # 滚动到底部
        logger.info("滚动到底部")
        self.scroll.set_bottom(main=self.main, skip_first_screenshot=False)
        self.main.device.sleep(1)

        # 逐页搜索
        swipe_count = 0
        while selected_count < len(self.target_characters):
            swipe_count += 1
            logger.info(
                f"搜索第 {swipe_count} 页 (已选: {selected_count}/{len(self.target_characters)})"
            )

            # 获取截图并应用遮罩
            self.main.device.screenshot()
            image = self.main.device.image

            if self.use_mask:
                image = self.mask_list.apply(image)

            # 一次性检测所有目标角色
            all_matches = []

            for char_name, template in self.target_characters.items():
                if char_name in selected_names:
                    continue

                try:
                    sim, button = template.match_result(image, name=char_name)
                    if sim >= self.SIMILARITY_THRESHOLD:
                        logger.info(f"找到 {char_name}: 相似度 {sim:.3f}")
                        all_matches.append((char_name, button))
                except Exception as e:
                    logger.error(f"匹配 {char_name} 出错: {e}")

            # 批量点击
            for char_name, button in all_matches:
                if selected_count >= len(self.target_characters):
                    break

                if char_name in selected_names:
                    continue

                logger.info(f"点击 {char_name} at {button.button}")
                self.main.device.click(button, control_check=False)
                self.main.device.sleep((0.5, 0.8))

                selected_names.add(char_name)
                selected_count += 1
                logger.info(f"已选 {selected_count}/{len(self.target_characters)}")

            # 检查是否完成
            if selected_count >= len(self.target_characters):
                logger.info("所有角色已选择完成！")
                break

            # 检查是否到达顶部
            if self.scroll.at_top(main=self.main):
                logger.warning("已到达列表顶部")
                if selected_count < len(self.target_characters):
                    logger.warning(
                        f"仅找到 {selected_count}/{len(self.target_characters)} 个角色"
                    )
                break

            # 向上翻页
            logger.info("向上翻页...")
            self.scroll.next_page(main=self.main, skip_first_screenshot=False)
            self.main.device.sleep(0.8)

        return selected_count == len(self.target_characters)

    def ensure_characters_selected(self, skip_first_screenshot=True):
        """
        Args:
            skip_first_screenshot (bool): 是否跳过第一次截图

        Returns:
            bool: True表示进行了重选，False表示已正确无需操作
        """
        logger.hr("角色已正确选择", level=1)

        # 确认定时器
        confirm_timer = Timer(1.5, count=3).start()

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.main.device.screenshot()

            # 达到确认时间后进行验证
            if confirm_timer.reached():
                break

            self.main.device.sleep(0.3)

        # ==================== 验证 ====================
        is_correct = self._verify_selected_characters()

        # ==================== 跳过或重选 ====================
        if is_correct:
            logger.info(" 角色已正确选择，跳过选择流程")
            return False  # 未改变
        else:
            logger.info(" 角色不正确，开始重新选择")

            # 清空
            self._clear_selected_characters()

            # 重选
            success = self._select_characters_from_list()

            if success:
                logger.info(" 角色重选完成")
                return True  # 已改变
            else:
                logger.warning(" 角色重选失败")
                return True  # 已尝试改变
