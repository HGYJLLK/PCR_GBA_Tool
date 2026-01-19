import module.config.server as server
from module.base.decorator import cached_property, del_cached_property


class Resource:
    """
    资源管理类，管理 Button 和 Template 等资源对象
    """

    # 类属性：记录所有 button 和 template 实例
    instances = {}
    # 实例属性：记录实例的缓存属性列表
    cached = []

    def resource_add(self, key):
        """
        将实例添加到全局资源

        Args:
            key: 资源键（通常是文件路径）
        """
        Resource.instances[key] = self

    def resource_release(self):
        """
        释放缓存的属性
        """
        for cache in self.cached:
            del_cached_property(self, cache)

    @classmethod
    def is_loaded(cls, obj):
        """
        检查资源是否已加载

        Args:
            obj: 资源对象

        Returns:
            bool: 是否已加载
        """
        if hasattr(obj, "_image") and obj._image is None:
            return False
        elif hasattr(obj, "image") and obj.image is None:
            return False
        return True

    @classmethod
    def resource_show(cls):
        """
        显示所有已加载的资源
        """
        from module.logger import logger

        logger.hr("Show resource")
        for key, obj in cls.instances.items():
            if cls.is_loaded(obj):
                continue
            logger.info(f"{obj}: {key}")

    @staticmethod
    def parse_property(data, s=None):
        """
        解析 Button 或 Template 对象的属性（`area`, `color`, `button`, `file` 等）

        Args:
            data: 字典或字符串
            s (str): 服务器名称，如果为 None 则使用全局 server.server

        Returns:
            解析后的值
        """
        if s is None:
            s = server.server
        if isinstance(data, dict):
            return data[s]
        else:
            return data


def release_resources(next_task=""):
    """
    释放资源（内存管理）

    Args:
        next_task (str): 下一个任务名称
    """
    # 释放资源缓存
    for key, obj in Resource.instances.items():
        obj.resource_release()
