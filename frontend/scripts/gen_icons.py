#!/usr/bin/env python3
"""生成 PWA 图标(纯标准库, 无需 Pillow): 深色底 + 琥珀色圆环(太阳/每日)几何标记。

用法: python3 frontend/scripts/gen_icons.py
输出: frontend/public/icons/icon-192.png, icon-512.png
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ICON_DIR = Path(__file__).resolve().parent.parent / "public" / "icons"


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def make_png(size: int, path: Path) -> None:
    cx = cy = size / 2
    ring_r = size * 0.34
    ring_t = size * 0.05
    dot_r = size * 0.11

    rows = []
    for y in range(size):
        row = bytearray([0])  # filter type 0 (None)
        for x in range(size):
            d = math.hypot(x - cx, y - cy)
            # 底色: 深蓝灰 (slate-900)
            r, g, b = 15, 23, 42
            # 圆环 + 中心圆点: 琥珀 (amber-500)
            if abs(d - ring_r) < ring_t or d < dot_r:
                r, g, b = 245, 158, 11
            row += bytes((r, g, b))
        rows.append(bytes(row))

    raw = b"".join(rows)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(png)


if __name__ == "__main__":
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        out = ICON_DIR / f"icon-{size}.png"
        make_png(size, out)
        print(f"✓ 已生成 {out} ({size}x{size})")
