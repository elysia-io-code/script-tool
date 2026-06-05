# 脚本工具

一个可配置的桌面脚本启动器。运行后会显示原生窗口，选择脚本后根据配置动态渲染输入项，然后执行对应命令并显示输出。

## 功能

- 通过 `scripts.json` 配置脚本列表和输入项
- 支持文本、数字、文件、图片、目录、保存路径、下拉框、复选框等输入类型
- 脚本运行输出会显示在窗口底部
- 后续新增脚本时，不需要改界面代码

## 安装

克隆仓库：

```bash
git clone https://github.com/elysia-io-code/script-tool.git
cd script-tool
```

确认 Python 可用：

```bash
python3 --version
```

这个工具使用 Python 自带的 Tkinter 原生窗口。如果运行时报 `No module named '_tkinter'`，需要安装带 Tk 支持的 Python。

macOS Homebrew 示例：

```bash
brew install python-tk
```

如果你使用的是特定 Python 版本，例如 Python 3.14，可能需要：

```bash
brew install python-tk@3.14
```

## 运行

```bash
python3 script_tool.py
```

也可以在 Finder 里双击 `启动脚本工具.command`。

如果双击 `.command` 文件时 macOS 提示无法打开，可以在终端里执行：

```bash
chmod +x 启动脚本工具.command
```

## 新增脚本

1. 在 `scripts/` 目录里放脚本，例如 `scripts/demo.py`。
2. 在 `scripts.json` 里新增一项。

示例：

```json
{
  "id": "demo",
  "name": "示例脚本",
  "description": "演示文本输入和文件选择。",
  "command": ["${python}", "${root}/scripts/demo.py", "${name}", "${file}"],
  "inputs": [
    {"id": "name", "label": "名称", "type": "text", "required": true},
    {"id": "file", "label": "文件", "type": "file", "required": true}
  ]
}
```

可用输入类型：

- `text`：文本输入
- `number`：数字输入
- `file`：选择文件
- `image`：选择图片
- `folder`：选择目录
- `save_file`：选择保存路径
- `select`：下拉选择，需要配置 `options`
- `checkbox`：勾选框

命令模板可使用：

- `${python}`：当前 Python 解释器
- `${root}`：工具所在目录
- `${输入 id}`：用户填写或选择的值

## 内置示例

- 获取域名 SSL Pin：依赖系统 `openssl`
- 1024 图片生成 ICO：支持选择常用 ICO 尺寸；优先使用 `Pillow`，没有 Pillow 时会在 macOS 上自动使用系统 `sips`
- 查看 ICO 图片尺寸：读取 ico 文件中包含的图片数量、尺寸、位深、格式和数据大小

可选安装 Pillow：

```bash
python3 -m pip install Pillow
```
