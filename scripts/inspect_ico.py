#!/usr/bin/env python3
import struct
import sys
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("用法：inspect_ico.py <icon.ico>")

    ico_path = Path(sys.argv[1])
    if not ico_path.exists():
        raise SystemExit(f"找不到 ICO 文件：{ico_path}")

    data = ico_path.read_bytes()
    entries = parse_ico(data)

    print(f"文件：{ico_path}")
    print(f"图片数量：{len(entries)}")
    print()

    for index, entry in enumerate(entries, start=1):
        print(
            f"{index}. {entry['width']}x{entry['height']} "
            f"{entry['bit_count']} bit，{entry['format']}，"
            f"{entry['size']} bytes，offset {entry['offset']}"
        )


def parse_ico(data):
    if len(data) < 6:
        raise SystemExit("文件过小，不是有效 ICO。")

    reserved, icon_type, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or icon_type not in {1, 2}:
        raise SystemExit("不是有效 ICO/CUR 文件。")

    needed = 6 + count * 16
    if len(data) < needed:
        raise SystemExit("ICO 目录不完整。")

    entries = []
    for index in range(count):
        offset = 6 + index * 16
        width, height, color_count, reserved, planes, bit_count, size, image_offset = struct.unpack_from(
            "<BBBBHHII",
            data,
            offset,
        )
        if reserved != 0:
            raise SystemExit("ICO 目录项格式异常。")

        actual_width = 256 if width == 0 else width
        actual_height = 256 if height == 0 else height
        image_data = data[image_offset : image_offset + size]

        entries.append(
            {
                "width": actual_width,
                "height": actual_height,
                "color_count": color_count,
                "planes": planes,
                "bit_count": bit_count,
                "size": size,
                "offset": image_offset,
                "format": detect_format(image_data),
            }
        )

    return entries


def detect_format(image_data):
    if image_data.startswith(PNG_SIGNATURE):
        return "PNG"
    if image_data.startswith(b"BM"):
        return "BMP"
    return "DIB/BMP"


if __name__ == "__main__":
    main()
