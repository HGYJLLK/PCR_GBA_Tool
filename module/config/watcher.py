"""
配置热更新功能,文件监控器
"""

import os
from datetime import datetime

from module.config.utils import filepath_config, DEFAULT_TIME


class ConfigWatcher:
    config_name = "pcr"
    start_mting = DEFAULT_TIME

    def start_watching(self) -> None:
        """
        启动配置热更新，开始监控配置文件
        """
        self.start_mting = self.get_mtime()

    def get_mtime(self) -> datetime:
        """
        获取配置文件的最近修改时间

        Returns:
            datetime：文件最近修改时间
        """
        timestamp = os.stat(filepath_config(self.config_name)).st_mtime
        mtime = datetime.fromtimestamp(timestamp).replace(microsecond=0)
        return mtime

    def should_reload(self) -> bool:
        """
        判断是否需要重新加载配置文件

        Returns:
            bool：如果文件已修改且应该重新加载配置，则返回True
        """
        try:
            mtime = self.get_mtime()
            if mtime > self.start_mting:
                print(f'配置 "{self.config_name}" 在 {mtime} 被修改，正在重新加载...')
                return True
            return False
        except (OSError, FileNotFoundError):
            return False
