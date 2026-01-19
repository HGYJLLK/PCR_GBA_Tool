from collections import deque
from typing import Any, Union, List


def deep_get(data, keys, default=None):
    """
    从嵌套字典获取值

    Args:
        data (dict): 字典
        keys (Union[str,List[str]]): 键值，可以是字符串或列表
        default (Any, optional): 默认值. Defaults to None.

    Returns:
        获取到的值或者默认值
    """
    if isinstance(keys, str):
        keys = keys.split(".")

    current = data
    try:
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    except (KeyError, TypeError, AttributeError):
        return default


def deep_set(data, keys, value):
    """
    设置嵌套字典的值

    Args:
        data (dict): 字典
        keys (Union[str,List[str]]): 键值，可以是字符串或列表
        value (Any): 设置的值
    """
    if isinstance(keys, str):
        keys = keys.split(".")

    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def deep_merge(dict1, dict2):
    """
    深度合并两个字典

    Args:
        dict1 (dict): 字典1
        dict2 (dict): 字典2

    Returns:
        dict: 深度合并后的字典
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def deep_copy(data):
    """
    深度拷贝字典

    Args:
        data (dict): 要复制的数据

    Returns:
        dict: 深度拷贝后的字典
    """
    if isinstance(data, dict):
        return {k: deep_copy(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [deep_copy(v) for v in data]
    else:
        return data


def deep_iter(data, min_depth=None, depth=3):
    """
    深度迭代字典
    """
    if min_depth is None:
        min_depth = depth
    assert 1 <= min_depth <= depth

    # 等价于 dict.items()
    try:
        if depth == 1:
            for k, v in data.items():
                yield [k], v
            return
        # 迭代第一层深度
        elif min_depth == 1:
            q = deque()
            for k, v in data.items():
                key = [k]
                if type(v) is dict:
                    q.append((key, v))
                else:
                    yield key, v
        else:
            q = deque()
            for k, v in data.items():
                key = [k]
                if type(v) is dict:
                    q.append((key, v))
    except AttributeError:
        # data 不是字典
        return

    # 迭代深度
    current = 2
    while current <= depth:
        new_q = deque()
        # 最大深度
        if current == depth:
            while q:
                key, value = q.popleft()
                try:
                    for k, v in value.items():
                        new_key = key + [k]
                        if current >= min_depth:
                            yield new_key, v
                except AttributeError:
                    # value 不是字典
                    pass
        else:
            while q:
                key, value = q.popleft()
                try:
                    for k, v in value.items():
                        new_key = key + [k]
                        if type(v) is dict:
                            new_q.append((new_key, v))
                        elif current >= min_depth:
                            yield new_key, v
                except AttributeError:
                    # value 不是字典
                    pass
        q = new_q
        current += 1


def deep_default(d, keys, value):
    """
    Set value into nested dict safely, imitating deep_get().
    Can only set dict
    """
    # 150 * depth (ns)
    if type(keys) is str:
        keys = keys.split(".")

    first = True
    exist = True
    prev_d = None
    prev_k = None
    prev_k2 = None
    try:
        for k in keys:
            if first:
                prev_d = d
                prev_k = k
                first = False
                continue
            try:
                # if key in dict: dict[key] > dict.get > dict.setdefault > try dict[key] except
                if exist and prev_k in d:
                    prev_d = d
                    d = d[prev_k]
                else:
                    exist = False
                    new = {}
                    d[prev_k] = new
                    d = new
            except TypeError:
                # `d` is not dict
                exist = False
                d = {}
                prev_d[prev_k2] = {prev_k: d}

            prev_k2 = prev_k
            prev_k = k
            # prev_k2, prev_k = prev_k, k
    # Input `keys` is not iterable
    except TypeError:
        return

    # Last key, set value
    try:
        d.setdefault(prev_k, value)
        return
    # Last value `d` is not dict
    except AttributeError:
        prev_d[prev_k2] = {prev_k: value}
        return


def deep_pop(d, keys, default=None):
    """
    Pop value from nested dict and list
    """
    if type(keys) is str:
        keys = keys.split(".")

    try:
        for k in keys[:-1]:
            d = d[k]
        # No `pop(k, default)` so it can pop list
        return d.pop(keys[-1])
    # No such key
    except KeyError:
        return default
    # Input `keys` is not iterable or input `d` is not dict
    # list indices must be integers or slices, not str
    except TypeError:
        return default
    # Input `keys` out of index
    except IndexError:
        return default
    # Last `d` is not dict
    except AttributeError:
        return default
