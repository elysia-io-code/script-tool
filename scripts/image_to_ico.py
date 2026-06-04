#!/usr/bin/env python3
import io
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


SIZES = [16, 24, 32, 48, 64, 128, 256]


def main():
    if len(sys.argv) != 3:
        raise SystemExit("用法：image_to_ico.py <input-image> <output.ico>")

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        raise SystemExit(f"找不到图片：{input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries = make_png_entries(input_path)
    write_ico(output_path, entries)
    print(f"已生成：{output_path}")


def make_png_entries(input_path):
    try:
        from PIL import Image
    except ImportError:
        return make_png_entries_with_sips(input_path)

    with Image.open(input_path) as image:
        image = image.convert("RGBA")
        if image.width != image.height:
            print(f"提示：输入图片不是正方形，当前尺寸为 {image.width}x{image.height}，将居中裁剪。")
            image = crop_square(image)

        entries = []
        for size in SIZES:
            resized = image.resize((size, size), Image.LANCZOS)
            buffer = io.BytesIO()
            resized.save(buffer, format="PNG")
            entries.append((size, buffer.getvalue()))

    return entries


def make_png_entries_with_sips(input_path):
    if not shutil.which("sips"):
        raise SystemExit("缺少 Pillow，且当前系统找不到 sips。请先运行：python3 -m pip install Pillow")

    entries = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for size in SIZES:
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
