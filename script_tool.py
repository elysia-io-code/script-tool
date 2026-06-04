#!/usr/bin/env python3
import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from string import Template
from tkinter import (
    BooleanVar,
    END,
    Listbox,
    StringVar,
    Text,
    Tk,
    filedialog,
    messagebox,
)
from tkinter import font
from tkinter import ttk


ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "scripts.json"


COLORS = {
    "bg": "#f4f6f8",
    "panel": "#ffffff",
    "sidebar": "#17202a",
    "sidebar_muted": "#9aa6b2",
    "line": "#d8dee6",
    "text": "#17202a",
    "muted": "#5d6b7a",
    "primary": "#2563eb",
    "primary_active": "#1d4ed8",
    "terminal": "#0f1720",
    "terminal_text": "#dbe7f3",
}


class ScriptTool:
    def __init__(self, root):
        self.root = root
        self.root.title("脚本工具")
        self.root.geometry("980x640")
        self.root.minsize(860, 560)
        self.root.configure(bg=COLORS["bg"])

        self.scripts = self.load_scripts()
        self.current_script = None
        self.field_vars = {}
        self.output_queue = queue.Queue()
        self.running = False

        self.configure_styles()
        self.build_layout()
        self.root.after(100, self.drain_output_queue)

    def configure_styles(self):
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Arial", size=13)
        self.root.option_add("*Font", default_font)

        self.style.configure("App.TFrame", background=COLORS["bg"])
        self.style.configure("Panel.TFrame", background=COLORS["panel"])
        self.style.configure("Sidebar.TFrame", background=COLORS["sidebar"])
        self.style.configure("Field.TFrame", background=COLORS["panel"])

        self.style.configure("SidebarTitle.TLabel", background=COLORS["sidebar"], foreground="#ffffff", font=("Arial", 18, "bold"))
        self.style.configure("SidebarHint.TLabel", background=COLORS["sidebar"], foreground=COLORS["sidebar_muted"], font=("Arial", 11))
        self.style.configure("Title.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Arial", 24, "bold"))
        self.style.configure("Desc.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=("Arial", 13))
        self.style.configure("Section.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Arial", 14, "bold"))
        self.style.configure("FieldLabel.TLabel", background=COLORS["panel"], foreground="#334155", font=("Arial", 13))
        self.style.configure("Status.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Arial", 12))

        self.style.configure("TEntry", padding=(8, 7), fieldbackground="#ffffff", bordercolor=COLORS["line"])
        self.style.configure("TCombobox", padding=(8, 7), fieldbackground="#ffffff")
        self.style.configure("Primary.TButton", padding=(18, 8), background=COLORS["primary"], foreground="#ffffff", borderwidth=0)
        self.style.map("Primary.TButton", background=[("active", COLORS["primary_active"]), ("disabled", "#94a3b8")])
        self.style.configure("Secondary.TButton", padding=(14, 8), background="#ffffff", foreground=COLORS["text"], bordercolor=COLORS["line"])
        self.style.configure("Path.TButton", padding=(12, 7), background="#ffffff", foreground=COLORS["text"], bordercolor=COLORS["line"])

    def load_scripts(self):
        if not CONFIG_PATH.exists():
            messagebox.showerror("配置缺失", f"找不到配置文件：{CONFIG_PATH}")
            return []

        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception as exc:
            messagebox.showerror("配置错误", f"读取 scripts.json 失败：{exc}")
            return []

        return data.get("scripts", [])

    def build_layout(self):
        container = ttk.Frame(self.root, style="App.TFrame", padding=18)
        container.pack(fill="both", expand=True)

        left = ttk.Frame(container, width=270, style="Sidebar.TFrame", padding=(16, 18))
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ttk.Label(left, text="脚本工具", style="SidebarTitle.TLabel", anchor="w").pack(fill="x")
        ttk.Label(left, text=f"{len(self.scripts)} 个可用脚本", style="SidebarHint.TLabel", anchor="w").pack(fill="x", pady=(4, 16))
        self.script_list = Listbox(
            left,
            exportselection=False,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            bg=COLORS["sidebar"],
            fg="#e8eef5",
            selectbackground="#ffffff",
            selectforeground=COLORS["text"],
            font=("Arial", 13),
            relief="flat",
        )
        self.script_list.pack(fill="both", expand=True)
        self.script_list.bind("<<ListboxSelect>>", self.on_script_select)

        for script in self.scripts:
            self.script_list.insert(END, script.get("name", "未命名脚本"))

        right = ttk.Frame(container, style="Panel.TFrame", padding=(24, 22))
        right.pack(side="left", fill="both", expand=True)

        self.title_label = ttk.Label(right, text="选择一个脚本", anchor="w", style="Title.TLabel")
        self.title_label.pack(fill="x")

        self.desc_label = ttk.Label(right, text="", anchor="w", justify="left", wraplength=650, style="Desc.TLabel")
        self.desc_label.pack(fill="x", pady=(8, 18))

        self.form_frame = ttk.Frame(right, style="Panel.TFrame")
        self.form_frame.pack(fill="x")

        action_row = ttk.Frame(right, style="Panel.TFrame")
        action_row.pack(fill="x", pady=(18, 14))

        self.run_button = ttk.Button(action_row, text="运行", width=14, command=self.run_selected_script, state="disabled", style="Primary.TButton")
        self.run_button.pack(side="left")

        self.clear_button = ttk.Button(action_row, text="清空输出", width=14, command=self.clear_output, style="Secondary.TButton")
        self.clear_button.pack(side="left", padx=(8, 0))

        ttk.Label(right, text="输出", anchor="w", style="Section.TLabel").pack(fill="x")
        self.output = Text(
            right,
            height=16,
            wrap="word",
            bg=COLORS["terminal"],
            fg=COLORS["terminal_text"],
            insertbackground=COLORS["terminal_text"],
            borderwidth=0,
            padx=14,
            pady=12,
            font=("Menlo", 12),
            relief="flat",
        )
        self.output.pack(fill="both", expand=True, pady=(8, 0))

        self.status_label = ttk.Label(self.root, text="就绪", anchor="w", style="Status.TLabel")
        self.status_label.pack(fill="x", padx=18, pady=(0, 10))

        if self.scripts:
            self.script_list.selection_set(0)
            self.on_script_select(None)

    def on_script_select(self, _event):
        selection = self.script_list.curselection()
        if not selection:
            return

        self.current_script = self.scripts[selection[0]]
        self.field_vars = {}
        for child in self.form_frame.winfo_children():
            child.destroy()

        self.title_label.config(text=self.current_script.get("name", "未命名脚本"))
        self.desc_label.config(text=self.current_script.get("description", ""))
        self.run_button.config(state="normal")

        fields = self.current_script.get("inputs", [])
        if not fields:
            ttk.Label(self.form_frame, text="这个脚本不需要输入。", anchor="w", style="Desc.TLabel").pack(fill="x")
            return

        for field in fields:
            self.add_field(field)

    def add_field(self, field):
        field_id = field["id"]
        field_type = field.get("type", "text")
        default = str(field.get("default", ""))

        row = ttk.Frame(self.form_frame, style="Field.TFrame")
        row.pack(fill="x", pady=7)
        ttk.Label(row, text=field.get("label", field_id), width=18, anchor="w", style="FieldLabel.TLabel").pack(side="left")

        if field_type == "checkbox":
            var = BooleanVar(value=bool(field.get("default", False)))
            ttk.Checkbutton(row, variable=var).pack(side="left")
            self.field_vars[field_id] = (field, var)
            return

        var = StringVar(value=default)
        self.field_vars[field_id] = (field, var)

        if field_type == "select":
            options = field.get("options", [])
            if options and not var.get():
                var.set(options[0])
            ttk.Combobox(row, textvariable=var, values=options, state="readonly").pack(side="left", fill="x", expand=True)
            return

        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

        if field_type in {"file", "image", "folder", "save_file"}:
            ttk.Button(row, text="选择", command=lambda f=field, v=var: self.pick_path(f, v), style="Path.TButton").pack(side="left", padx=(8, 0))

    def pick_path(self, field, var):
        field_type = field.get("type")
        title = field.get("label", "选择")

        if field_type == "folder":
            value = filedialog.askdirectory(title=title)
        elif field_type == "save_file":
            value = filedialog.asksaveasfilename(
                title=title,
                initialfile=field.get("default", ""),
                defaultextension=field.get("default_extension", ""),
                filetypes=field.get("filetypes", [("所有文件", "*.*")]),
            )
        else:
            value = filedialog.askopenfilename(
                title=title,
                filetypes=field.get("filetypes", [("所有文件", "*.*")]),
            )

        if value:
            var.set(value)

    def collect_values(self):
        values = {}
        for field_id, (field, var) in self.field_vars.items():
            value = var.get()
            if field.get("required", False) and (value is None or str(value).strip() == ""):
                raise ValueError(f"请填写：{field.get('label', field_id)}")
            values[field_id] = value
        return values

    def build_command(self, values):
        command = self.current_script.get("command")
        if not command:
            raise ValueError("脚本配置缺少 command")

        values = {
            **values,
            "python": sys.executable,
            "root": str(ROOT_DIR),
        }
        return [Template(str(part)).safe_substitute(values) for part in command]

    def run_selected_script(self):
        if not self.current_script or self.running:
            return

        try:
            values = self.collect_values()
            command = self.build_command(values)
        except Exception as exc:
            messagebox.showerror("无法运行", str(exc))
            return

        self.running = True
        self.run_button.config(state="disabled")
        self.status_label.config(text=f"正在运行：{self.current_script.get('name', '脚本')}")
        self.write_output(f"\n$ {shell_quote(command)}\n")

        thread = threading.Thread(target=self.run_process, args=(command,), daemon=True)
        thread.start()

    def run_process(self, command):
        try:
            process = subprocess.Popen(
                command,
                cwd=str(ROOT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            assert process.stdout is not None
            for line in process.stdout:
                self.output_queue.put(line)

            code = process.wait()
            self.output_queue.put(f"\n进程结束，退出码：{code}\n")
        except Exception as exc:
            self.output_queue.put(f"\n运行失败：{exc}\n")
        finally:
            self.output_queue.put(("__done__", None))

    def drain_output_queue(self):
        try:
            while True:
                item = self.output_queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "__done__":
                    self.running = False
                    if self.current_script:
                        self.run_button.config(state="normal")
                    self.status_label.config(text="就绪")
                else:
                    self.write_output(item)
        except queue.Empty:
            pass
        self.root.after(100, self.drain_output_queue)

    def write_output(self, text):
        self.output.insert(END, text)
        self.output.see(END)

    def clear_output(self):
        self.output.delete("1.0", END)


def shell_quote(command):
    return " ".join("'" + part.replace("'", "'\\''") + "'" if " " in part else part for part in command)


def main():
    root = Tk()
    ScriptTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
