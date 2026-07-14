"""S1W/S1H: 전역 초록 제거 + 최대 연결요소 크롭."""
from __future__ import annotations

import io
import sys
from collections import deque
from pathlib import Path

import httpx
from PIL import Image

from fix_packs_v5 import to_dark_pack

sys.stdout.reconfigure(encoding="utf-8")
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "set-boxes"
AUDIT = Path(__file__).parent / "_img_audit" / "fix_round2"
BG = (15, 23, 42)
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
URL = "https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-07-55-87507-1580796475.png"
BOXES = {
    "S1W": (900, 1260, 1160, 1660),
    "S1H": (900, 1845, 1160, 2245),
}


def is_green_mat(r: int, g: int, b: int) -> bool:
    # bright / mid green poster mat
    if g > r + 18 and g > b + 8 and g > 50:
        return True
    # teal streaks
    if b > 40 and g > r + 10 and g > 60 and abs(g - b) < 40:
        return True
    return False


def largest_component(mask: list[list[bool]]) -> list[tuple[int, int]]:
    h, w = len(mask), len(mask[0])
    visited = [[False] * w for _ in range(h)]
    best: list[tuple[int, int]] = []
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or visited[y][x]:
                continue
            q = deque([(x, y)])
            visited[y][x] = True
            comp: list[tuple[int, int]] = []
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not visited[ny][nx]:
                        visited[ny][nx] = True
                        q.append((nx, ny))
            if len(comp) > len(best):
                best = comp
    return best


def process(raw: Image.Image) -> Image.Image:
    rgb = raw.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    # 1) paint all green mat to BG
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if is_green_mat(r, g, b) or (r > 248 and g > 248 and b > 248):
                px[x, y] = BG

    # 2) content mask = not BG and not near-black cosmic dust
    mask = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if (r, g, b) == BG:
                continue
            if r + g + b < 45:
                px[x, y] = BG
                continue
            mask[y][x] = True

    best = largest_component(mask)
    if len(best) < 500:
        return to_dark_pack(rgb)

    xs = [p[0] for p in best]
    ys = [p[1] for p in best]
    pad = 10
    box = (
        max(0, min(xs) - pad),
        max(0, min(ys) - pad),
        min(w, max(xs) + pad + 1),
        min(h, max(ys) + pad + 1),
    )
    sub = rgb.crop(box)
    # clear leftover BG-adjacent greenish fringe again
    sp = sub.load()
    sw, sh = sub.size
    for y in range(sh):
        for x in range(sw):
            r, g, b = sp[x, y]
            if is_green_mat(r, g, b):
                sp[x, y] = BG
    return to_dark_pack(sub)


def main():
    poster = Image.open(io.BytesIO(client.get(URL).content))
    for code, box in BOXES.items():
        raw = poster.crop(box)
        out = process(raw)
        out.save(PUBLIC / f"{code}.png", optimize=True)
        out.save(AUDIT / f"{code}_clean.png", optimize=True)
        print(code, "raw", raw.size, "->", out.size)


if __name__ == "__main__":
    main()
