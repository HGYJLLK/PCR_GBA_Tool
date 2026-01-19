# PCR_GBA (PrincessConnect!Re:Dive Guild Battle Automation)

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-%3E%3D3.8-3776ab?logo=python&logoColor=white" alt="Python >=3.8" /></a>
  <a href="https://developer.android.com/studio/command-line/adb"><img src="https://img.shields.io/badge/ADB-tool-3DDC84?logo=android&logoColor=white" alt="ADB tool" /></a>
</p>

# 目录

- [安装](#安装)
- [Wiki](#wiki)
- [已知问题](#已知问题)
- [鸣谢](#鸣谢)

# 安装

- python 版本必须为 3.7.6

```python
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python pcr.py
```

# Wiki

- 开发文档详情请看[Wiki](https://github.com/HGYJLLK/PCR_GBA_Tool/wiki)

# 已知问题

- 安装 av 库遇到问题

  > 如果你是使用 conda 环境，尝试使用该命令单独安装 av 库：`conda install av=10.0.0 -c conda-forge -y`
  > 安装成功后，记得在 requirements.txt 将 av 这个库注释掉
  > 安装成功后再次执行 `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

- 安装 opencv 库遇到问题
  > 尝试安装指定版本：pip install opencv-python==4.5.3.56

# 鸣谢

感谢[AzurLaneAutoScript](https://github.com/LmeSzinc/AzurLaneAutoScript)项目的 AzurLane 自动化脚本，本项目参考了其代码，在此表示感谢
