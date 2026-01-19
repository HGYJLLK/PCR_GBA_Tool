import sys

sys.path.insert(0, "./")

from module.config.config import PriconneConfig
from module.device.device import Device
from module.character.assets import *
from module.ui.scroll import Scroll
from module.base.button import ButtonGrid
from module.base.base import ModuleBase
from module.logger import logger
from module.ui.ui import UI
from module.ui.page import *
from module.ui.assets import *


def main():
    config = PriconneConfig("cwj", "Pcr")
    device = Device(config)
    # 禁用卡死检测
    device.disable_stuck_detection()
    # 实例化 UI 类
    ui = UI(config=config, device=device)

    # 从任意位置 → 公会战
    ui.ui_ensure(page_team_battle)  # 自动：main → adventure → team_battle

    logger.info(" 成功进入公会战！")


if __name__ == "__main__":
    main()
