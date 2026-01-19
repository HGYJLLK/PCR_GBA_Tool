"""
装饰器工具
"""

from typing import Generic, TypeVar

T = TypeVar("T")


class cached_property(Generic[T]):
    """
    缓存属性装饰器
    """

    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        # 检查缓存
        cache_attr = f"_cached_{self.func.__name__}"
        if hasattr(obj, cache_attr):
            return getattr(obj, cache_attr)
        # 计算并缓存
        value = self.func(obj)
        setattr(obj, cache_attr, value)
        return value


def del_cached_property(obj, name):
    """
    删除缓存的属性

    Args:
        obj: 对象
        name: 属性名
    """
    cache_attr = f"_cached_{name}"
    if hasattr(obj, cache_attr):
        delattr(obj, cache_attr)


def has_cached_property(obj, name):
    """
    检查是否有缓存的属性

    Args:
        obj: 对象
        name: 属性名

    Returns:
        bool: 是否有缓存
    """
    cache_attr = f"_cached_{name}"
    return hasattr(obj, cache_attr)


def set_cached_property(obj, name, value):
    """
    设置缓存的属性

    Args:
        obj: 对象
        name: 属性名
        value: 值
    """
    cache_attr = f"_cached_{name}"
    setattr(obj, cache_attr, value)


def run_once(f):
    """
    Run a function only once, no matter how many times it has been called.

    Examples:
        @run_once
        def my_function(foo, bar):
            return foo + bar

        while 1:
            my_function()

    Examples:
        def my_function(foo, bar):
            return foo + bar

        action = run_once(my_function)
        while 1:
            action()
    """

    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)

    wrapper.has_run = False
    return wrapper
