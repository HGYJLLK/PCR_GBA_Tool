"""
配置工具
"""

import json
import os
import yaml
from typing import Dict, Any
from datetime import datetime, timedelta

from deploy.atomic import atomic_read_text, atomic_read_bytes, atomic_write

DEFAULT_TIME = datetime(2020, 1, 1, 0, 0)


def read_file(file):
    """
    读取 yaml 或 json 文件

    Args:
        file (str): 文件路径

    Returns:
        dict, list: 文件内容，文件不存在时返回空字典
    """
    print(f"read: {file}")
    if file.endswith(".json"):
        content = atomic_read_bytes(file)
        if not content:
            return {}
        return json.loads(content)
    elif file.endswith(".yaml"):
        content = atomic_read_text(file)
        data = list(yaml.safe_load_all(content))
        if len(data) == 1:
            data = data[0]
        if not data:
            data = {}
        return data
    else:
        print(f"Unsupported config file extension: {file}")
        return {}


def write_file(file, data):
    """
    写入 yaml 或 json 文件

    Args:
        file (str): 文件路径
        data (dict, list): 要写入的数据
    """
    print(f"write: {file}")
    if file.endswith(".json"):
        content = json.dumps(
            data, indent=2, ensure_ascii=False, sort_keys=False, default=str
        )
        atomic_write(file, content)
    elif file.endswith(".yaml"):
        if isinstance(data, list):
            content = yaml.safe_dump_all(
                data,
                default_flow_style=False,
                encoding="utf-8",
                allow_unicode=True,
                sort_keys=False,
            )
        else:
            content = yaml.safe_dump(
                data,
                default_flow_style=False,
                encoding="utf-8",
                allow_unicode=True,
                sort_keys=False,
            )
        atomic_write(file, content)
    else:
        print(f"Unsupported config file extension: {file}")


def filepath_argument(filename):
    """配置文件路径"""
    return f"./module/config/argument/{filename}.yaml"


def filepath_args():
    return "./module/config/argument/args.json"


def filepath_config(filename):
    """
    用户配置文件路径

    Args:
        filename (str): 配置文件名

    Returns:
        str: 配置文件路径
    """
    return os.path.join("./config", f"{filename}.json")


def filepath_code():
    """代码配置文件路径"""
    return "./module/config/config_generated.py"


def path_to_arg(path):
    """
    将路径转换为参数

    Args:
        path (str): 配置路径，如 "Scheduler.ServerUpdate"

    Returns:
        str: 参数名，如 "Scheduler_ServerUpdate"
    """
    return str(path).replace(".", "_")


def arg_to_path(arg):
    """
    将参数转换为路径
    例如：'Scheduler_Enable' -> 'Scheduler.Enable'
    """
    return str(arg).replace("_", ".")


def dict_to_kv(dictionary, allow_none=True):
    """
    字典转换为键值字符串
    例如：{'a': 1, 'b': 2} -> 'a=1, b=2'

    Args:
        dictionary: 字典
        allow_none (bool): 是否允许None值

    Returns:
        str: 键值对字符串
    """
    return ", ".join(
        [f"{k}={repr(v)}" for k, v in dictionary.items() if allow_none or v is not None]
    )


def parse_value(value, data=None):
    """
    Convert a string to float, int, datetime, if possible.

    Args:
        value (str): 配置值
        data (dict): 配置数据

    Returns:
        解析后的值
    """
    if "option" in data:
        if value not in data["option"]:
            return data["value"]
    if isinstance(value, str):
        if value == "":
            return None
        if value == "true" or value == "True":
            return True
        if value == "false" or value == "False":
            return False
        if "." in value:
            try:
                return float(value)
            except ValueError:
                pass
        else:
            try:
                return int(value)
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass

    return value


def data_to_type(data, **kwargs):
    """
    | Condition                            | Type     |
    | ------------------------------------ | -------- |
    | Value is bool                        | checkbox |
    | Arg has options                      | select   |
    | `Filter` is in name (in data['arg']) | textarea |
    | Rest of the args                     | input    |

    Args:
        data (dict):
        kwargs: Any additional properties

    Returns:
        str:
    """
    kwargs.update(data)
    if isinstance(kwargs["value"], bool):
        return "checkbox"
    elif "option" in kwargs and kwargs["option"]:
        return "select"
    elif "Filter" in kwargs["arg"]:
        return "textarea"
    else:
        return "input"
