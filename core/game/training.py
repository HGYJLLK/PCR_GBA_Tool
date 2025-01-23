"""训练场相关功能"""
from airtest.core.api import exists, touch, Template
import time
from utils.logger import logger
from core.game.base import GameBase


class GameTemplates:
    @property
    def training_icon(self):
        return Template(r"static/images/button/大家的训练场.png")


class TrainingOperation(GameBase):
    def __init__(self):
        super().__init__()
        self.templates = GameTemplates()

    def enter_training_area(self):
        """进入训练场"""
        retry_count = 0
        while retry_count < 15:
            if exists(self.templates.training_icon):
                pos = exists(self.templates.training_icon)
                logger.info(f"找到训练场图标，坐标：{pos}")
                touch(pos)
                time.sleep(1)

                # 检查是否成功进入（图标不再存在）
                if not exists(self.templates.training_icon):
                    logger.info("进入训练场成功")
                    break
            else:
                logger.info("未找到训练场图标，点击固定位置")
                touch((1166, 698))
                time.sleep(2)

            retry_count += 1
