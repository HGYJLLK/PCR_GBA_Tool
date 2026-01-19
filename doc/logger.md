# 1.1 Logger

这里介绍 module/logger.py 文件

这是基于 logger + rich 库实现的日志管理系统，参考了 alas 源码

日志格式：%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s

时间格式：%Y-%m-%d %H:%M:%S

例子：2020-09-11 08:35:59.460 | INFO | XXXXXXXX

## class Highlighter(RegexHighlighter)

该类继承自 RegexHighlighter，用于高亮日志中的关键词，也就是需要高亮的内容

## COLOR_THEME

颜色主题，与 Highlighter 类配合使用，自定义日志的颜色显示

## logger.info

表示系统正常运行的信息，是对运行状态、情况的描述，能够追踪到运行的情况

## logger.warning

表示系统出现了警告，但是程序仍然可以正常运行，是对程序运行状态的提醒，但是需要注意

## logger.error

表示系统出现了错误，可能会导致程序崩溃，需要注意，要t1 级处理

## logger.critical

表示系统出现了严重错误，程序崩溃，需要立即处理

## logger.debug

调试信息，一般用于开发阶段，用于追踪程序运行的细节

## logger.hr(title, level=0)

仅在脚本开始的时候运行
```bash
2020-01-01 00:00:00.000 | INFO | +---------------------------------------------+
2020-01-01 00:00:00.000 | INFO | |                    TITLE                    |
2020-01-01 00:00:00.000 | INFO | +---------------------------------------------+
```

## logger.hr(title, level=1)

表示开始执行某个大功能大模块的时候运行

```bash
2020-01-01 00:00:00.000 | INFO | ==================== TITLE ====================
```

## logger.hr(title, level=2)

表示功能的某一个阶段开始的时候运行，比如跳转到模拟公会战、公会战模拟的时候

```bash
2020-01-01 00:00:00.000 | INFO | -------------------- TITLE --------------------
```

## logger.hr(title, level=3)

表示某个功能的某个阶段的细分运行，即跳转到模拟公会战中间会运行很多东西

```bash
2020-01-01 00:00:00.000 | INFO | <<< TITLE >>>
```

## logger.attr(name, text)

进行一些设置、配置的时候运行

```bash
2020-01-01 00:00:00.000 | INFO | [name] text
```

## logger.attr_align(name, text, front='', align=22)

与 logger.attr 类似，但是可以设置对齐方式

```bash
2020-09-11 02:16:51.542 | INFO |           vanish_point: (  635，-1676)
2020-09-11 02:16:51.543 | INFO |          distant_point: (-2245，-1676)
2020-09-11 02:16:51.568 | INFO | 0.109s  _   Horizontal: 6 (6 inner，2 edge)
2020-09-11 02:16:51.568 | INFO | Edges: /_\    Vertical: 9 (9 inner，2 edge)
2020-09-11 02:16:51.617 | INFO |            tile_center: 0.955 (good match)
2020-09-11 02:16:51.627 | INFO | 0.058s  _   edge_lines: 3 hori，2 vert
2020-09-11 02:16:51.627 | INFO | Edges: /_\   homo_loca: ( 24， 54)
2020-09-11 02:16:51.630 | INFO |            center_loca: (3，2)
2020-09-11 02:16:51.630 | INFO |       camera_corrected: A1 -> D3
2020-09-11 02:16:51.630 | INFO |                 Camera: D3
```

## logger.exception

实现与 alas 完全相同的报错日志模式

通过在 Logger日志类中绑定self.exception = self.logger.exception方法，实现与 alas 完全相同的报错日志模式

其实这里是基于了 Rich 库封装好的一种日志错误输出方式，具体可以参考源码 rich.logging.RichHandler

在使用上通过 logger.exception 输出报错信息，会自动打印出报错的位置、类型、错误信息等，非常方便

```python
try:
    show()
except Exception as e:
    logger.exception("捕获到异常，显示详细信息")
```