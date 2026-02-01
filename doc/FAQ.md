# FAQ - 常见问题

本文档收集了开发和使用过程中的常见问题及解决方案

---

## 环境配置问题

### ADB 相关问题

#### Q1: 运行脚本时提示 `FileNotFoundError: [WinError 2] 系统找不到指定的文件`

系统环境变量 PATH 中没有配置 ADB 工具路径，导致 Python 无法找到 `adb.exe` 可执行文件

通常是 `subprocess.py` 的 `_execute_child` 中（**进程启动阶段**）无法启动成功

1. **找到 ADB 安装位置**

   常见位置：
   - Android SDK: `C:\Users\<用户名>\AppData\Local\Android\Sdk\platform-tools\`
   - MuMu 模拟器: `C:\Program Files\Netease\MuMuPlayer-12.0\shell\`

2. **添加到系统环境变量**

   - 按 `Win + R`，输入 `sysdm.cpl`，回车
   - 点击 "高级" → "环境变量"
   - 在 "系统变量" 中找到 `Path`，双击
   - 点击 "新建"，粘贴 ADB 所在目录的完整路径
   - 依次点击 "确定" 保存所有窗口

3. **验证配置**

   - **重新打开命令行窗口**
   - 运行以下命令验证：
     ```bash
     adb version
     ```
   - 如果显示版本信息，说明配置成功

### 依赖问题

#### Q1：安装requirements.txt av 库报错

1. 使用 conda单独安装这个 av 库：conda install av=10.0.0 -c conda-forge -y
2. 安装完成后从 requirements.txt 注释 av 库依赖
3. 重新运行 pip install -r requirements.txt 安装依赖

## 贡献

如果您遇到了新的问题并找到了解决方案，欢迎贡献到本 FAQ 文档！
