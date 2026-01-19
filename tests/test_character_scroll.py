"""
================================================================================
角色列表滚动测试工具
================================================================================

    python dev_tools/character_scroll.py

================================================================================
"""

import sys

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.character.assets import *
from module.ui.scroll import Scroll
from module.base.button import ButtonGrid
from module.base.base import ModuleBase
from module.logger import logger


def scroll_detection():
    """
    滚动条检测
    """
    logger.hr("Scroll Detection", level=0)

    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)

    # 禁用卡死检测
    device.disable_stuck_detection()

    # 创建 ModuleBase 实例
    module = ModuleBase(config=config, device=device)

    # 创建 Scroll 对象
    scroll = Scroll(
        area=DOCK_SCROLL.area,  # 整个滚动条轨道 (1218, 174, 1230, 484)
        color=(102, 149, 224),  # 滑块颜色 (102, 149, 224)
        name="CHARACTER_SCROLL",
        swipe_area=(1204, 220, 1213, 480),  # 列表滑动区域
    )

    print("\n请进入角色列表界面")
    input("按回车开始...\n")

    # 截图
    module.device.screenshot()

    # 保存完整截图
    import cv2

    cv2.imwrite(
        "debug_full_screenshot.png",
        cv2.cvtColor(module.device.image, cv2.COLOR_RGB2BGR),
    )
    logger.info("完整截图已保存到: debug_full_screenshot.png")

    # 保存滚动条区域截图
    scroll_image = module.image_crop(DOCK_SCROLL.area, copy=True)
    cv2.imwrite("debug_scroll_area.png", cv2.cvtColor(scroll_image, cv2.COLOR_RGB2BGR))
    logger.info(f"滚动条区域截图已保存到: debug_scroll_area.png")
    logger.info(f"  区域: {DOCK_SCROLL.area}")
    logger.info(f"  大小: {scroll_image.shape[:2][::-1]} (宽x高)")
    logger.info(f"  配置颜色: {DOCK_SCROLL.color}")

    # 滚动条检测
    logger.hr("开始检测滚动条", level=1)
    mask = scroll.match_color(main=module)
    logger.info(f"滚动条长度: {scroll.length} 像素")
    logger.info(f"总长度: {scroll.total} 像素")
    logger.info(f"匹配行数: {mask.sum()} / {len(mask)}")

    if scroll.appear(main=module):
        logger.info(" 滚动条检测成功")
        position = scroll.cal_position(main=module)
        logger.info(f"  当前位置: {position:.2f}")

        # 边界
        if scroll.at_top(main=module):
            logger.info("  当前在顶部")
        elif scroll.at_bottom(main=module):
            logger.info("  当前在底部")
        else:
            logger.info("  当前在中间位置")

    else:
        logger.error(" 滚动条检测失败！")
        logger.warning("可能原因:")
        logger.warning("  1. 滚动条区域坐标不正确")
        logger.warning("  2. 滚动条颜色不匹配")
        logger.warning("  3. 未进入角色列表界面")
        logger.warning("\n请检查:")
        logger.warning("  - debug_full_screenshot.png (完整截图)")
        logger.warning("  - debug_scroll_area.png (滚动条区域)")
        logger.warning(f"  - 滚动条应该在坐标 {DOCK_SCROLL.area}")


def scroll_control():
    """
    滚动控制
    """
    logger.hr("Scroll Control", level=0)

    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)

    # 禁用卡死检测
    device.disable_stuck_detection()

    # 创建 ModuleBase 实例
    module = ModuleBase(config=config, device=device)

    scroll = Scroll(
        area=DOCK_SCROLL.area,  # 整个滚动条轨道
        color=(102, 149, 224),  # 滑块颜色
        name="CHARACTER_SCROLL",
        swipe_area=(781, 200, 781, 385),  # 列表区域滑动
    )

    print("\n滚动操作:")
    print("  滚动到底部")
    print("  向上翻页")
    print("  滚动到顶部")
    input("\n按回车开始测试...\n")

    # 滚动到底部
    logger.info("滚动到底部")
    scroll.set_bottom(main=module, skip_first_screenshot=False)
    module.device.sleep(5)

    if scroll.at_bottom(main=module):
        logger.info(" 成功滚动到底部")
    else:
        logger.warning(" 滚动到底部失败")

    # 翻页
    for i in range(20):
        scroll.next_page(main=module, skip_first_screenshot=False)
        module.device.sleep(5)
        logger.info(f"  第 {i+1} 页完成")

    if scroll.at_top(main=module):
        logger.info(" 成功滚动到顶部")
    else:
        logger.warning(" 滚动到顶部失败")


# def grid_positions():
#     """
#     网格位置识别
#     """
#     logger.hr("Grid Positions", level=0)

#     grids = ButtonGrid(
#         origin=(84, 213),  # 左上角第一个卡片坐标
#         delta=(141, 146),  # 卡片间距
#         button_shape=(119, 116),  # 卡片大小
#         grid_shape=(8, 2),  # 8列2行
#         name="CHARACTER_CARD",
#     )

#     logger.info(f"网格配置:")
#     logger.info(f"  origin: {grids.origin}")
#     logger.info(f"  delta: {grids.delta}")
#     logger.info(f"  button_shape: {grids.button_shape}")
#     logger.info(f"  grid_shape: {grids.grid_shape}")

#     logger.info(f"\n所有网格位置:")
#     for x, y, button in grids.generate():
#         logger.info(f"  Grid({x},{y}): {button.area}")

#     # 可视化掩码
#     logger.info("\n生成可视化掩码图...")
#     grids.save_mask()
#     logger.info(" 掩码已保存到: CHARACTER_CARD.png")
#     logger.info("  请检查掩码图像是否与游戏界面匹配")


def template_matching():
    """
    全屏模板匹配
    """
    logger.hr("Template Matching (Fullscreen)", level=0)

    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)
    device.disable_stuck_detection()

    # 创建 ModuleBase 实例
    module = ModuleBase(config=config, device=device)

    similarity_threshold = 0.85
    print("\n请进入角色列表界面，确保目标角色在屏幕上")
    input("按回车开始全屏匹配...\n")

    # 截图
    module.device.screenshot()

    # 保存截图
    import cv2

    cv2.imwrite(
        "debug_fullscreen_match.png",
        cv2.cvtColor(module.device.image, cv2.COLOR_RGB2BGR),
    )
    logger.info("截图已保存: debug_fullscreen_match.png")

    # ========== 全屏模板匹配 ==========
    logger.hr("开始全屏匹配", level=1)

    try:
        # 彩色匹配
        logger.info("彩色匹配...")
        sim_color, button_color = TEMPLATE_SHUISHENGMU.match_result(module.device.image)
        logger.info(f"  相似度: {sim_color:.4f}")
        if button_color:
            logger.info(f"  匹配位置: {button_color.button}")
            logger.info(f"  匹配区域: {button_color.area}")

        # 亮度匹配
        logger.info("亮度匹配...")
        sim_luma, button_luma = TEMPLATE_SHUISHENGMU.match_luma_result(module.device.image)
        logger.info(f"  相似度: {sim_luma:.4f}")
        if button_luma:
            logger.info(f"  匹配位置: {button_luma.button}")
            logger.info(f"  匹配区域: {button_luma.area}")

        # 选择最佳匹配
        if sim_color > sim_luma:
            max_sim = sim_color
            best_button = button_color
            match_type = "彩色"
        else:
            max_sim = sim_luma
            best_button = button_luma
            match_type = "亮度"

        logger.hr("匹配结果", level=1)
        logger.info(f"最佳匹配类型: {match_type}")
        logger.info(f"最高相似度: {max_sim:.4f}")

        # 判断是否成功
        if max_sim > similarity_threshold:
            logger.info(f" 匹配成功！相似度 {max_sim:.4f} > {similarity_threshold:.2f}")
            logger.info(f"  点击位置: {best_button.button}")
            logger.info(f"  匹配区域: {best_button.area}")

            # 在图片上标记匹配位置
            marked_image = module.device.image.copy()
            area = best_button.area

            # 计算中心点
            center_x = (area[0] + area[2]) // 2
            center_y = (area[1] + area[3]) // 2

            # 画矩形框
            cv2.rectangle(
                marked_image, (area[0], area[1]), (area[2], area[3]), (0, 255, 0), 2
            )
            # 画中心点
            cv2.circle(marked_image, (center_x, center_y), 5, (255, 0, 0), -1)
            # 添加文字
            cv2.putText(
                marked_image,
                f"{max_sim:.3f}",
                (area[0], area[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

            # 保存结果
            output_path = "fullscreen_match_result.png"
            cv2.imwrite(output_path, cv2.cvtColor(marked_image, cv2.COLOR_RGB2BGR))
            logger.info(f"  结果已保存: {output_path}")

            return True
        else:
            logger.error(
                f" 匹配失败！相似度 {max_sim:.4f} <= {similarity_threshold:.2f}"
            )
            logger.warning("可能原因:")
            logger.warning("  1. 目标角色不在当前屏幕")
            logger.warning("  2. 模板图片与实际角色不匹配")
            logger.warning("  3. 角色被其他UI元素遮挡")
            logger.warning("  4. 需要降低相似度阈值")
            return False

    except Exception as e:
        logger.error(f"匹配过程出错: {e}")
        import traceback

        traceback.print_exc()
        return False


def complete_flow():
    logger.hr("Complete Scroll Search Flow", level=0)

    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)
    device.disable_stuck_detection()

    # 创建 ModuleBase 实例
    module = ModuleBase(config=config, device=device)

    # 创建 Scroll 对象
    scroll = Scroll(
        area=DOCK_SCROLL.area,
        color=(102, 149, 224),
        name="CHARACTER_SCROLL",
        swipe_area=(781, 200, 781, 385),
    )

    # 搜索目标
    target_template = TEMPLATE_SHUISHENGMU
    similarity_threshold = 0.85
    max_swipes = 20

    print("\n将执行完整的角色滚动搜索流程:")
    print(f"  目标角色: {target_template.name}")
    print(f"  相似度阈值: {similarity_threshold}")
    print(f"  最大翻页次数: {max_swipes}")
    print("\n流程:")
    print("  1. 滚动到底部")
    print("  2. 在当前页面全屏搜索目标角色")
    print("  3. 如果找到则点击，如果未找到则向上翻页")
    print("  4. 重复步骤 2-3 直到找到或到达顶部")
    print()
    input("请进入角色列表界面，按回车开始...\n")

    # ========== 滚动到底部 ==========
    logger.hr("滚动到底部", level=1)
    scroll.set_bottom(main=module, skip_first_screenshot=False)
    module.device.sleep(1)

    if scroll.at_bottom(main=module):
        logger.info(" 成功滚动到底部")
    else:
        logger.warning(" 可能未完全到达底部，继续执行")

    # ========== 逐页搜索 ==========
    logger.hr("开始逐页搜索", level=1)

    swipe_count = 0
    found = False

    import cv2

    while 1:
        swipe_count += 1
        logger.info(f"搜索第 {swipe_count} 页")

        # 截图
        module.device.screenshot()

        # ========== 全屏模板匹配 ==========
        try:
            # 彩色匹配
            sim_color, button_color = target_template.match_result(module.device.image)
            # 亮度匹配
            sim_luma, button_luma = target_template.match_luma_result(
                module.device.image
            )

            # 选择最佳匹配
            if sim_color > sim_luma:
                max_sim = sim_color
                best_button = button_color
                match_type = "彩色"
            else:
                max_sim = sim_luma
                best_button = button_luma
                match_type = "亮度"

            logger.info(f"  {match_type}匹配相似度: {max_sim:.4f}")

            # ========== 判断是否找到 ==========
            if max_sim > similarity_threshold:
                logger.hr(" 找到目标角色！", level=1)
                logger.info(f"角色: {target_template.name}")
                logger.info(f"相似度: {max_sim:.4f} > {similarity_threshold:.2f}")
                logger.info(f"位置: {best_button.area}")

                # 保存标记图片
                marked_image = module.device.image.copy()
                area = best_button.area
                center_x = (area[0] + area[2]) // 2
                center_y = (area[1] + area[3]) // 2

                cv2.rectangle(
                    marked_image, (area[0], area[1]), (area[2], area[3]), (0, 255, 0), 3
                )
                cv2.circle(marked_image, (center_x, center_y), 8, (255, 0, 0), -1)
                cv2.putText(
                    marked_image,
                    f"Found! {max_sim:.3f}",
                    (area[0], area[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

                output_path = "scroll_search_result.png"
                cv2.imwrite(output_path, cv2.cvtColor(marked_image, cv2.COLOR_RGB2BGR))
                logger.info(f"结果已保存: {output_path}")

                # 点击选择
                logger.info("点击角色...")
                module.device.click(best_button)
                module.device.sleep(0.5)

                found = True
                break

            else:
                logger.info(
                    f"  未找到目标角色（相似度 {max_sim:.4f} <= {similarity_threshold:.2f}）"
                )

        except Exception as e:
            logger.error(f"匹配过程出错: {e}")
            import traceback

            traceback.print_exc()

        # ========== 检查是否到达顶部 ==========
        if scroll.at_top(main=module):
            logger.info("已到达列表顶部")
            break

        # ========== 翻页 ==========
        logger.info("翻页...")
        scroll.next_page(main=module, skip_first_screenshot=False)
        module.device.sleep(0.5)

    # ========== 结果 ==========
    logger.hr("搜索完成", level=0)

    if found:
        logger.info(f" 角色选择成功！")
        logger.info(f"  目标: {target_template.name}")
        logger.info(f"  翻页次数: {swipe_count}")
        return True
    else:
        logger.error(f" 角色选择失败")
        logger.warning("可能原因:")
        logger.warning("  1. 目标角色不在列表中")
        logger.warning("  2. 模板文件与实际角色不匹配")
        logger.warning("  3. 需要增加 max_swipes 翻页次数")
        logger.warning("  4. 需要降低相似度阈值")
        logger.warning("\n建议:")
        logger.warning("  - 运行功能4测试角色在当前页面能否被识别")
        logger.warning("  - 检查滚动条是否工作正常（功能1-2）")
        logger.warning(
            f"  - 当前设置: similarity={similarity_threshold}, max_swipes={max_swipes}"
        )
        return False


def main():
    """主菜单"""
    while True:
        print("\n" + "=" * 60)
        print("角色列表滚动测试工具")
        print("=" * 60)
        print("1. 测试滚动条检测")
        print("2. 测试滚动控制")
        print("3. 测试网格位置")
        print("4. 测试模板匹配")
        print("5. 滚动搜索")
        print("0. 退出")
        print("=" * 60)

        choice = input("\n请选择 (0-6): ").strip()

        if choice == "1":
            scroll_detection()
        elif choice == "2":
            scroll_control()
        # elif choice == "3":
        #     grid_positions()
        elif choice == "4":
            template_matching()
        elif choice == "5":
            complete_flow()
        elif choice == "0":
            print("\n再见！")
            break
        else:
            print("\n无效选择，请重试")

        input("\n按回车继续...")


if __name__ == "__main__":
    main()
