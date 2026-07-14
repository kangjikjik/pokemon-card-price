"""Quick corner / ACE check"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "set-boxes"
from audit_packs_full import corner_whiteness, load_bytes
from kr_sets import KR_SETS

print("=== corner samples ===")
for code in ["SV8", "SV8a", "SV7", "S6H", "XY11", "CEL", "SM4a", "SM4"]:
    p = PUBLIC / f"{code}.png"
    if not p.exists():
        print(code, "MISSING")
        continue
    im = Image.open(p).convert("RGB")
    w, h = im.size
    data = p.read_bytes()
    wh = corner_whiteness(data)
    corners = [im.getpixel(pt) for pt in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (5, 5)]]
    print(f"{code:8} {w}x{h} wh={wh:.3f} corners={corners}")

print("\n=== re-audit summary (bg-only heuristic) ===")
# true bg: only outermost 3px ring average darkness
ok = soft = bad = 0
for s in KR_SETS:
    url = s.box_image_kr or ""
    data, kind = load_bytes(url) if url else (b"", "empty")
    if not data:
        print(f"{s.code} NO_DATA {kind}")
        bad += 1
        continue
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    ring = []
    for x in range(w):
        for y in range(min(3, h)):
            ring.append(im.getpixel((x, y)))
        for y in range(max(0, h - 3), h):
            ring.append(im.getpixel((x, y)))
    for y in range(h):
        for x in range(min(3, w)):
            ring.append(im.getpixel((x, y)))
        for x in range(max(0, w - 3), w):
            ring.append(im.getpixel((x, y)))
    white = sum(1 for r, g, b in ring if r >= 235 and g >= 235 and b >= 235)
    dark = sum(1 for r, g, b in ring if r + g + b < 120)
    wr = white / len(ring)
    dr = dark / len(ring)
    status = "OK" if wr < 0.15 or dr > 0.5 else ("SOFT" if wr < 0.35 else "WHITE")
    if status == "OK":
        ok += 1
    elif status == "SOFT":
        soft += 1
        print(f"  {s.code:6} ring_white={wr:.2f} dark={dr:.2f} SOFT {s.name_kr}")
    else:
        bad += 1
        print(f"  {s.code:6} ring_white={wr:.2f} dark={dr:.2f} WHITE {s.name_kr}")

print(f"\nring OK={ok} soft={soft} white/bad={bad}")
