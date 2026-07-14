"""라운드2: S1W/S1H/SM12a/SM9/SM8b/SM4+/SM4/SM1C/SM1M/CP6 수정 + 동기화"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import httpx
from PIL import Image

from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from fix_packs_v5 import to_dark_pack, local_name
from kr_sets import KR_SETS, KrSet
from revert_featured_55 import write_set_images

sys.stdout.reconfigure(encoding="utf-8")
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public" / "set-boxes"
AUDIT = Path(__file__).parent / "_img_audit" / "fix_round2"
AUDIT.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
BG = (15, 23, 42)

# 단일 팩 썸네일 (포스터/박스 아님)
PACKS: dict[str, str] = {
    "SM12a": "https://data1.pokemonkorea.co.kr/2019/11/2019-11-27_14-54-21-95149-1574834061.png",
    "SM9": "https://data1.pokemonkorea.co.kr/2019/03/2019-03-13_10-30-00-72260-1552440600.jpg",
    "SM8b": "https://data1.pokemonkorea.co.kr/2019/02/2019-02-13_17-30-53-68445-1550046653.png",
}

DUALS: dict[str, tuple[str, str]] = {
    "SM4": ("https://data1.pokemonkorea.co.kr/2018/01/2018-01-08_10-25-24-68181-1515374724.png", "left"),
    "SM4+": ("https://data1.pokemonkorea.co.kr/2018/01/2018-01-08_10-25-24-68181-1515374724.png", "right"),
    "SM1C": ("https://data1.pokemonkorea.co.kr/2017/01/2017-01-30_14-43-58-88992-1485755038.png", "left"),
    "SM1M": ("https://data1.pokemonkorea.co.kr/2017/01/2017-01-30_14-43-58-88992-1485755038.png", "right"),
    # CP6 3팩 → 가운데 리자몽 팩만
    "CP6": ("https://data1.pokemonkorea.co.kr/2016/09/2016-09-20_13-45-22-59022-1474346722.jpg", "mid3"),
}

# 스토어 단일 팩 사진 (포스터 크롭보다 훨씬 깨끗)
S1_PACKS = {
    "S1W": "https://www.japan2uk.com/cdn/shop/files/Pokemon_Sword_s1W_Korean_Booster_Pack_1200x1200.png",
    "S1H": "https://www.japan2uk.com/cdn/shop/files/Pokemon_Shield_s1H_Korean_Booster_Pack_1200x1200.png",
}


def is_green_mat(r: int, g: int, b: int) -> bool:
    if g > r + 25 and g > b + 15 and g > 70:
        return True
    # dark green streaks
    if g >= r and g >= b and 40 <= g <= 120 and r < 90 and b < 90:
        return True
    return False


def extract_pack_on_green(im: Image.Image) -> Image.Image:
    """초록 매트 위 팩만 bbox로 잘라 다크 캔버스에 올림."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            r, g, b = rgb.getpixel((x, y))
            if not is_green_mat(r, g, b) and not (r > 245 and g > 245 and b > 245):
                # also skip near-black cosmic if any
                if r + g + b < 40:
                    continue
                xs.append(x)
                ys.append(y)
    if not xs:
        return to_dark_pack(im)
    pad = 4
    box = (
        max(0, min(xs) - pad),
        max(0, min(ys) - pad),
        min(w, max(xs) + pad + 1),
        min(h, max(ys) + pad + 1),
    )
    subject = rgb.crop(box)
    # replace remaining green in subject with BG
    sp = subject.load()
    sw, sh = subject.size
    for y in range(sh):
        for x in range(sw):
            r, g, b = sp[x, y]
            if is_green_mat(r, g, b) or (r >= 248 and g >= 248 and b >= 248):
                sp[x, y] = BG
    return to_dark_pack(subject)


def load_dual(url: str, how: str) -> Image.Image:
    im = Image.open(io.BytesIO(client.get(url).content))
    w, h = im.size
    if how == "left":
        return im.crop((0, 0, w // 2, h))
    if how == "right":
        return im.crop((w // 2, 0, w, h))
    if how == "mid3":
        third = w // 3
        return im.crop((third, 0, third * 2, h))
    return im


def save(code: str, im: Image.Image) -> None:
    out = to_dark_pack(im)
    path = PUBLIC / local_name(code)
    out.save(path, optimize=True)
    out.save(AUDIT / local_name(code), optimize=True)
    print(f"  {code}: {out.size} -> {path.name}")


def main():
    print("=== S1 store packs ===")
    for code, url in S1_PACKS.items():
        im = Image.open(io.BytesIO(client.get(url).content))
        save(code, im)

    print("=== single packs ===")
    for code, url in PACKS.items():
        im = Image.open(io.BytesIO(client.get(url).content))
        save(code, im)

    print("=== duals / CP6 ===")
    for code, (url, how) in DUALS.items():
        im = load_dual(url, how)
        save(code, im)

    codes = set(PACKS) | set(DUALS) | set(S1_PACKS)
    updated = []
    for s in KR_SETS:
        if s.code in codes and (PUBLIC / local_name(s.code)).exists():
            updated.append(
                KrSet(
                    s.code, s.name_kr, s.released_at, f"/set-boxes/{local_name(s.code)}",
                    s.bs_code, s.collectory_id, s.msrp_pack_kr, s.msrp_box_kr, s.pokemoncard_page,
                )
            )
        else:
            updated.append(s)
    write_kr_sets(updated)
    ensure_kr_sets_footer()
    write_set_images(updated)
    print("synced kr_sets + set-images")


if __name__ == "__main__":
    main()
