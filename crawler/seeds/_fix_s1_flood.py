"""Download S1 poster and try corner-flood only green removal + tight bbox."""
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
# slightly wider to include full pack tilt
BOXES = {
    "S1W": (900, 1260, 1160, 1660),
    "S1H": (900, 1845, 1160, 2245),
}


def is_green_mat(r: int, g: int, b: int) -> bool:
    if g > r + 20 and g > b + 10 and g > 55:
        return True
    if g >= r - 5 and g >= b - 5 and 35 <= g <= 130 and r < 100 and b < 100:
        return True
    return False


def corner_flood_remove(im: Image.Image) -> Image.Image:
    """Flood from corners through green/near-white only; leave pack intact."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    visited = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def try_seed(x: int, y: int) -> None:
        if not (0 <= x < w and 0 <= y < h):
            return
        r, g, b = px[x, y]
        if is_green_mat(r, g, b) or (r > 240 and g > 240 and b > 240):
            q.append((x, y))
            visited[y][x] = True

    for x in range(w):
        try_seed(x, 0)
        try_seed(x, h - 1)
    for y in range(h):
        try_seed(0, y)
        try_seed(w - 1, y)

    while q:
        x, y = q.popleft()
        px[x, y] = BG
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                r, g, b = px[nx, ny]
                if is_green_mat(r, g, b) or (r > 240 and g > 240 and b > 240):
                    visited[ny][nx] = True
                    q.append((nx, ny))

    # bbox of non-BG
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            if px[x, y] != BG:
                xs.append(x)
                ys.append(y)
    if not xs:
        return to_dark_pack(rgb)
    pad = 8
    cropped = rgb.crop(
        (max(0, min(xs) - pad), max(0, min(ys) - pad), min(w, max(xs) + pad + 1), min(h, max(ys) + pad + 1))
    )
    return to_dark_pack(cropped)


def main():
    poster = Image.open(io.BytesIO(client.get(URL).content))
    poster.save(AUDIT / "S1_poster_full.png")
    print("poster", poster.size)
    for code, box in BOXES.items():
        raw = poster.crop(box)
        raw.save(AUDIT / f"raw_{code}.png")
        out = corner_flood_remove(raw)
        out.save(PUBLIC / f"{code}.png", optimize=True)
        out.save(AUDIT / f"{code}_flood.png", optimize=True)
        print(code, out.size)


if __name__ == "__main__":
    main()
