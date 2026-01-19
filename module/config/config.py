#!/usr/bin/env python3
"""
公主连结配置类
"""

import copy
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from module.config.config_generated import GeneratedConfig
from module.config.config_updater import ConfigUpdater
from module.config.deep import deep_get, deep_set
from module.config.utils import filepath_config, dict_to_kv, path_to_arg, DEFAULT_TIME
from module.config.watcher import ConfigWatcher
from module.logger import logger


class TaskEnd(Exception):
    """任务结束异常"""

    pass


class Function:
    """
    任务函数封装，把 json 里的定时任务设置打包成一个对象，供调度器使用
    """

    def __init__(self, data):
        self.enable = deep_get(data, keys="Scheduler.Enable", default=False)
        self.command = deep_get(data, keys="Scheduler.Command", default="Unknown")
        self.next_run = deep_get(data, keys="Scheduler.NextRun", default=DEFAULT_TIME)

    def __str__(self):
        enable = "Enable" if self.enable else "Disable"
        return f"{self.command} ({enable}, {str(self.next_run)})"

    __repr__ = __str__

    def __eq__(self, other):
        if not isinstance(other, Function):
            return False
        return self.command == other.command and self.next_run == other.next_run


def name_to_function(name):
    """
    创建函数对象
    """
    function = Function({})
    function.command = name
    function.enable = True
    return function


class PriconneConfig(ConfigUpdater, GeneratedConfig, ConfigWatcher):
    """
    公主连结配置类
    """

    stop_event: threading.Event = None
    bound = {}

    BUTTON_OFFSET = 30
    WAIT_BEFORE_SAVING_SCREEN_SHOT = 1

    # 截图保存配置
    SCREEN_SHOT_SAVE_INTERVAL = 1  # 截图保存间隔（秒）
    SCREEN_SHOT_SAVE_FOLDER = "./screenshot"  # 截图保存文件夹
    SCREEN_SHOT_SAVE_FOLDER_BASE = "./screenshot"  # 基础截图文件夹

    # DroidCast 配置
    DROIDCAST_VERSION = "DroidCast_raw"
    DROIDCAST_FILEPATH_LOCAL = "./bin/DroidCast/DroidCast_raw-release-1.0.apk"
    DROIDCAST_FILEPATH_REMOTE = "/data/local/tmp/DroidCast_raw.apk"
    FORWARD_PORT_RANGE = (20000, 21000)  # ADB端口转发范围

    # MaaTouch 配置
    MAATOUCH_FILEPATH_LOCAL = "./bin/MaaTouch/maatouchsync"
    MAATOUCH_FILEPATH_REMOTE = "/data/local/tmp/maatouchsync"

    def __setattr__(self, key, value):
        """
        自动保存
        """
        if key in self.bound:
            path = self.bound[key]  # 获取绑定的路径
            self.modified[path] = value  # 记录修改
            if self.auto_update:
                self.update()  # 自动更新配置
        else:
            super().__setattr__(key, value)

    def __init__(self, config_name="template", task=None):
        """
        初始化配置
        """
        print(f"初始化公主连结配置: {config_name}")
        # 读取 ./config/<config_name>.json
        self.config_name = config_name
        # 存放从 .json 读来的完整数据
        self.data = {}
        # 修改的参数记录 Key: 路径, Value: 修改值
        self.modified = {}  # “暂存区”，记录被修改的键值对
        """
        Key: 参数名, Value: 数据路径
        “地图”，记录 属性名 -> .json路径
        作用：写入保存服务
        """
        self.bound = {}
        # 是否自动更新
        self.auto_update = True
        # 强制覆盖的变量
        self.overridden = {}
        # 调度队列
        self.pending_task = []
        self.waiting_task = []
        # 当前任务
        self.task: Function
        # 模板配置标识
        self.is_template_config = config_name.startswith("template")

        if self.is_template_config:
            print("使用模板配置")
            self.auto_update = False
            self.task = name_to_function("template")

        self.init_task(task)

    def init_task(self, task=None):
        """
        初始化任务
        """
        if self.is_template_config:
            return

        self.load()  # 加载配置文件
        if task is None:
            # 默认绑定Pcr任务
            task = name_to_function("Pcr")
        else:
            task = name_to_function(task)

        self.bind(task)  # 绑定配置
        self.task = task
        self.save()

    def load(self):
        """
        加载配置文件，将./config/<config_name>.json读入self.data
        """
        # 使用ConfigUpdater的read_file方法，自动从模板生成配置
        self.data = self.read_file(self.config_name)
        self.config_override()

        for path, value in self.modified.items():
            deep_set(self.data, keys=path, value=value)

    def bind(self, func, func_list=None):
        """
        绑定任务配置
        """
        if isinstance(func, Function):
            func = func.command  # 默认绑定的就是“Pcr” 任务

        # 配置优先级列表
        # func_list: ["Pcr", <task>, *func_list]
        if func_list is None:
            func_list = []
        if func not in func_list:
            func_list.insert(0, func)  # 默认插入“Pcr” -> ["Pcr"]
        if "Pcr" not in func_list:
            func_list.insert(0, "Pcr")  # 如果func 不是“Pcr”，也插入“Pcr” -> ["Pcr"]

        logger.info(f"Bind task {func_list}")

        # 绑定参数
        visited = set()  # 记录处理过的路径
        self.bound.clear()
        for func in func_list:
            func_data = self.data.get(func, {})
            for group, group_data in func_data.items():
                if isinstance(group_data, dict):
                    for arg, value in group_data.items():
                        path = f"{group}.{arg}"
                        if path in visited:
                            continue
                        arg_name = path_to_arg(path)
                        super().__setattr__(arg_name, value)
                        self.bound[arg_name] = f"{func}.{path}"
                        visited.add(path)

        # 覆盖参数
        for arg, value in self.overridden.items():
            super().__setattr__(arg, value)

    def save(self):
        """
        保存配置修改
        """
        if not self.modified:
            return False

        for path, value in self.modified.items():
            deep_set(self.data, keys=path, value=value)

        logger.info(
            f"保存配置 {filepath_config(self.config_name)}, {dict_to_kv(self.modified)}"
        )
        self.modified.clear()
        self.write_file(self.config_name, data=self.data)
        return True

    def update(self):
        """
        更新配置
        """
        self.load()
        self.config_override()
        self.bind(self.task)
        self.save()

    def override(self, **kwargs):
        """
        覆盖配置
        """
        for arg, value in kwargs.items():
            self.overridden[arg] = value
            super().__setattr__(arg, value)

    config_override = override

    # def multi_set(self):
    #     """
    #     批量设置配置
    #     """
    #     return MultiSetWrapper(main=self)

    # def cross_get(self, keys, default=None):
    #     """
    #     跨任务获取配置
    #     """
    #     return deep_get(self.data, keys=keys, default=default)

    # def cross_set(self, keys, value):
    #     """
    #     跨任务设置配置
    #     """
    #     self.modified[keys] = value
    #     if self.auto_update:
    #         self.update()

    # def get_value(self, path: str, default: Any = None) -> Any:
    #     """
    #     获取配置值

    #     Args:
    #         path: 配置路径，如 "GameSettings.Language"
    #         default: 默认值

    #     Returns:
    #         配置值
    #     """
    #     return deep_get(self.data, path, default)

    # def set_value(self, path: str, value: Any):
    #     """
    #     设置配置值

    #     Args:
    #         path: 配置路径，如 "GameSettings.Language"
    #         value: 配置值
    #     """
    #     self.modified[path] = value
    #     deep_set(self.data, path, value)
    #     if self.auto_update:
    #         self.save()

    # @staticmethod
    # def task_stop(message=""):
    #     """
    #     停止当前任务
    #     """
    #     if message:
    #         raise TaskEnd(message)
    #     else:
    #         raise TaskEnd


# class MultiSetWrapper:
#     """
#     批量设置包装器
#     """

#     def __init__(self, main):
#         self.main = main
#         self.in_wrapper = False

#     def __enter__(self):
#         if self.main.auto_update:
#             self.main.auto_update = False
#         else:
#             self.in_wrapper = True
#         return self

#     def __exit__(self, exc_type, exc_val, exc_tb):
#         if not self.in_wrapper:
#             self.main.update()
#             self.main.auto_update = True
