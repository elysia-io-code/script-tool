#!/usr/bin/env python3
import io
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_SIZES = [16, 24, 32, 48, 64, 128, 256]


def main():
    if len(sys.argv) not in {3, 4}:
        raise SystemExit("用法：image_to_ico.py <input-image> <output.ico> [sizes]")

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    sizes = parse_sizes(sys.argv[3] if len(sys.argv) == 4 else "")

    if not input_path.exists():
        raise SystemExit(f"找不到图片：{input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries = make_png_entries(input_path, sizes)
    write_ico(output_path, entries)
    print(f"已生成：{output_path}")
    print(f"包含尺寸：{', '.join(f'{size}x{size}' for size in sizes)}")


def parse_sizes(value):
    if not value:
        return DEFAULT_SIZES

    sizes = []
    for item in value.replace("，", ",").split(","):
        item = item.strip().lower().replace("x", "")
        if not item:
            continue
        try:
            size = int(item)
        except ValueError:
            raise SystemExit(f"尺寸不是数字：{item}")
        if size < 1 or size > 256:
            raise SystemExit(f"ICO 尺寸必须在 1 到 256 之间：{size}")
        if size not in sizes:
            sizes.append(size)

    if not sizes:
        raise SystemExit("至少选择一个 ICO 尺寸。")
    return sizes


def make_png_entries(input_path, sizes):
    try:
        from PIL import Image
    except ImportError:
        return make_png_entries_with_sips(input_path, sizes)

    with Image.open(input_path) as image:
        image = image.convert("RGBA")
        if image.width != image.height:
            print(f"提示：输入图片不是正方形，当前尺寸为 {image.width}x{image.height}，将居中裁剪。")
            image = crop_square(image)

        entries = []
        for size in sizes:
            resized = image.resize((size, size), Image.LANCZOS)
            buffer = io.BytesIO()
            resized.save(buffer, format="PNG")
            entries.append((size, buffer.getvalue()))

    return entries


def make_png_entries_with_sips(input_path, sizes):
    if not shutil.which("sips"):
        raise SystemExit("缺少 Pillow，且当前系统找不到 sips。请先运行：python3 -m pip install Pillow")

    entries = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for size in sizes:
            png_path = temp_root / f"icon-{size}.png"
            result = subprocess.run(
                ["sips", "-s", "format", "png", "-z", str(size), str(size), str(input_path), "--out", str(png_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "sips 生成 PNG 失败")
            entries.append((size, png_path.read_bytes()))

    return entries


def crop_square(image):
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def write_ico(output_path, entries):
    header_size = 6
    directory_size = 16 * len(entries)
    offset = header_size + directory_size

    with output_path.open("wb") as file:
        file.write(struct.pack("<HHH", 0, 1, len(entries)))

        for size, data in entries:
            width_byte = 0 if size >= 256 else size
            height_byte = 0 if size >= 256 else size
            file.write(
                struct.pack(
                    "<BBBBHHII",
                    width_byte,
                    height_byte,
                    0,
                    0,
                    1,
                    32,
                    len(data),
                    offset,
                )
            )
            offset += len(data)

        for _size, data in entries:
            file.write(data)


if __name__ == "__main__":
    main()
