# 4. UI导航

## BFS 寻路算法

- 代码位于：module/ui/page.py

```python
@classmethod
def init_connection(cls, destination):
    """
    从目标页面反向构建 BFS 树，用于寻找最短路径
    """
    cls.clear_connection()

    visited = {destination}

    while 1:
        new = visited.copy()
        for page in visited:
            for link in cls.iter_pages():
                if link in visited:
                    continue
                if page in link.links:
                    link.parent = page  # 设置父节点指针
                    new.add(link)

        if len(new) == len(visited):
            break  # 无新节点，遍历完成
        visited = new
```

**寻路原理**：

1. **反向 BFS**：从目标页面开始，向源头扩散
2. **parent 链**：每个页面记录到达目标的下一步
3. **最短路径**：BFS 保证找到最少点击次数

## 页面跳转实现

```python
def ui_goto(self, destination, get_ship=True, offset=(30, 30), skip_first_screenshot=True):
    # 初始化寻路
    Page.init_connection(destination)

    logger.hr(f"UI goto {destination}")
    while 1:
        self.device.screenshot()

        # 到达目标
        if self.ui_page_appear(page=destination, offset=offset):
            logger.info(f'Page arrive: {destination}')
            break

        # 查找当前页面并执行跳转
        for page in Page.iter_pages():
            if page.parent is None or page.check_button is None:
                continue
            if self.appear(page.check_button, offset=offset, interval=5):
                logger.info(f'Page switch: {page} -> {page.parent}')
                button = page.links[page.parent]  # 获取跳转按钮
                self.device.click(button)
                break

        # 处理弹窗干扰
        if self.ui_additional(get_ship=get_ship):
            continue
```

## 弹窗处理系统

```python
def ui_additional(self, get_ship=True):
    """处理所有 UI 切换时的弹窗"""

    # OpSi 特殊弹窗（优先级最高）
    if self.ui_page_os_popups():
        return True

    # 通用弹窗
    if self.handle_popup_confirm("UI_ADDITIONAL"):
        return True
    if self.handle_urgent_commission():
        return True

    # 主界面弹窗
    if self.ui_page_main_popups(get_ship=get_ship):
        return True

    # 剧情跳过
    if self.handle_story_skip():
        return True

    # 误触处理
    if self.appear(EXERCISE_PREPARATION, interval=3):
        logger.info(f'UI additional: {EXERCISE_PREPARATION} -> {GOTO_MAIN}')
        self.device.click(GOTO_MAIN)
        return True
```

## 开发者导航配置

### 定义页面

```python
# module/ui/page.py

# 创建页面对象，指定识别按钮
page_A = Page(A_CHECK)          # A 页面用 A_CHECK 按钮识别
page_B = Page(B_CHECK)          # B 页面用 B_CHECK 按钮识别
page_C = Page(C_CHECK)          # C 页面
page_D = Page(D_CHECK)          # D 页面
page_E = Page(E_CHECK)          # E 页面
```

**开发者只需要：**
- 截图裁剪出每个页面的特征按钮（如 `A_CHECK.png`）
- 创建 Page 对象

### 定义连接

```python
# 定义页面之间的直接链接（link）
# 格式：page_X.link(button=点击的按钮, destination=目标页面)

page_A.link(button=A_TO_B_BUTTON, destination=page_B)  # A 有按钮可以到 B
page_A.link(button=A_TO_C_BUTTON, destination=page_C)  # A 有按钮可以到 C

page_B.link(button=B_TO_D_BUTTON, destination=page_D)  # B 有按钮可以到 D
page_B.link(button=B_TO_A_BUTTON, destination=page_A)  # B 有按钮返回 A

page_C.link(button=C_TO_E_BUTTON, destination=page_E)  # C 有按钮到 E
page_C.link(button=C_TO_A_BUTTON, destination=page_A)  # C 有按钮返回 A

page_D.link(button=D_TO_E_BUTTON, destination=page_E)  # D 有按钮到 E

page_E.link(button=E_TO_A_BUTTON, destination=page_A)  # E 有按钮返回 A
```