"""
公主连结服务器配置
"""

server = "cn"

VALID_SERVER = ["cn"]

# 公主连结包名映射
VALID_PACKAGE = {
    "com.bilibili.priconne": "cn",
}

# 包名到启动Activity的映射
DICT_PACKAGE_TO_ACTIVITY = {
    "com.bilibili.priconne": "com.bilibili.permission.PermissionActivity",
}


def set_server(package_or_server: str):
    """
    设置服务器
    Args:
        package_or_server: 包名或服务器名称
    """
    global server

    # 如果是服务器名称，直接设置
    if package_or_server in VALID_SERVER:
        server = package_or_server
        return

    # 如果是包名，查找对应的服务器
    if package_or_server in VALID_PACKAGE:
        server = VALID_PACKAGE[package_or_server]
        return

    # 未找到匹配，使用默认值
    from module.logger import logger

    logger.warning(
        f"Unknown package or server: {package_or_server}, using default: {server}"
    )
