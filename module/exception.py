# ============================================================================
# 任务控制类异常
# ============================================================================


class TaskEnd(Exception):
    """任务正常结束"""

    pass


class ScriptEnd(Exception):
    """脚本正常结束"""

    pass


class ProcessComplete(Exception):
    """某个处理阶段结束"""

    pass


class GamePageUnknownError(Exception):
    """游戏页面未知错误"""

    pass


# ============================================================================
# 资源类异常
# ============================================================================


class ResourceExhausted(Exception):
    """资源相关异常"""

    pass


"""
后续的所有资源相关，均继承自ResourceExhausted
"""

# ============================================================================
# 系统状态类异常
# ============================================================================


class SystemStuck(Exception):
    """系统卡死"""

    pass


class SystemOverload(Exception):
    """系统过载"""

    pass


class SystemConfigError(Exception):
    """系统配置错误"""

    pass


# ============================================================================
# 检测识别类异常
# ============================================================================


class DetectionError(Exception):
    """检测相关异常"""

    pass


class PatternDetectionError(DetectionError):
    """模板匹配异常"""

    pass


class ImageDetectionError(DetectionError):
    """图像识别异常"""

    pass


class TextDetectionError(DetectionError):
    """文本识别异常"""

    pass


# ============================================================================
# 数据处理过程类异常
# ============================================================================


class ProcessingError(Exception):
    """数据处理相关异常"""

    pass


class DataValidationError(ProcessingError):
    """数据输入校验失败"""

    pass


class AlgorithmError(ProcessingError):
    """算法异常"""

    pass


class ConversionError(ProcessingError):
    """数据格式转换异常"""

    pass


# ============================================================================
# 外部依赖类异常
# ============================================================================


class ExternalServiceError(Exception):
    """外部服务调用相关异常"""

    pass


class NetworkConnectionError(ExternalServiceError):
    """网络连接异常"""

    pass


class APIServiceError(ExternalServiceError):
    """API服务调用异常"""

    pass


class DatabaseError(ExternalServiceError):
    """数据库操作异常"""

    pass


# ============================================================================
# 用户交互类异常
# ============================================================================


class UserIntervention(Exception):
    """人工介入相关异常（顶层处理要进行通知和暂停执行）"""

    pass


class UserInputRequired(UserIntervention):
    """抛出需要用户输入的对话框或表单"""

    pass


class UserDecisionRequired(UserIntervention):
    """需要用户选择"""

    pass


class UserAuthenticationRequired(UserIntervention):
    """需要用户进行身份验证"""

    pass


# ============================================================================
# 设备连接类异常
# ============================================================================


class RequestHumanTakeover(Exception):
    """请求人工接管"""

    pass


class EmulatorNotRunningError(Exception):
    """模拟器未运行"""

    pass


class GameNotRunningError(Exception):
    """游戏未运行"""

    pass


class GameStuckError(Exception):
    """游戏卡住"""

    pass


class GameTooManyClickError(Exception):
    """游戏点击过多"""

    pass


class ScriptError(Exception):
    """脚本错误"""

    pass
