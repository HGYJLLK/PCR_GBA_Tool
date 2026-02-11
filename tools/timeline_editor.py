"""
时间轴 GUI 编辑器
可视化编辑战斗时间轴，支持添加、删除、导出时间轴配置

用法:
    python tools/timeline_editor.py
"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    print("错误: 需要安装 tkinter")
    print("请运行: pip install tk")
    sys.exit(1)


class TimelineEditor:
    """时间轴编辑器 GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("PCR 时间轴编辑器")
        self.root.geometry("800x600")
        
        # 时间轴数据
        self.timeline_name = tk.StringVar(value="我的轴")
        self.actions = []  # [(time_str, characters, description)]
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置 UI"""
        # 顶部：时间轴名称
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="时间轴名称:").pack(side=tk.LEFT)
        ttk.Entry(top_frame, textvariable=self.timeline_name, width=30).pack(side=tk.LEFT, padx=5)
        
        # 中间：添加动作表单
        form_frame = ttk.LabelFrame(self.root, text="添加动作", padding="10")
        form_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 时间输入
        ttk.Label(form_frame, text="时间 (分:秒):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.time_entry = ttk.Entry(form_frame, width=10)
        self.time_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        self.time_entry.insert(0, "1:24")
        
        # 角色选择
        ttk.Label(form_frame, text="角色:").grid(row=1, column=0, sticky=tk.W, pady=5)
        char_frame = ttk.Frame(form_frame)
        char_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        self.char_vars = []
        for i in range(1, 6):
            var = tk.BooleanVar()
            ttk.Checkbutton(char_frame, text=f"{i}号位", variable=var).pack(side=tk.LEFT, padx=5)
            self.char_vars.append(var)
        
        # 描述输入
        ttk.Label(form_frame, text="描述:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.desc_entry = ttk.Entry(form_frame, width=40)
        self.desc_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.desc_entry.insert(0, "开UB")
        
        # 添加按钮
        ttk.Button(form_frame, text="添加动作", command=self.add_action).grid(row=3, column=1, sticky=tk.W, pady=10)
        
        # 动作列表
        list_frame = ttk.LabelFrame(self.root, text="时间轴动作", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建 Treeview
        columns = ("时间", "角色", "描述")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 删除按钮
        button_row = ttk.Frame(list_frame)
        button_row.pack(pady=5, fill=tk.X)
        ttk.Button(button_row, text="删除选中", command=self.delete_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_row, text="保存到文件", command=self.save_to_file).pack(side=tk.LEFT, padx=5)
        
        # 底部：操作按钮
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="生成 Python 代码", command=self.generate_python, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导出 JSON", command=self.export_json, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导入 JSON", command=self.import_json, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空", command=self.clear_all, width=10).pack(side=tk.LEFT, padx=5)
        
    def add_action(self):
        """添加动作"""
        time_str = self.time_entry.get().strip()
        
        # 验证时间格式
        if not self.validate_time(time_str):
            messagebox.showerror("错误", "时间格式错误！请使用 '分:秒' 格式，例如 '1:24'")
            return
        
        # 获取选中的角色
        characters = [i+1 for i, var in enumerate(self.char_vars) if var.get()]
        if not characters:
            messagebox.showerror("错误", "请至少选择一个角色！")
            return
        
        description = self.desc_entry.get().strip()
        if not description:
            description = f"{time_str} - 开UB"
        
        # 添加到列表
        self.actions.append((time_str, characters, description))
        
        # 按时间排序（倒序）
        self.actions.sort(key=lambda x: self.time_to_seconds(x[0]), reverse=True)
        
        # 刷新显示
        self.refresh_tree()
        
        # 清空输入
        for var in self.char_vars:
            var.set(False)
        
    def delete_action(self):
        """删除选中的动作"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要删除的动作！")
            return
        
        for item in selected:
            index = self.tree.index(item)
            del self.actions[index]
        
        self.refresh_tree()
        
    def clear_all(self):
        """清空所有动作"""
        if messagebox.askyesno("确认", "确定要清空所有动作吗？"):
            self.actions.clear()
            self.refresh_tree()
    
    def refresh_tree(self):
        """刷新动作列表显示"""
        # 清空
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 重新添加
        for time_str, characters, description in self.actions:
            char_str = ", ".join([f"{c}号" for c in characters])
            self.tree.insert("", tk.END, values=(time_str, char_str, description))
    
    def validate_time(self, time_str):
        """验证时间格式"""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return False
            minutes = int(parts[0])
            seconds = int(parts[1])
            return 0 <= minutes <= 9 and 0 <= seconds <= 59
        except:
            return False
    
    def time_to_seconds(self, time_str):
        """时间字符串转秒数"""
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    
    def generate_python(self):
        """生成 Python 代码"""
        if not self.actions:
            messagebox.showwarning("提示", "时间轴为空！")
            return
        
        # 生成代码
        code_lines = [
            "from module.train.timeline import Timeline",
            "",
            f"timeline = Timeline(\"{self.timeline_name.get()}\")"
        ]
        
        for time_str, characters, description in self.actions:
            if len(characters) == 1:
                char_str = str(characters[0])
            else:
                char_str = str(characters)
            code_lines.append(f'timeline.add_action("{time_str}", {char_str}, "{description}")')
        
        code = "\n".join(code_lines)
        
        # 显示在新窗口
        self.show_code_window("Python 代码", code)
    
    def save_to_file(self):
        """保存到 test_battle_train.py 文件"""
        if not self.actions:
            messagebox.showwarning("提示", "时间轴为空！")
            return
        
        # 生成代码
        code_lines = []
        for time_str, characters, description in self.actions:
            if len(characters) == 1:
                char_str = str(characters[0])
            else:
                char_str = str(characters)
            code_lines.append(f'        timeline.add_action("{time_str}", {char_str}, "{description}")')
        
        code = "\n".join(code_lines)
        
        # 显示预览和确认
        preview = f"""将保存以下代码到 test_battle_train.py:

timeline = Timeline("{self.timeline_name.get()}")
{code}

确定要保存吗？"""
        
        if messagebox.askyesno("确认保存", preview):
            try:
                # 读取文件
                file_path = Path(__file__).parent.parent / "tests" / "test_battle_train.py"
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 查找并替换时间轴部分
                import re
                pattern = r'(# ========== 在这里自定义你的时间轴 ==========\s*\n)(.*?)(# ==========================================)'
                
                replacement = f'\\1        timeline = Timeline("{self.timeline_name.get()}")\n{code}\n        \\3'
                
                new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                
                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                messagebox.showinfo("成功", f"已保存到: {file_path}")
                
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
    
    def export_json(self):
        """导出为 JSON"""
        if not self.actions:
            messagebox.showwarning("提示", "时间轴为空！")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            data = {
                "name": self.timeline_name.get(),
                "actions": [
                    {
                        "time": time_str,
                        "characters": characters,
                        "description": description
                    }
                    for time_str, characters, description in self.actions
                ]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"已导出到: {filename}")
    
    def import_json(self):
        """从 JSON 导入"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.timeline_name.set(data.get("name", "导入的轴"))
                self.actions.clear()
                
                for action in data.get("actions", []):
                    self.actions.append((
                        action["time"],
                        action["characters"],
                        action["description"]
                    ))
                
                self.refresh_tree()
                messagebox.showinfo("成功", f"已导入 {len(self.actions)} 个动作")
                
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")
    
    def show_code_window(self, title, code):
        """显示代码窗口"""
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("600x400")
        
        # 文本框
        text = tk.Text(window, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", code)
        text.config(state=tk.DISABLED)
        
        # 复制按钮
        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
            messagebox.showinfo("成功", "已复制到剪贴板！")
        
        ttk.Button(window, text="复制到剪贴板", command=copy_to_clipboard).pack(pady=5)


def main():
    """主函数"""
    root = tk.Tk()
    app = TimelineEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
