"""
pokemoncard.co.kr / pokemon-card.com 제품 페이지에서 featured 15 발매가 검증

실행: python scrape_set_msrp.py  (crawler/seeds/ 폴더)
"""
from __future__ import annotations

import re
import sys

import httpx

from kr_sets import KR_SETS

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)
JP_PACK_RE = re.compile(r"希望小売価格[：:]\s*([\d,]+)\s*円")
JP_PACK_ALT = re.compile(r"([\d,]+)円（税込）")

JP_PRODUCT_URL: dict[str, tuple[str, str]] = {
    "MG6": ("アビスアイ", "https://www.pokemon-card.com/ex/m5/"),
    "MG5a": ("ニンジャスピナー", "https://www.pokemon-card.com/ex/m4/"),
    "MG5": ("ムニキスゼロ", "https://www.pokemon-card.com/ex/m3/"),
    "MG3a": ("メガシンフォニア", "https://www.pokemon-card.com/ex/m1/"),
    "MG4": ("インフェルノX", "https://www.pokemon-card.com/ex/m2/"),
    "MG3": ("メガブレイブ", "https://www.pokemon-card.com/ex/m1/"),
    "MG1a": ("熱風のアリーナ", "https://www.pokemon-card.com/products/sv/sv9a.html"),
    "MG2": ("ブラックボルト", "https://www.pokemon-card.com/ex/sv11/"),
    "SV8a": ("バトルパートナーズ", "https://www.pokemon-card.com/ex/sv9/"),
    "SV7": ("超電ブレイカー", "https://www.pokemon-card.com/ex/sv8/"),
    "SV8": ("テラスタルフェスex", "https://www.pokemon-card.com/ex/sv8a/"),
    "SV6a": ("楽園ドラゴーナ", "https://www.pokemon-card.com/products/sv/sv7a.html"),
    "SV6": ("ステラミラクル", "https://www.pokemon-card.com/ex/sv7/"),
    "SV5a": ("ナイトワンダラー", "https://www.pokemon-card.com/products/sv/sv6a.html"),
    "SV5K": ("変幻の仮面", "https://www.pokemon-card.com/ex/sv6/"),
    "SV5M": ("クリムゾンヘイズ", "https://www.pokemon-card.com/ex/sv5/"),
    "SV4x": ("サイバージャッジ", "https://www.pokemon-card.com/ex/sv4/"),
    "SV4": ("ワイルドフォース", "https://www.pokemon-card.com/ex/sv4/"),
    "SV4a": ("シャイニートレジャーex", "https://www.pokemon-card.com/ex/sv4a/"),
    "SV4K": ("古代の咆哮", "https://www.pokemon-card.com/ex/sv4/"),
    "SV4M": ("未来の一閃", "https://www.pokemon-card.com/ex/sv4/"),
    "SV3a": ("レイジングサーフ", "https://www.pokemon-card.com/products/sv/sv3a.html"),
    "SV3": ("黒炎の支配者", "https://www.pokemon-card.com/ex/sv3/"),
    "SV2a": ("ポケモンカード151", "https://www.pokemon-card.com/ex/sv2a/"),
    "SV2D": ("クレイバースト", "https://www.pokemon-card.com/ex/sv2/"),
}


def scrape_kr(pack_img_key: str) -> tuple[int, int, int]:
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    for page in range(600, 960):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        if pack_img_key not in r.text:
            continue
        m = KR_PRICE_RE.search(r.text)
        if not m:
            continue
        return page, int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    return 0, 0, 0


def scrape_jp(url: str) -> int:
    r = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
    m = JP_PACK_RE.search(r.text) or JP_PACK_ALT.search(r.text)
    return int(m.group(1).replace(",", "")) if m else 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ok = fail = 0
    print(f"{'code':5} | {'KR pack':>8} | {'KR box':>8} | {'page':>4} | {'JP pack':>7} | status")
    print("-" * 65)
    for s in KR_SETS:
        img_key = s.box_image_kr.split("/")[-1].replace(".png", "")
        page, pack_kr, box_kr = scrape_kr(img_key)
        jp_name, jp_url = JP_PRODUCT_URL[s.code]
        pack_jp = scrape_jp(jp_url)
        kr_ok = pack_kr == s.msrp_pack_kr and box_kr == s.msrp_box_kr and page == s.pokemoncard_page
        status = "OK" if kr_ok and pack_jp else "MISMATCH" if pack_kr else "FAIL"
        if status == "OK":
            ok += 1
        else:
            fail += 1
        print(f"{s.code:5} | {pack_kr:8} | {box_kr:8} | {page:4} | {pack_jp:7} | {status}")
        if not kr_ok and pack_kr:
            print(f"       expected KR {s.msrp_pack_kr}/{s.msrp_box_kr} page {s.pokemoncard_page}")
    print(f"\n{ok} OK, {fail} issues")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
