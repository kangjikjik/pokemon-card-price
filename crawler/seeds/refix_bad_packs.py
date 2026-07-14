"""스크린샷 문제 팩 — 단일 부스터만 골라 다크 캔버스로 교체.

규칙:
- 세로비 > 1.6 → 배너/인포그래픽 거부
- 가로비 < 0.85 & 넓은 이미지 → 듀얼이면 좌/우 크롭
- 체커보드/흰 배경 → 다크 캔버스 합성
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import httpx
from PIL import Image

from fix_white_canvas import to_black_canvas, ring_whiteness
from revert_featured_55 import write_set_images
from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from kr_sets import KR_SETS, KrSet

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "web" / "public" / "set-boxes"
AUDIT = Path(__file__).parent / "_img_audit" / "refix"
AUDIT.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

IMG_RE = re.compile(
    r"(https?://(?:data1\.pokemonkorea\.co\.kr|pokemonkorea\.co\.kr)[^\"'\s>]+\.(?:png|jpg|jpeg|PNG|JPG|JPEG))"
)

# 스크린샷 + 분류기로 확정된 문제 세트 + pokemoncard page
PAGES: dict[str, int] = {
    "SM8": 152,
    "SM7": 149,
    "SM6b": 140,
    "SM6": 132,
    "SM2+": 118,
    "SM1+": 110,
    "CP6": 89,
    "XY11": 83,
    "XY9": 62,
    "XY8a": 70,  # may need search
    "XY7": 55,
    "XY6": 48,
    "XY5a": 42,
    "XY5b": 42,
    "XY4": 36,
    "XY3": 30,
    "XY2": 24,
    "EBB1": 18,
    "XY5": 15,  # megalocannon page guess
    "XY3a": 12,
    "BW4": 8,
    "S1a": 250,
    "S1W": 220,
    "S1H": 220,
}

# 알려진 단일팩 / 크롭 소스 (육안·과거 검증)
KNOWN: dict[str, str] = {
    "SM8": "https://data1.pokemonkorea.co.kr/2018/11/2018-11-08_17-51-28-24380-1541667088.png",
    "SM7": "https://data1.pokemonkorea.co.kr/2018/10/2018-10-04_16-47-50-82250-1538641670.png",
    "SM6b": "https://data1.pokemonkorea.co.kr/2018/07/2018-07-12_11-20-18-79039-1531362018.png",
    "SM6": "https://data1.pokemonkorea.co.kr/2018/05/2018-05-24_15-30-22-73162-1527143422.png",
    "SM6a": "https://data1.pokemonkorea.co.kr/2018/06/2018-06-22_18-47-50-16043-1529660870.png",
    "SM2+": "https://data1.pokemonkorea.co.kr/2017/10/2017-10-24_18-33-58-94770-1508837638.png",
    "SM1+": "https://data1.pokemonkorea.co.kr/2017/05/2017-05-11_14-22-40-76242-1494480160.png",
    "SM4a": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
    "SM7a": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
    "CP6": "https://data1.pokemonkorea.co.kr/2016/09/2016-09-20_13-45-22-59022-1474346722.jpg",
    "XY8a": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY10_main_OuZo_4.jpg",
    "XY9": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY9_main_2.jpg",
    "XY7": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY7_main_3.jpg",
    "XY6": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY6_main_2.jpg",
    "XY4": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY4_main_5.jpg",
    "XY3": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY3_main_6.jpg",
    "XY2": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY2_main_7.jpg",
    "EBB1": "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_ex_battle_boost.png",
    "XY5": "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_mc.png",
    "XY3a": "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_plazmagail.png",
    "BW4": "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_darkrush.png",
    "S2": "https://data1.pokemonkorea.co.kr/2020/04/2020-04-09_15-43-53-72986-1586414633.png",
}

# 듀얼 팩 크롭 (좌/우)
DUAL_CROPS: dict[str, tuple[str, str]] = {
    # source, side
    "XY5a": ("http://pokemonkorea.co.kr/templates/default/content_image/card/XY5_main.jpg", "left"),
    "XY5b": ("http://pokemonkorea.co.kr/templates/default/content_image/card/XY5_main.jpg", "right"),
    "XY11": ("https://data1.pokemonkorea.co.kr/2016/07/2016-07-28_09-45-50-64547-1469666750.jpg", "left"),
}


def local_name(code: str) -> str:
    return f"{code.replace('+', 'plus')}.png"


def score_pack(im: Image.Image) -> float:
    w, h = im.size
    if w < 80 or h < 80:
        return -100
    ar = h / w
    score = 0.0
    # ideal pack portrait ~ 1.1–1.6 or product shot ~0.9–1.3
    if 0.9 <= ar <= 1.7:
        score += 40
    elif 0.75 <= ar < 0.9:
        score += 15  # slightly wide single
    elif ar > 2.0:
        score -= 80  # banner
    elif ar < 0.7:
        score -= 20  # dual-ish
    # prefer larger
    score += min(30, (w * h) ** 0.5 / 40)
    # penalize mostly white
    rgb = im.convert("RGB")
    step = max(1, w // 30)
    whites = 0
    n = 0
    for x in range(0, w, step):
        for y in range(0, h, step):
            r, g, b = rgb.getpixel((x, y))
            n += 1
            if r > 245 and g > 245 and b > 245:
                whites += 1
    if whites / n > 0.45:
        score -= 25
    return score


def crop_dual(im: Image.Image, side: str) -> Image.Image:
    w, h = im.size
    mid = w // 2
    if side == "left":
        return im.crop((0, 0, mid, h))
    return im.crop((mid, 0, w, h))


def fetch_page_candidates(page: int) -> list[str]:
    r = client.get(f"https://pokemoncard.co.kr/card/{page}")
    if r.status_code >= 400:
        return []
    urls = []
    seen = set()
    for u in IMG_RE.findall(r.text):
        if u in seen:
            continue
        seen.add(u)
        low = u.lower()
        if any(x in low for x in ("hover", "banner", "bg_", "gms", "collection", "wide", "1920")):
            continue
        urls.append(u)
    return urls


def pick_best(urls: list[str]) -> tuple[Image.Image | None, str, float]:
    best = None
    best_url = ""
    best_score = -999.0
    for u in urls:
        try:
            data = client.get(u).content
            im = Image.open(io.BytesIO(data))
        except Exception:
            continue
        sc = score_pack(im)
        print(f"    cand {sc:6.1f} {im.size} {u[-70:]}")
        if sc > best_score:
            best_score = sc
            best = im
            best_url = u
    return best, best_url, best_score


def process_code(code: str) -> bool:
    print(f"\n=== {code} ===")
    im = None
    src = ""

    if code in DUAL_CROPS:
        url, side = DUAL_CROPS[code]
        print(f"  dual crop {side} from {url[-50:]}")
        data = client.get(url).content
        raw = Image.open(io.BytesIO(data))
        im = crop_dual(raw, side)
        src = f"crop:{side}:{url}"
    elif code in KNOWN:
        url = KNOWN[code]
        print(f"  known {url[-60:]}")
        try:
            data = client.get(url).content
            im = Image.open(io.BytesIO(data))
            src = url
            sc = score_pack(im)
            print(f"  score={sc:.1f} size={im.size}")
            if sc < 0:
                print("  known rejected, try page")
                im = None
        except Exception as e:
            print(f"  known fail {e}")
            im = None

    if im is None and code in PAGES:
        cands = fetch_page_candidates(PAGES[code])
        if code in KNOWN:
            cands = [KNOWN[code]] + cands
        print(f"  page {PAGES[code]} cands={len(cands)}")
        im2, url2, sc = pick_best(cands)
        if im2 is not None and sc >= 0:
            im, src = im2, url2

    if im is None:
        print("  FAIL no image")
        return False

    # if still dual-wide, and code expects single, try half
    w, h = im.size
    if h / w < 0.85 and w > 400 and code not in ("CP6",):
        print("  auto-split wide image -> left half as fallback? skip split unless dual")
        # only auto for known dual pairs already handled

    out = to_black_canvas(im)
    # reject if result still banner-like tiny pack
    ow, oh = out.size
    path = PUBLIC / local_name(code)
    out.save(path, optimize=True)
    # also save audit
    out.save(AUDIT / f"{code}.png", optimize=True)
    wr = ring_whiteness(path)
    print(f"  SAVED {path.name} {out.size} ring_white={wr:.3f} src={src[-55:]}")
    return wr < 0.15


def main():
    # codes to fix from screenshots + classifier banners
    codes = [
        "SM8", "SM7", "SM6b", "SM6", "SM2+", "SM1+", "CP6",
        "XY11", "XY8a", "XY9", "XY7", "XY6", "XY5a", "XY5b",
        "XY4", "XY3", "XY2", "EBB1", "XY5", "XY3a", "BW4",
        "SM4a", "SM7a",
        "S1a", "S1W", "S1H",
    ]
    ok = 0
    fail = []
    for code in codes:
        try:
            if process_code(code):
                ok += 1
            else:
                fail.append(code)
        except Exception as e:
            print(f"  ERR {code}: {e}")
            fail.append(code)

    # update kr_sets / set-images for these to /set-boxes/
    fixes = {c: f"/set-boxes/{local_name(c)}" for c in codes if (PUBLIC / local_name(c)).exists()}
    updated = []
    for s in KR_SETS:
        if s.code in fixes:
            updated.append(KrSet(s.code, s.name_kr, s.released_at, fixes[s.code], s.box_image_jp))
        else:
            updated.append(s)
    write_kr_sets(updated)
    ensure_kr_sets_footer()
    write_set_images({s.code: s.box_image_kr for s in updated if s.box_image_kr})

    print(f"\nOK={ok} FAIL={fail}")
    (Path(__file__).parent / "_audit_out" / "refix_result.json").write_text(
        json.dumps({"ok": ok, "fail": fail, "fixes": fixes}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
