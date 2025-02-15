'''竞技场相关功能'''
import logging
from pathlib import Path
from airtest.core.api import Template, touch, exists

logger = logging.getLogger(__name__)

class GoToJJCBox:
    def __init__(self, device):
        """
        初始化导航到竞技场的功能类

        Args:
            device: ATX/uiautomator2 设备实例
        """
        self.device = device

        # 设置图标模板路径
        self.button_path = Path("static/images/button")
        self.templates = {
            "main_menu_icon": Template(str(self.button_path / "主菜单.png")),
            "my_home_select_icon": Template(str(self.button_path / "我的主页_select.png")),
            "adventure_icon": Template(str(self.button_path / "冒险.png")),
            "battle_arena_icon": Template(str(self.button_path / "战斗竞技场.png")),
            "defense_setting_icon": Template(str(self.button_path / "防守设定.png")),
        }

    def detect_icon(self, icon_template: Template) -> bool:
        """
        检测屏幕上是否存在指定图标

        Args:
            icon_template: 要检测的图标模板

        Returns:
            bool: 是否检测到图标
        """
        try:
            result = exists(icon_template)
            if result:
                logger.info(f"检测到图标: {icon_template}")
                return True
            else:
                logger.info(f"未检测到图标: {icon_template}")
                return False
        except Exception as e:
            logger.error(f"检测图标失败: {e}")
            return False

    def click_icon(self, icon_template: Template):
        """
        点击指定的图标

        Args:
            icon_template: 要点击的图标模板
        """
        try:
            if self.detect_icon(icon_template):
                touch(icon_template)
                logger.info(f"成功点击图标: {icon_template}")
            else:
                logger.warning(f"未检测到图标，无法点击: {icon_template}")
        except Exception as e:
            logger.error(f"点击图标失败: {e}")

    def navigate(self):
        """
        导航到竞技场相关页面
        """
        logger.info("开始导航到竞技场...")

        # 检测是否在主页面
        if not self.detect_icon(self.templates["main_menu_icon"]):
            logger.error("未检测到主菜单图标，无法继续操作")
            return
        logger.info("检测到主菜单图标，确认在主页面")

        # 检测是否是“我的主页”状态
        if self.detect_icon(self.templates["my_home_select_icon"]):
            logger.info("当前已经是“我的主页”状态")
        else:
            logger.info("未检测到“我的主页”状态，直接导航")

        # 点击冒险图标
        self.click_icon(self.templates["adventure_icon"])

        # 点击战斗竞技场图标
        self.click_icon(self.templates["battle_arena_icon"])

        # 点击防守设定图标
        self.click_icon(self.templates["defense_setting_icon"])

        logger.info("导航到竞技场完成")


def run_goto_jjc_box(device):
    """
    执行导航到竞技场功能

    Args:
        device: ATX/uiautomator2 设备实例
    """
    try:
        navigator = GoToJJCBox(device)
        navigator.navigate()
    except Exception as e:
        logger.error(f"导航操作失败: {e}")


if __name__ == "__main__":
    # 这里需要传入实际的device实例
    run_goto_jjc_box(None)
