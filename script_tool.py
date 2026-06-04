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
    Button,
    Checkbutton,
    END,
    Entry,
    Frame,
    Label,
    Listbox,
    OptionMenu,
    StringVar,
    Text,
    Tk,
    filedialog,
    messagebox,
)


ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "scripts.json"


class ScriptTool:
    def __init__(self, root):
        self.root = root
        self.root.title("脚本工具")
        self.root.geometry("980x640")
        self.root.minsize(860, 560)

        self.scripts = self.load_scripts()
        self.current_script = None
        self.field_vars = {}
        self.output_queue = queue.Queue()
        self.running = False

        self.build_layout()
        self.root.after(100, self.drain_output_queue)

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
        container = Frame(self.root, padx=16, pady=16)
        container.pack(fill="both", expand=True)

        left = Frame(container, width=260)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        Label(left, text="脚本列表", anchor="w").pack(fill="x")
        self.script_list = Listbox(left, exportselection=False)
        self.script_list.pack(fill="both", expand=True, pady=(8, 0))
        self.script_list.bind("<<ListboxSelect>>", self.on_script_select)

        for script in self.scripts:
            self.script_list.insert(END, script.get("name", "未命名脚本"))

        right = Frame(container, padx=18)
        right.pack(side="left", fill="both", expand=True)

        self.title_label = Label(right, text="选择一个脚本", anchor="w", font=("Arial", 18, "bold"))
        self.title_label.pack(fill="x")

        self.desc_label = Label(right, text="", anchor="w", justify="left", wraplength=650)
        self.desc_label.pack(fill="x", pady=(6, 14))

        self.form_frame = Frame(right)
        self.form_frame.pack(fill="x")

        action_row = Frame(right)
        action_row.pack(fill="x", pady=(12, 10))

        self.run_button = Button(action_row, text="运行", width=14, command=self.run_selected_script, state="disabled")
        self.run_button.pack(side="left")

        self.clear_button = Button(action_row, text="清空输出", width=14, command=self.clear_output)
        self.clear_button.pack(side="left", padx=(8, 0))

        Label(right, text="输出", anchor="w").pack(fill="x")
        self.output = Text(right, height=18, wrap="word")
        self.output.pack(fill="both", expand=True, pady=(8, 0))

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
            Label(self.form_frame, text="这个脚本不需要输入。", anchor="w").pack(fill="x")
            return

        for field in fields:
            self.add_field(field)

    def add_field(self, field):
        field_id = field["id"]
        field_type = field.get("type", "text")
        default = str(field.get("default", ""))

        row = Frame(self.form_frame)
        row.pack(fill="x", pady=5)
        Label(row, text=field.get("label", field_id), width=18, anchor="w").pack(side="left")

        if field_type == "checkbox":
            var = BooleanVar(value=bool(field.get("default", False)))
            Checkbutton(row, variable=var).pack(side="left")
            self.field_vars[field_id] = (field, var)
            return

        var = StringVar(value=default)
        self.field_vars[field_id] = (field, var)

        if field_type == "select":
            options = field.get("options", [])
            if options and not var.get():
                var.set(options[0])
            OptionMenu(row, var, *options).pack(side="left", fill="x", expand=True)
            return

        Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

        if field_type in {"file", "image", "folder", "save_file"}:
            Button(row, text="选择", command=lambda f=field, v=var: self.pick_path(f, v)).pack(side="left", padx=(8, 0))

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
