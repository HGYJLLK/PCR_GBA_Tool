"""
战斗角色位置定义
分辨率: 1280×720
"""

# 角色点击位置 (x, y)
# 基于 MaaPcrclanbattle 的坐标
CHARACTER_POSITIONS = {
    1: (300, 550),  # 1号位（最左）
    2: (460, 550),  # 2号位
    3: (660, 550),  # 3号位（中间）
    4: (780, 550),  # 4号位
    5: (940, 550),  # 5号位（最右）
}

# 点击区域大小
CLICK_AREA_SIZE = (50, 50)


def get_character_position(char_id):
    """
    获取角色点击位置
    
    Args:
        char_id: 角色ID (1-5)
        
    Returns:
        (x, y) 坐标元组，如果 ID 无效则返回 None
    """
    return CHARACTER_POSITIONS.get(char_id)


def get_all_positions():
    """获取所有角色位置"""
    return CHARACTER_POSITIONS.copy()
