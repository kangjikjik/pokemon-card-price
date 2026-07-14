"""전체 featured 박스 이미지 — 비율·중복 감사"""
from __future__ import annotations

import struct
from collections import defaultdict

import httpx
from kr_sets import KR_SETS

client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})


def png_size(data: bytes):
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    return None


def jpeg_size(data: bytes):
    if not data.startswith(b"\xff\xd8"):
        return None
    i = 2
    while i < len(data):
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break
        m = data[i]
        i += 1
        if m in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 3 : i + 7])
            return w, h
        if i + 1 >= len(data):
            break
        seg = struct.unpack(">H", data[i : i + 2])[0]
        i += seg
    return None


def dims(url: str):
    try:
        r = client.get(url)
        sz = png_size(r.content[:65536]) or jpeg_size(r.content[:65536])
        if sz:
            w, h = sz
            ratio = w / h if h else 0
            if ratio > 1.3:
                kind = "wide"
            elif ratio < 0.85:
                kind = "tall"
            else:
                kind = "box"
            return w, h, kind, ratio
    except Exception:
        pass
    return 0, 0, "?", 0


by_url: dict[str, list[str]] = defaultdict(list)
issues = []

for s in KR_SETS:
    url = s.box_image_kr or ""
    if not url:
        issues.append((s.code, "missing", url))
        continue
    w, h, kind, ratio = dims(url)
    by_url[url].append(s.code)
    bad_kw = any(k in url.lower() for k in ("hover", "banner", "gms05"))
    if kind == "wide" or bad_kw:
        issues.append((s.code, kind, f"{w}x{h} {url.split('/')[-1]}"))

print(f"wide/bad: {len(issues)}")
for row in issues:
    print(f"  {row[0]:6} {row[1]:6} {row[2]}")

print("\nduplicate URLs:")
for url, codes in sorted(by_url.items(), key=lambda x: -len(x[1])):
    if len(codes) > 1:
        print(f"  {codes} -> {url.split('/')[-1]}")
