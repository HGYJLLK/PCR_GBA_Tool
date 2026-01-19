"""
UI 页面导航系统
"""

import traceback


class Page:
    """
    UI导航系统
    """

    # Key: str, page name like "page_main"
    # Value: Page, page instance
    all_pages = {}

    @classmethod
    def clear_connection(cls):
        """清空所有页面的 parent 连接"""
        for page in cls.all_pages.values():
            page.parent = None

    @classmethod
    def init_connection(cls, destination):
        """
        使用 A* 算法初始化页面间的路径（反向BFS）

        Args:
            destination (Page): 目标页面
        """
        cls.clear_connection()  # 清空旧的导航路线

        visited = [destination]  # 从目的地开始
        visited = set(visited)
        while 1:
            new = visited.copy()
            for page in visited:
                for link in cls.iter_pages():  # 遍历地图上所有节点
                    if link in visited:
                        continue
                    # 判断"link" 能不能“到达” "page"？
                    if page in link.links:
                        # “link”的“下一步” (parent) 就是 "page"
                        link.parent = page
                        new.add(link)
            if len(new) == len(visited):
                break
            visited = new

    @classmethod
    def iter_pages(cls):
        """遍历所有已注册的页面"""
        return cls.all_pages.values()

    @classmethod
    def iter_check_buttons(cls):
        """遍历所有页面的检测按钮"""
        for page in cls.all_pages.values():
            yield page.check_button

    def __init__(self, check_button):
        """
        初始化页面

        Args:
            check_button (Button): 用于识别该页面的特征按钮
        """
        self.check_button = check_button  # 用于识别该页面的特征按钮
        self.links = {}  # 存放 check_button所在的页面到其他页面的导航链接
        # 自动获取变量名作为页面名称
        (filename, line_number, function_name, text) = traceback.extract_stack()[-2]
        self.name = text[: text.find("=")].strip()
        self.parent = None
        # 注册到全局页面表
        Page.all_pages[self.name] = self

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def link(self, button, destination):
        """
        定义到其他页面的导航链接

        Args:
            button (Button): 点击此按钮可到达目标页面
            destination (Page): 目标页面
        """
        self.links[destination] = button


"""
定义 PCR 的 UI 页面
"""

# 导入按钮定义
from module.ui.assets import *


page_adventure = Page(TEAM_BATTLE)
page_main = Page(MAIN_CHECK)

# 公会战
page_team_battle = Page(TEAM_BATTLE_CHECK)
page_team_battle.link(button=GO_TO_MAIN, destination=page_main)

# 冒险模式
page_adventure.link(button=GO_TO_MAIN, destination=page_main)
page_adventure.link(button=TEAM_BATTLE, destination=page_team_battle)

# 训练场
page_train = Page(TRAIN_CHECK)
page_train.link(button=GO_TO_MAIN, destination=page_main)
page_train.link(button=ADVENTURE, destination=page_adventure)

# 菜单界面
page_menu = Page(MENU_CHECK)
page_menu.link(button=GO_TO_MAIN, destination=page_main)
page_menu.link(button=ADVENTURE, destination=page_adventure)
page_menu.link(button=MENU_CHECK, destination=page_train)

# 主界面
page_main.link(button=ADVENTURE, destination=page_adventure)
page_main.link(button=GO_TO_MENU, destination=page_menu)

# Unknown page
page_unknown = Page(None)
page_unknown.link(button=GO_TO_MAIN, destination=page_main)
