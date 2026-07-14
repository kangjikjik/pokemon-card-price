"""이미지 비율로 배너/박스 구분"""
from __future__ import annotations

import io
import struct
import httpx
from kr_sets import KR_SETS, KR_BY_CODE

client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})


def png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return w, h


def jpeg_size(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    i = 2
    while i < len(data):
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break
        marker = data[i]
        i += 1
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 3 : i + 7])
            return w, h
        if i + 1 >= len(data):
            break
        seg = struct.unpack(">H", data[i : i + 2])[0]
        i += seg
    return None


def image_dims(url: str) -> tuple[int, int, str]:
    try:
        r = client.get(url)
        data = r.content[:65536]
        sz = png_size(data) or jpeg_size(data)
        if sz:
            w, h = sz
            kind = "wide" if w > h * 1.3 else ("tall" if h > w * 1.2 else "square")
            return w, h, kind
    except Exception:
        pass
    return 0, 0, "?"


PROBLEM = ["SM5+", "SM5", "SM4+", "SM4", "SM4a", "SM7a", "SM12", "SM2+", "SM1M", "SM1C", "XY5a", "XY5b"]
for code in PROBLEM:
    s = KR_BY_CODE[code]
    w, h, kind = image_dims(s.box_image_kr)
    print(f"{code:6} {w:4}x{h:<4} {kind:5} {s.box_image_kr.split('/')[-1]}")
