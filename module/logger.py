import datetime
import logging
import os

from rich.console import Console  # 控制台对象
from rich.logging import RichHandler  # Rich 的日志处理器
from rich.rule import Rule  # 分隔线
from rich.style import Style  # 样式定义
from rich.theme import Theme  # 主题配置
from rich.highlighter import RegexHighlighter  # 正则表达式高亮器


class Highlighter(RegexHighlighter):
    """
    定义需要高亮显示的内容
    """

    base_prefix = "log."  # 定义高亮前缀
    highlights = [
        # 时间格式：14:30:25.123
        (
            r"(?P<time>([0-1]{1}\d{1}|[2]{1}[0-3]{1})(?::)?"
            r"([0-5]{1}\d{1})(?::)?([0-5]{1}\d{1})(.\d+\b))"
        ),
        # 各种括号：{ [ ( ) ] }
        r"(?P<brace>[\{\[\(\)\]\}])",
        # 布尔值和 None
        r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
        # /path/to/file.txt 或 C:\Windows\file.exe
        r"(?P<path>(([A-Za-z]\:)|.)?\B([\/\\][\w\.\-\_\+]+)*[\/\\])(?P<filename>[\w\.\-\_\+]*)?",
    ]


# 颜色主题:定义内容使用的颜色
COLOR_THEME = Theme(
    {
        "log.brace": Style(bold=True),  # 括号：粗体
        "log.bool_true": Style(color="bright_green", italic=True),  # 布尔值 True
        "log.bool_false": Style(color="bright_red", italic=True),  # 布尔值 False
        "log.none": Style(color="magenta", italic=True),  # 特殊值 None
        "log.path": Style(color="magenta"),  # 文件路径
        "log.filename": Style(color="bright_magenta"),  # 文件名
        "log.str": Style(color="green", italic=False, bold=False),  # 字符串
        "log.time": Style(color="cyan"),  # 时间
        "log.line": Style(bold=True),  # 分隔线文字
    }
)


class Logger:
    """
    日志类
    """

    def __init__(self, log_name="default"):
        """
        初始化日志器

        Args:
            log_name(str,optional)：日志器名称，标志来自哪个功能模块的日志
        """
        self.logger = logging.getLogger(log_name)
        self.logger.setLevel(logging.DEBUG)

        # 清空现有日志处理器，防止重复添加
        self.logger.handlers = []

        # 设置控制台和日志文件输出格式
        self.console_formatter = logging.Formatter(
            # %(msecs)03d，毫秒位数为3位，不足补0
            fmt="%(asctime)s.%(msecs)03d │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.file_formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 设置控制台输出
        self._setup_console_handler()

        # 设置日志文件输出
        self._setup_file_handler(log_name)

        # 绑定日志方法
        self._setup_methods()

    def _setup_console_handler(self):
        """
        美化控制台输出
        """
        console_hdlr = RichHandler(
            console=Console(
                theme=COLOR_THEME,
                highlighter=Highlighter(),
            ),
            show_path=False,  # 隐藏文件路径
            show_time=False,  # 隐藏时间（已经用自己的格式了）
            rich_tracebacks=True,  # 美化的错误追踪
            tracebacks_show_locals=True,  # 错误时显示局部变量
            tracebacks_extra_lines=3,  # 错误追踪显示额外的代码行数
        )
        console_hdlr.setFormatter(self.console_formatter)
        self.logger.addHandler(console_hdlr)

    def _setup_file_handler(self, log_name):
        """
        设置文件输出
        """
        # 日志文件路径
        log_dir = "./logs"
        os.makedirs(log_dir, exist_ok=True)

        # 按日期命名日志文件
        log_file = os.path.join(
            log_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d')}_{log_name}.log"
        )

        try:
            file_hdlr = logging.FileHandler(log_file, encoding="utf-8")
            file_hdlr.setFormatter(self.file_formatter)
            self.logger.addHandler(file_hdlr)
            self.log_file = log_file  # 记录日志文件路径
        except Exception as e:
            # 创建文件失败，只记录错误
            self.logger.error(f"Failed to create log file: {e}")

    def _setup_methods(self):
        """
        绑定日志方法和自定义方法
        """
        # 绑定日志方法
        self.info = self.logger.info
        self.debug = self.logger.debug
        self.warning = self.logger.warning
        self.error = self._error_handler(self.logger.error)
        self.critical = self.logger.critical
        self.exception = self.logger.exception

        # 绑定自定义方法
        self.hr = self._hr  # 分级标题
        self.conf = self._conf  # 配置属性
        self.conf_align = self._conf_align  # 配置属性对齐
        self.rule = self._rule  # 分割线
        self.attr = self._attr  # 属性显示

    def _error_handler(self, error_func):
        """
        异常错误处理

        如：logger.error(ValueError("错误信息")) 会自动格式化为 "ValueError: 错误信息"
        """

        def error_wrapper(msg, *args, **kwargs):
            if isinstance(msg, Exception):
                msg = f"{type(msg).__name__}: {msg}"
            return error_func(msg, *args, **kwargs)

        return error_wrapper

    def _hr(self, title, level=3):
        """
        分级标题

        level=0: 最高级，上下都有双线
        level=1: 一级标题，双线
        level=2: 二级标题，单线
        level=3: 三级标题，简单的 <<< 标记

        Args:
            title: 标题文字
            level: 标题级别 (0-3)
        """
        title = str(title).upper()
        if level == 1:
            """
            ══════ SECTION 1 ══════
            """
            self._rule(title, characters="=")
        elif level == 2:
            """
            ───── SUBSECTION ──────
            """
            self._rule(title, characters="-")
        elif level == 3:
            """
            <<< SUBSUBSECTION >>>
            """
            self.info(f"[bold]<<< {title} >>>[/bold]", extra={"markup": True})
        elif level == 0:
            """
            ══════════
             SECTION
            ══════════
            """
            self._rule(characters="=")
            self._rule(title, characters=" ")
            self._rule(characters="=")

    def _conf(self, title, text):
        """
        显示配置项或状态信息，格式：[属性名] 属性值

            [Config] demo_config.yaml
            [Version] 1.0.0
        """
        self.info("[%s] %s" % (str(title), str(text)))

    def _conf_align(self, title, text, front="", align=22):
        """
        格式：      属性名: 属性值
                   Host: 127.0.0.1
                   Port: 8080

        Args:
            title: 属性名
            text: 属性值
            front: 前缀
            align: 左侧对齐长度
        """
        title = str(title).rjust(align)
        if front:
            title = front + title[len(front) :]
        self.info("%s: %s" % (title, str(text)))

    def _attr(self, name, value):
        """
        显示属性信息，格式：name = value

        Args:
            name: 属性名
            value: 属性值
        """
        self.info(f"{name} = {value}")

    def _rule(
        self, title="", *, characters="-", style="rule.line", end="\n", align="center"
    ):
        """
        分割线

        Args:
            title: 分隔线中间的标题
            *：仅限关键字参数（python3有的），指*之后的参数只能通过关键字来传参
            characters: 分隔线字符
            style: 样式（rule.line为rich默认分割线样式）
            end: 结束字符
            align: 对齐方式
        """
        # 获取 Rich 控制台
        for handler in self.logger.handlers:
            if isinstance(handler, RichHandler):
                rule = Rule(
                    title=title,
                    characters=characters,
                    style=style,
                    end=end,
                    align=align,
                )
                handler.console.print(rule)
                break


# 初始化 Logger
logger = Logger("pcr")


# 演示 和 测试日志功能
def show():
    logger.info("INFO")
    logger.warning("WARNING")
    logger.debug("DEBUG")
    logger.error("ERROR")
    logger.critical("CRITICAL")
    logger.hr("hr0", 0)
    logger.hr("hr1", 1)
    logger.hr("hr2", 2)
    logger.hr("hr3", 3)
    logger.info(r"Brace { [ ( ) ] }")
    logger.info(r"True, False, None")
    logger.info(r"/path/to/file.txt or C:\Windows\file.exe")
    local_var1 = "This is local variable"  # 测试异常发生时能否显示局部变量
    # Line before exception  # 测试日志行号追踪功能
    raise Exception("Exception")  # 抛出异常，测试异常处理能力
