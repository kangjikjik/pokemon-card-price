"""pokemoncard.co.kr — 타임라인 갭 45세트 발매가·페이지 검증"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

from build_gap_codes import rows as GAP_ROWS

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)
OUT = Path(__file__).with_name("timeline_gaps_msrp.json")


def img_key(url: str) -> str:
    if not url:
        return ""
    base = url.rsplit("/", 1)[-1]
    return base.replace(".png", "").replace(".jpg", "").replace(".PNG", "")[:24]


def scrape_one(c: httpx.Client, code: str, name: str, img: str) -> dict:
    key = img_key(img)
    needles = [name, name.replace(" ", ""), name[:4], name[:6]]
    page_min, page_max = 80, 960
    if code.startswith(("BW", "XY", "SM", "CP", "EBB", "S1", "S2")) and not code.startswith("SV"):
        page_max = 400
    for page in range(page_min, page_max):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        hit = (key and key in r.text) or any(
            n and len(n) >= 2 and (n in r.text or n in r.text.replace(" ", ""))
            for n in needles
        )
        if not hit:
            continue
        m = KR_PRICE_RE.search(r.text)
        if not m:
            continue
        return {
            "code": code,
            "page": page,
            "pack": int(m.group(1).replace(",", "")),
            "box": int(m.group(2).replace(",", "")),
            "status": "OK",
        }
    return {"code": code, "page": 0, "pack": 0, "box": 0, "status": "FAIL"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    results = []
    ok = 0
    print(f"{'code':6} | {'page':>4} | {'pack':>6} | {'box':>7} | status | name")
    print("-" * 70)
    for row in GAP_ROWS:
        code = row["code"]
        name = row["name_kr"]
        img = row["box_image_kr"]
        res = scrape_one(c, code, name, img)
        res["name_kr"] = name
        res["released_at"] = row["released_at"]
        results.append(res)
        if res["status"] == "OK":
            ok += 1
        print(
            f"{code:6} | {res['page']:4} | {res['pack']:6} | {res['box']:7} | "
            f"{res['status']:6} | {name[:28]}"
        )
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nverified {ok}/{len(results)} -> {OUT.name}")


if __name__ == "__main__":
    main()
