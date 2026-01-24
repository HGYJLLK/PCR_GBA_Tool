# 1 setup

本文档介绍如何运行 PCR_GBA_Tool

## 环境要求

- **Python 版本**: 3.7.6（必须使用此版本）
- **操作系统**: Windows（暂不支持 mac 系统）
- **模拟器**: MuMu12
- **ADB 工具**：用于连接和控制模拟器

## 安装步骤

### 克隆项目

```bash
git clone https://github.com/HGYJLLK/PCR_GBA_Tool.git
cd PCR_GBA_Tool
```

### 创建虚拟环境

```bash
# 使用 conda
conda create -n pcr python=3.7.6
conda activate pcr
```

### 安装依赖

```bash
pip install -r requirements.txt
```

## 配置模拟器

### MuMu12 配置

1. 打开 MuMu 模拟器设置
2. 开启 ADB 调试

### 连接验证

```bash
# 检查 ADB 连接
adb devices

# 应显示类似：
# List of devices attached
# 127.0.0.1:16384    device
```

## 配置文件

### 创建用户配置

1. 复制模板配置：

```bash
copy config\template.json config\your_config.json
```

2. 编辑配置文件，修改你的 mumu 的 ADB 地址：

```json
{
  "Pcr": {
    "Emulator": {
      "Serial": "127.0.0.1:16384"
    }
  }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `Emulator.Serial` | 模拟器 ADB 地址 | `auto` |
| `Emulator.ScreenshotMethod` | 截图方式 | `DroidCast_raw` |
| `Emulator.ControlMethod` | 控制方式 | `MaaTouch` |

## 运行程序

修改 `pcr.py` 中的配置名称：

```python
pcr = PCRGBATool(config_name="your_config")
```

```bash
python pcr.py
```