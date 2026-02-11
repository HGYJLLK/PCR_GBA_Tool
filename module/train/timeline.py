"""
战斗时间轴配置
定义在特定时间点点击哪些角色
"""

from module.logger import logger


class TimelineAction:
    """单个时间点的动作"""
    
    def __init__(self, time_str, characters, description=""):
        """
        Args:
            time_str: 时间字符串，如 "1:24"
            characters: 要点击的角色列表，如 [3, 4]
            description: 描述，如 "3号位和4号位开UB"
        """
        self.time_str = time_str
        self.time_seconds = self._parse_time(time_str)
        self.characters = characters if isinstance(characters, list) else [characters]
        self.description = description
        self.executed = False
    
    def _parse_time(self, time_str):
        """解析时间字符串为秒数"""
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    
    def __repr__(self):
        return f"TimelineAction({self.time_str}, {self.characters}, '{self.description}')"


class Timeline:
    """战斗时间轴"""
    
    def __init__(self, name="default"):
        self.name = name
        self.actions = []
    
    def add_action(self, time_str, characters, description=""):
        """
        添加一个时间点动作
        
        Args:
            time_str: 时间字符串，如 "1:24"
            characters: 要点击的角色ID或ID列表，如 3 或 [3, 4]
            description: 动作描述
            
        Returns:
            self (支持链式调用)
        """
        action = TimelineAction(time_str, characters, description)
        self.actions.append(action)
        # 按时间倒序排序（从大到小）
        self.actions.sort(key=lambda x: x.time_seconds, reverse=True)
        return self
    
    def get_next_action(self, current_seconds):
        """
        获取下一个要执行的动作
        
        Args:
            current_seconds: 当前时间（秒）
            
        Returns:
            TimelineAction 或 None
        """
        for action in self.actions:
            if not action.executed and current_seconds <= action.time_seconds:
                return action
        return None
    
    def reset(self):
        """重置所有动作状态"""
        for action in self.actions:
            action.executed = False
        logger.info(f"时间轴 '{self.name}' 已重置")
    
    def __repr__(self):
        return f"Timeline('{self.name}', {len(self.actions)} actions)"


# 预定义时间轴示例
def create_example_timeline():
    """创建示例时间轴"""
    timeline = Timeline("示例轴")
    timeline.add_action("1:24", [3, 4], "3号4号开UB")
    timeline.add_action("1:11", 1, "1号开UB")
    timeline.add_action("1:00", [2, 5], "2号5号开UB")
    return timeline


# 预定义：简单测试轴
def create_test_timeline():
    """创建测试时间轴（用于验证功能）"""
    timeline = Timeline("测试轴")
    timeline.add_action("1:20", 3, "测试：点击3号位")
    timeline.add_action("1:10", [1, 5], "测试：点击1号和5号位")
    return timeline
