"""5개 팩 이미지를 XY11(타오르는 투사) 채움 비율에 맞춤."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "set-boxes"
AUDIT = Path(__file__).parent / "_img_audit" / "normalize_fill"
AUDIT.mkdir(parents=True, exist_ok=True)

BG = (15, 23, 42)
REF = "XY11.png"
TARGETS = ["SM2plus.png", "SM1plus.png", "SM1M.png", "SM1C.png", "CP6.png"]
TARGET_H_FILL = 0.79  # XY11 기준
CANVAS = 360


def is_bg(r: int, g: int, b: int) -> bool:
    if abs(r - BG[0]) + abs(g - BG[1]) + abs(b - BG[2]) <= 45:
        return True
    # near-black letterbox
    if r + g + b <= 55:
        return True
    # studio white / light gray
    if r >= 235 and g >= 235 and b >= 235:
        return True
    if r >= 210 and g >= 210 and b >= 210 and max(r, g, b) - min(r, g, b) < 18:
        return True
    return False


def content_bbox(im: Image.Image) -> tuple[int, int, int, int]:
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(h):
        for x in range(w):
            if not is_bg(*px[x, y]):
                xs.append(x)
                ys.append(y)
    if not xs:
        return 0, 0, w, h
    pad = 2
    return (
        max(0, min(xs) - pad),
        max(0, min(ys) - pad),
        min(w, max(xs) + pad + 1),
        min(h, max(ys) + pad + 1),
    )


def paint_bg(im: Image.Image) -> Image.Image:
    rgb = im.convert("RGB")
    px = rgb.load()
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            if is_bg(*px[x, y]):
                px[x, y] = BG
    return rgb


def fit_like_xy11(im: Image.Image) -> Image.Image:
    cleaned = paint_bg(im)
    box = content_bbox(cleaned)
    subject = cleaned.crop(box)
    # re-paint residual bg in subject
    subject = paint_bg(subject)
    sw, sh = subject.size
    if sh < 10 or sw < 10:
        return Image.new("RGB", (CANVAS, CANVAS), BG)

    target_h = int(CANVAS * TARGET_H_FILL)
    scale = target_h / sh
    nw = max(1, int(round(sw * scale)))
    nh = max(1, int(round(sh * scale)))
    # keep within canvas width with small side margin
    max_w = int(CANVAS * 0.92)
    if nw > max_w:
        scale = max_w / sw
        nw = max(1, int(round(sw * scale)))
        nh = max(1, int(round(sh * scale)))

    resized = subject.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (CANVAS, CANVAS), BG)
    canvas.paste(resized, ((CANVAS - nw) // 2, (CANVAS - nh) // 2))
    return canvas


def measure(path: Path) -> str:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    x0, y0, x1, y1 = content_bbox(paint_bg(im))
    bw, bh = x1 - x0, y1 - y0
    return f"{path.name}: {w}x{h} pack={bw}x{bh} h_fill={bh/h:.2f}"


def main() -> None:
    print("REF", measure(PUBLIC / REF))
    for name in TARGETS:
        src = PUBLIC / name
        before = measure(src)
        out = fit_like_xy11(Image.open(src))
        out.save(src, optimize=True)
        out.save(AUDIT / name, optimize=True)
        after = measure(src)
        print(f"- {before}")
        print(f"  -> {after}")


if __name__ == "__main__":
    main()
