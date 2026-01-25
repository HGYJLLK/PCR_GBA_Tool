# 4 dev_tools

本文介绍 PCR_GBA_Tool 的开发辅助工具，用于简化按钮资源的创建和管理流程

---

## button_extract.py

批量处理 `assets/` 目录，自动生成所有模块的 `assets.py` 文件

```bash
python dev_tools/button_extract.py
```

```bash
assets/
├── handler/
│   ├── LOGIN_CHECK.png       → Button 定义
│   ├── TEMPLATE_ICON.png     → Template 定义
│   └── LOGIN_CHECK.AREA.png  → 覆盖 area 属性
├── ui/
│   └── ...
└── train/
    └── ...

↓ 运行 button_extract.py ↓

module/
├── handler/assets.py
├── ui/assets.py
└── train/assets.py
```

参数说明：

| 模板 | 类型 | 说明 |
|----------|------|------|
| `NAME.png` | Button | 普通按钮 |
| `TEMPLATE_NAME.png` | Template | 模板 (全屏搜索) |
| `MASK_NAME.png` | Mask | 遮罩 (限定搜索区域)，需手动定义 |
| `NAME.AREA.png` | - | 覆盖检测区域 |
| `NAME.COLOR.png` | - | 覆盖颜色取样区域 |
| `NAME.BUTTON.png` | - | 覆盖点击区域 |

生成的代码就像这样

```python
# module/handler/assets.py
LOGIN_CHECK = Button(area=(600, 400, 680, 480), color=(100, 150, 255), button=(600, 400, 680, 480), file="./assets/handler/LOGIN_CHECK.png")
TEMPLATE_ICON = Template(file="./assets/handler/TEMPLATE_ICON.png")
```

## create_button.py

一体化的交互式按钮创建工具

```bash
python dev_tools/create_button.py
```

交互流程：

```
══════ STEP 1: 截图 ══════
请确保游戏界面显示你要提取的按钮,然后按 Enter...
✓ 已保存截图: ./temp_screenshot.png

══════ STEP 2: 选择按钮区域 ══════
正在打开浏览器...
✓ 已在浏览器中打开选择工具 (button_creator.html)

══════ STEP 3: 输入按钮信息 ══════
请输入按钮名称: LOGIN_BUTTON
请输入按钮坐标: ...

══════ STEP 4: 提取并保存 ══════
✓ 已保存按钮图片: ./assets/train/LOGIN_BUTTON.png

══════ STEP 5: 更新 assets.py ══════
请手动将生成代码添加到 module/train/assets.py
```

## 常用工作流

### 添加新按钮

1. 运行 `python dev_tools/create_button.py`
2. 截图 → 框选 (Web UI) → 输入名称
3. 将生成的图片移动到正式目录 (如 `assets/handler/`)
4. 运行 `python dev_tools/button_extract.py` 更新代码
5. 使用: `from module.handler.assets import NEW_BUTTON`