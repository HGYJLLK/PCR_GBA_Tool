"""训练场相关功能"""
from airtest.core.api import exists, touch
import time
from utils.logger import logger
from core.game.base import GameBase
from templates import XLC_ICON

class TrainingOperation(GameBase):
    def enter_training_area(self):
        """进入训练场"""
        retry_count = 0
        while retry_count < 15:
            if exists(XLC_ICON):
                pos = exists(XLC_ICON)
                logger.info(f"找到训练场图标，坐标：{pos}")
                touch(pos)
                time.sleep(1)
                if not exists(XLC_ICON):
                    logger.info("进入训练场成功")
                    break
            else:
                logger.info("未找到训练场图标，点击固定位置")
                touch((1166, 698))
                time.sleep(2)
            retry_count += 1