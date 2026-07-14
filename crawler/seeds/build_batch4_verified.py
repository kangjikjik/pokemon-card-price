"""4배치 12팩 — pokemoncard 검증값 확정"""
from __future__ import annotations

import json
import sys
import time

import httpx

from pick_batch4 import BATCH4_CODES, PAGE_HINTS, fetch_batch4_sets
from probe_batch4 import DEFAULT_MSRP
from resolve_legacy_box_images import pick_box
from verify_batch1_kr import scrape_page

OUT_PY = __file__.replace("build_batch4_verified.py", "batch4_verified.py")
OUT_JSON = __file__.replace("build_batch4_verified.py", "batch4_scraped.json")

# probe_batch4 결과 반영
VERIFIED_PAGES = {
    "XY8a": 65,
    "XY7": 50,
    "XY6": 47,
    "XY5a": 44,
    "XY5b": 44,
    "XY4": 40,
    "XY3": 36,
    "XY2": 33,
    "XY5": 25,
    "XY3a": 9,
    "BW4": 13,
}


def title_ok(code: str, name_kr: str, title: str) -> bool:
    rules = {
        "XY8a": ("초능력", "제왕"),
        "XY7": ("밴디트",),
        "XY6": ("에메랄드",),
        "XY5a": ("가이아",),
        "XY5b": ("타이달",),
        "XY4": ("팬텀",),
        "XY3": ("라이징",),
        "XY2": ("와일드",),
        "EBB1": ("배틀", "부스트"),
        "XY5": ("메갈로",),
        "XY3a": ("플라스마게일",),
        "BW4": ("다크러시",),
    }
    keys = rules.get(code, ())
    return all(k in title for k in keys) if keys else name_kr[:3] in title


def find_ebb1(client: httpx.Client) -> int:
    import re
    from verify_batch1_kr import parse_release_date

    for p in range(1, 40):
        r = client.get(f"https://pokemoncard.co.kr/card/{p}", timeout=15)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        h3 = re.findall(r"<h3[^>]*>([^<]+)</h3>", r.text)
        if h3 and "EX" in h3[0] and "배틀" in h3[0] and "부스트" in h3[0]:
            return p
        time.sleep(0.04)
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    client = httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    sets = fetch_batch4_sets()
    pages = dict(VERIFIED_PAGES)
    ebb = find_ebb1(client)
    if ebb:
        pages["EBB1"] = ebb

    rows = []
    print(f"{'code':6} | {'page':>4} | {'date':12} | {'pack':>6} | {'box':>7} | img")
    print("-" * 75)

    for code, name_kr, cid, bs in sets:
        page = pages.get(code, PAGE_HINTS.get(code, 0))
        if not page:
            print(f"{code:6} | FAIL")
            rows.append({"code": code, "status": "FAIL", "collectory_id": cid, "bs_code": bs, "name_kr": name_kr})
            continue

        res = scrape_page(page)
        time.sleep(0.12)
        r = client.get(f"https://pokemoncard.co.kr/card/{page}", timeout=15)
        r.encoding = "utf-8"
        if not title_ok(code, name_kr, res.get("title", "")):
            print(f"{code:6} | TITLE_MISMATCH | {res.get('title','')}")
            rows.append({"code": code, "status": "FAIL", "collectory_id": cid})
            continue

        box = pick_box(r.text)
        def_m = DEFAULT_MSRP.get(code, (1000, 30000))
        pack = res.get("pack") or def_m[0]
        box_kr = res.get("box") or def_m[1]

        row = {
            "code": code,
            "name_kr": name_kr,
            "released_at": res.get("released_at") or "",
            "box_image_kr": box,
            "bs_code": bs,
            "collectory_id": cid,
            "msrp_pack_kr": pack,
            "msrp_box_kr": box_kr,
            "pokemoncard_page": page,
            "title": res.get("title", ""),
            "status": "OK" if box else "NO_IMG",
        }
        rows.append(row)
        flag = "OK" if box else "NO_IMG"
        print(
            f"{code:6} | {page:4} | {row['released_at']:12} | {pack:6} | {box_kr:7} | {flag}"
        )

    ok = [r for r in rows if r.get("status") == "OK" and r.get("box_image_kr")]
    fail = [r for r in rows if r not in ok]
    if fail:
        print(f"\nWARN: {len(fail)} without box image: {[r['code'] for r in fail]}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    lines = [
        '"""4배치 12팩 — pokemoncard.co.kr 검증값"""',
        "from __future__ import annotations",
        "from dataclasses import dataclass",
        "",
        "@dataclass(frozen=True)",
        "class VerifiedSet:",
        "    code: str",
        "    name_kr: str",
        "    released_at: str",
        "    box_image_kr: str",
        "    bs_code: str",
        "    collectory_id: str",
        "    msrp_pack_kr: int",
        "    msrp_box_kr: int",
        "    pokemoncard_page: int",
        "",
        "BATCH4_VERIFIED: list[VerifiedSet] = [",
    ]
    for r in ok:
        lines.append(
            f'    VerifiedSet(\n'
            f'        "{r["code"]}", "{r["name_kr"]}", "{r["released_at"]}",\n'
            f'        "{r["box_image_kr"]}",\n'
            f'        "{r["bs_code"]}", "{r["collectory_id"]}",\n'
            f'        {r["msrp_pack_kr"]}, {r["msrp_box_kr"]}, {r["pokemoncard_page"]},\n'
            f"    ),"
        )
    lines.extend(["]", "", "BATCH4_CODES = [s.code for s in BATCH4_VERIFIED]", ""])
    with open(OUT_PY, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nwrote {OUT_PY} OK={len(ok)}/{len(BATCH4_CODES)}")


if __name__ == "__main__":
    main()
