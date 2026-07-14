"""문제 팩 이미지 실물 분류 리포트"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

from kr_sets import KR_SETS

sys.stdout.reconfigure(encoding="utf-8")
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "set-boxes"

# 스크린샷에서 확인된 문제 코드
SUSPECT = {
    "EBB1", "XY5", "XY3a", "BW4", "XY6", "XY5a", "XY5b", "XY4", "XY3", "XY2",
    "CP6", "XY11", "XY8a", "XY9", "XY7", "SM2+", "SM1+", "SM8", "SM7", "SM6b", "SM6",
    "SM7a", "SM4a", "SM1C", "SM1M",
}


def classify(path: Path) -> list[str]:
    im = Image.open(path)
    w, h = im.size
    rgb = im.convert("RGB")
    rgba = im.convert("RGBA")
    ar = h / w if w else 0
    issues: list[str] = []

    if ar >= 1.85:
        issues.append(f"BANNER_TALL:{ar:.2f}")
    if ar <= 0.75 and w > 400:
        issues.append(f"DUAL_WIDE:{ar:.2f}")

    # checker: sample grid of mid-gray alternating in bg
    samples = []
    for x in range(0, min(w, 120), 4):
        for y in range(0, min(h, 120), 4):
            samples.append(rgb.getpixel((x, y)))
    light = sum(1 for r, g, b in samples if 170 <= r <= 210 and abs(r - g) < 12 and abs(g - b) < 12)
    darkg = sum(1 for r, g, b in samples if 90 <= r <= 140 and abs(r - g) < 12 and abs(g - b) < 12)
    if light > 8 and darkg > 8 and (light + darkg) / len(samples) > 0.25:
        issues.append("CHECKER")

    # white studio
    ring = []
    for x in range(0, w, max(1, w // 60)):
        for y in (0, 1, 2, h - 1, h - 2, max(0, h - 3)):
            ring.append(rgb.getpixel((x, min(y, h - 1))))
    wr = sum(1 for r, g, b in ring if r >= 245 and g >= 245 and b >= 245) / len(ring)
    if wr >= 0.2:
        issues.append(f"WHITE:{wr:.2f}")

    # mostly opaque white content area (CP6 style)
    whites = 0
    total = 0
    step = max(1, w // 40)
    for x in range(0, w, step):
        for y in range(0, h, step):
            total += 1
            r, g, b = rgb.getpixel((x, y))
            if r >= 245 and g >= 245 and b >= 245:
                whites += 1
    if whites / total >= 0.35:
        issues.append(f"WHITE_FILL:{whites/total:.2f}")

    return issues or ["OK"]


print(f"{'code':6} {'size':10} issues / name")
for s in KR_SETS:
    name = s.box_image_kr or ""
    if not name.startswith("/set-boxes/"):
        continue
    code = s.code
    p = PUBLIC / Path(name).name
    if not p.exists():
        print(f"{code:6} MISSING     {s.name_kr}")
        continue
    im = Image.open(p)
    tags = classify(p)
    mark = "" if tags == ["OK"] and code not in SUSPECT else " <<<"
    if tags != ["OK"] or code in SUSPECT:
        print(f"{code:6} {im.size[0]:4}x{im.size[1]:<4} {','.join(tags):30} {s.name_kr}{mark}")
