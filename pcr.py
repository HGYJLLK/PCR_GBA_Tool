from datetime import datetime
import time
import sys
import os

from module.logger import logger, show
from module.exception import *
from module.config.config import PriconneConfig
from module.base.decorator import cached_property, del_cached_property


class PCRGBATool:
    """
    PCR 自动化工具类
    """

    def __init__(self, config_name="maple"):
        """
        初始化 PCR

        Args:
            config_name: 配置文件名,默认为 "maple"
        """
        logger.hr("Start", level=0)
        self.config_name = config_name
        self.is_first_task = True

    @cached_property  # 检查是否被加载过，即按需懒加载
    def config(self):
        """
        延迟初始化配置对象
        """
        try:
            config = PriconneConfig(config_name=self.config_name)
            return config
        except RequestHumanTakeover:
            logger.critical("Request human takeover")
            exit(1)
        except Exception as e:
            logger.exception(e)
            exit(1)

    @cached_property
    def device(self):
        """
        延迟初始化设备对象
        """
        try:
            from module.device.device import Device

            device = Device(config=self.config)
            return device
        except RequestHumanTakeover:
            logger.critical("Request human takeover")
            exit(1)
        except Exception as e:
            logger.exception(e)
            exit(1)

    def start_log(self):
        """启动日志"""
        logger.hr("PCR-GBA-Tool", level=1)
        logger.info(f"配置文件：{self.config.config_name}.json")
        logger.info(f"截图方式：{self.config.Emulator_ScreenshotMethod}")
        logger.info(f"点击方式：{self.config.Emulator_ControlMethod}")

    def run(self, command):
        """
        所有任务的调度中心

        Args:
            command: 任务名称

        Returns:
            bool: 任务是否成功执行
        """
        try:
            # 执行任务，根据字符串"command"，调用同名的方法
            self.__getattribute__(command)()
            return True  # 任务正常结束
        except TaskEnd:
            # 任务正常结束
            return True
        # 捕获游戏运行中的"可恢复"错误
        except GameNotRunningError as e:
            logger.warning(e)
            logger.warning("Game not running, will restart")
            return False  # # 返回 False，loop 启动失败
        except (GameStuckError, GameTooManyClickError) as e:
            logger.error(e)
            logger.warning(f"Game stuck, will be restarted in 10 seconds")
            logger.warning("If you are playing by hand, please stop the script")
            self.device.sleep(10)
            return False
        except RequestHumanTakeover:
            logger.critical("Request human takeover")
            exit(1)
        except Exception as e:
            logger.exception(e)
            logger.critical("Unexpected error occurred")
            exit(1)

    def start(self):
        """
        启动游戏并进入主界面
        """
        from module.handler.login import LoginHandler

        LoginHandler(self.config, device=self.device).app_start()

    def restart(self):
        """
        重启游戏
        """
        from module.handler.login import LoginHandler

        LoginHandler(self.config, device=self.device).app_restart()

    def loop(self):
        """
        主循环入口
        """
        self.start_log()

        logger.hr("正在启动 PCR", level=1)

        try:
            # 初始化设备
            _ = self.device
            self.device.config = self.config

            # 执行启动任务
            logger.info("Scheduler: Start task `Start`")
            logger.hr("Start", level=0)
            success = self.run("start")
            logger.info("Scheduler: End task `Start`")

            if success:
                logger.hr("PCR 启动完成", level=1)
                return 0
            else:
                logger.error("PCR 启动失败")
                return 1

        except RequestHumanTakeover as e:
            logger.critical(f"需要人工介入: {e}")
            return 1
        except EmulatorNotRunningError as e:
            logger.critical(f"模拟器错误: {e}")
            return 1
        except Exception as e:
            logger.exception(e)
            return 1


if __name__ == "__main__":
    pcr = PCRGBATool()
    sys.exit(pcr.loop())  # 0 成功，1 失败
