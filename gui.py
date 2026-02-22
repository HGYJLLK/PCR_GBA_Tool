import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import yaml

# 保证能正确导入 module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module.config.config import PriconneConfig
from pcr import PCRGBATool

# ==================== 中文翻译映射 ====================
TRANSLATIONS = {
    # ---- Task / Tab 名 ----
    "Pcr": "公主连结",

    # ---- Group 名 ----
    "Scheduler": "调度器",
    "Emulator": "模拟器",

    # ---- 字段名 ----
    # Scheduler
    "Enable": "启用",
    "NextRun": "下次运行",
    "Command": "指令",
    "SuccessInterval": "成功间隔(s)",
    "FailureInterval": "失败间隔(s)",
    "ServerUpdate": "服务器更新时间",
    # Emulator
    "Serial": "序列号",
    "PackageName": "PackageName",
    "ScreenshotMethod": "截图方式",
    "ControlMethod": "控制方式",
    "AdbRestart": "ADB重连",
}

def t(key: str) -> str:
    """返回 key 对应的中文标签，没有映射时原样返回。"""
    return TRANSLATIONS.get(key, key)


class ConfigGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PCR GBA Tool - Configuration Editor")
        self.root.geometry("900x700")
        
        # 优化界面字型与样式
        self.style = ttk.Style(self.root)
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")
            
        default_font = ("Microsoft YaHei", 10)
        bold_font = ("Microsoft YaHei", 10, "bold")
        
        self.style.configure(".", font=default_font)
        self.style.configure("TButton", padding=6, relief="flat", background="#e1e1e1", font=bold_font)
        self.style.map("TButton", background=[("active", "#cce4f7")])
        self.style.configure("TNotebook.Tab", padding=[15, 5], font=bold_font)
        self.style.configure("TLabelframe", font=bold_font, padding=10)
        self.style.configure("TLabelframe.Label", font=bold_font, foreground="#333333")
        
        # 加载 argument.yaml 解析组件选项
        self.argument_data = self.load_arguments()
        
        # 初始化配置
        self.config_name = "maple"
        self.pcr_config = PriconneConfig(config_name=self.config_name)
        self.config_data = self.pcr_config.data
        
        self.create_widgets()

    def load_arguments(self):
        """加载 argument.yaml，用于提取各个设置的 option 项"""
        yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "module", "config", "argument", "argument.yaml")
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"警告: 无法加载 argument.yaml，下拉框将回退为输入框 ({e})")
            return {}

    def get_options_for_field(self, group_name, field_name):
        """从 argument_data 提取对应字段的 option 列表"""
        if not self.argument_data:
            return None
        group_data = self.argument_data.get(group_name)
        if group_data and isinstance(group_data, dict):
            field_data = group_data.get(field_name)
            if field_data and isinstance(field_data, dict):
                return field_data.get("option", None)
        return None

    def create_widgets(self):
        # 顶部控制栏
        top_frame = ttk.Frame(self.root, padding=15)
        top_frame.pack(side="top", fill="x")

        ttk.Label(top_frame, text=f"📂 当前配置: {self.config_name}.json", font=("Microsoft YaHei", 14, "bold"), foreground="#005a9e").pack(side="left")
        
        run_btn = ttk.Button(top_frame, text="▶ 运行主程序", command=self.run_main_program)
        run_btn.pack(side="right", padx=10)

        # 主内容区域：Notebook (选项卡)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=15, pady=10)

        self.tabs = {}
        self.variables = {}  # 保存所有 tkinter 变量以便于管理
        self.build_tabs()

    def build_tabs(self):
        # 清空现有的 tabs
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        self.tabs.clear()
        self.variables.clear()

        # 根据配置数据生成 UI
        for task_name, task_data in self.config_data.items():
            if not isinstance(task_data, dict):
                continue
            
            main_tab = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(main_tab, text=f" {t(task_name)} ")
            
            canvas = tk.Canvas(main_tab, highlightthickness=0)
            scrollbar = ttk.Scrollbar(main_tab, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e, canvas=canvas: canvas.configure(
                    scrollregion=canvas.bbox("all")
                )
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # 将 UI 组分列排布（每行两个 Group）
            col = 0
            row = 0
            for group_name, group_data in task_data.items():
                if not isinstance(group_data, dict):
                    continue
                # Storage 是框架内部持久化用的，不在 GUI 显示
                if group_name == "Storage":
                    continue
                
                group_frame = ttk.LabelFrame(scrollable_frame, text=f" {t(group_name)} ", padding=15)
                group_frame.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
                scrollable_frame.columnconfigure(col, weight=1)
                
                for i, (key, val) in enumerate(group_data.items()):
                    path = f"{task_name}.{group_name}.{key}"
                    
                    ttk.Label(group_frame, text=t(key), width=22, anchor="w").grid(row=i, column=0, padx=5, pady=5, sticky="w")
                    
                    # 检查是否有下拉框选项
                    options = self.get_options_for_field(group_name, key)

                    if options is not None:
                        var = tk.StringVar(value=str(val))
                        # 如果需要显示布尔值，将 yaml 的 true/false 转成可以理解的字符串
                        str_options = [str(opt).lower() if isinstance(opt, bool) else str(opt) for opt in options]
                        cb = ttk.Combobox(group_frame, textvariable=var, values=str_options, state="readonly", width=18)
                        cb.grid(row=i, column=1, sticky="ew", padx=5)
                        cb.bind("<<ComboboxSelected>>", lambda e, p=path, v=var, opts=options: self.on_combobox_change(p, v.get(), opts))
                        self.variables[path] = var
                        
                    elif isinstance(val, bool):
                        var = tk.BooleanVar(value=val)
                        cb = ttk.Checkbutton(group_frame, variable=var, command=lambda p=path, v=var: self.on_value_change(p, v.get()))
                        cb.grid(row=i, column=1, sticky="w", padx=5)
                        self.variables[path] = var
                    elif isinstance(val, int) or isinstance(val, float):
                        var = tk.StringVar(value=str(val))
                        entry = ttk.Entry(group_frame, textvariable=var, width=20)
                        entry.grid(row=i, column=1, sticky="ew", padx=5)
                        entry.bind("<FocusOut>", lambda e, p=path, v=var, t=type(val): self.on_entry_change(p, v.get(), t))
                        entry.bind("<Return>", lambda e, p=path, v=var, t=type(val): self.on_entry_change(p, v.get(), t))
                        self.variables[path] = var
                    elif isinstance(val, list):
                        var = tk.StringVar(value=json.dumps(val))
                        entry = ttk.Entry(group_frame, textvariable=var, width=20)
                        entry.grid(row=i, column=1, sticky="ew", padx=5)
                        entry.bind("<FocusOut>", lambda e, p=path, v=var, t=list: self.on_entry_change(p, v.get(), t))
                        entry.bind("<Return>", lambda e, p=path, v=var, t=list: self.on_entry_change(p, v.get(), t))
                        self.variables[path] = var
                    else:
                        var_val = "" if val is None else str(val)
                        var = tk.StringVar(value=var_val)
                        entry = ttk.Entry(group_frame, textvariable=var, width=20)
                        entry.grid(row=i, column=1, sticky="ew", padx=5)
                        entry.bind("<FocusOut>", lambda e, p=path, v=var, t=str: self.on_entry_change(p, v.get(), t))
                        entry.bind("<Return>", lambda e, p=path, v=var, t=str: self.on_entry_change(p, v.get(), t))
                        self.variables[path] = var
                        
                col += 1
                if col > 1:
                    col = 0
                    row += 1

    def on_value_change(self, path, new_val):
        self.update_config(path, new_val)

    def on_combobox_change(self, path, new_val_str, original_options):
        """处理 Combobox 的事件，需要进行类型转换匹配"""
        # 尝试匹配原始的布尔或整型数据，避免全部存成 string
        val = new_val_str
        for opt in original_options:
            if isinstance(opt, bool) and str(opt).lower() == new_val_str.lower():
                val = opt
                break
            elif str(opt) == new_val_str:
                val = opt
                break
                
        self.update_config(path, val)

    def on_entry_change(self, path, new_val, val_type):
        try:
            if val_type == int:
                val = int(new_val)
            elif val_type == float:
                val = float(new_val)
            elif val_type == list:
                val = json.loads(new_val)
                if not isinstance(val, list):
                    raise ValueError
            else:
                val = new_val if new_val != "" else None
            
            self.update_config(path, val)
        except Exception as e:
            messagebox.showerror("类型错误", f"{path} 需要 {val_type.__name__} 类型的值!\n错误信息: {str(e)}")
            self.refresh_config()

    def update_config(self, path, value):
        from module.config.deep import deep_set
        deep_set(self.config_data, path, value)
        self.pcr_config.modified[path] = value
        saved = self.pcr_config.save()
        if saved:
            print(f"✅ 配置已实时保存: {path} = {value}")

    def run_main_program(self):
        def _run():
            try:
                print("▶ 开始运行主程序...")
                pcr_tool = PCRGBATool(config_name=self.config_name)
                res = pcr_tool.loop()
                print(f"⏹ 主程序结束退出, 代码: {res}")
            except Exception as e:
                print(f"❌ 运行期间产生异常: {e}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        messagebox.showinfo("运行通知", "主程序已启动，请在控制台查看输出日志。")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigGUI(root)
    root.mainloop()
