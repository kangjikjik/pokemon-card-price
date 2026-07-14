"""3배치 15팩 — pokemoncard 검증값 확정"""
from __future__ import annotations

import json
import sys
import time

import httpx

from pick_batch3 import BATCH3_CODES, PAGE_HINTS, fetch_batch3_sets
from scrape_batch2 import pick_box_from_html
from verify_batch1_kr import scrape_page

OUT_PY = __file__.replace("build_batch3_verified.py", "batch3_verified.py")
OUT_JSON = __file__.replace("build_batch3_verified.py", "batch3_scraped.json")


def title_matches(code: str, name_kr: str, title: str) -> bool:
    t = title.replace(" ", "")
    n = name_kr.replace(" ", "")
    if code == "SM4a":
        return "배틀부스트" in title and "REMASTER" not in title.upper()
    if code in ("SM4+", "SM4") and "울트라" in title:
        return True
    if n in t or n[:4] in t:
        return True
    rules = {
        "SM6b": ("창공", "카리스마"),
        "SM6a": ("챔피언", "로드"),
        "SM6": ("드래곤", "스톰"),
        "SM5+": ("금단", "빛"),
        "SM5": ("울트라", "포스"),
        "SM4+": ("울트라", "문"),
        "SM4": ("울트라", "썬"),
        "SM4a": ("배틀부스트",),
        "SM2+": ("빛나는", "전설"),
        "SM1+": ("새로운", "시련"),
        "SM1M": ("문", "컬렉션"),
        "SM1C": ("썬", "컬렉션"),
        "CP6": ("20", "ANNIVERSARY"),
        "XY11": ("타오르는", "투사"),
        "XY9": ("천공", "분노"),
    }
    keys = rules.get(code, ())
    return all(k in title for k in keys) if keys else False


def find_page(code: str, name_kr: str, hint: int) -> dict | None:
    for page in [hint] + [hint + d for d in (-3, -2, -1, 1, 2, 3, 4, -4, 5)]:
        if page < 50:
            continue
        res = scrape_page(page)
        time.sleep(0.1)
        if res.get("status") != "OK":
            continue
        if title_matches(code, name_kr, res.get("title", "")):
            return res
    for page in range(max(50, hint - 15), hint + 20):
        res = scrape_page(page)
        time.sleep(0.06)
        if res.get("status") != "OK":
            continue
        if title_matches(code, name_kr, res.get("title", "")):
            return res
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    client = httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    sets = fetch_batch3_sets()
    if len(sets) != len(BATCH3_CODES):
        missing = set(BATCH3_CODES) - {s[0] for s in sets}
        print(f"WARN missing collectory: {missing}")

    rows = []
    print(f"{'code':6} | {'page':>4} | {'date':12} | {'pack':>6} | {'box':>7}")
    print("-" * 55)

    for code, name_kr, cid, bs in sets:
        hint = PAGE_HINTS.get(code, 0)
        res = find_page(code, name_kr, hint) if hint else None
        if not res:
            print(f"{code:6} | FAIL | {name_kr}")
            rows.append({"code": code, "status": "FAIL", "collectory_id": cid, "bs_code": bs, "name_kr": name_kr})
            continue

        page = res["page"]
        r = client.get(f"https://pokemoncard.co.kr/card/{page}", timeout=15)
        r.encoding = "utf-8"
        box = pick_box_from_html(r.text)
        row = {
            "code": code,
            "name_kr": name_kr,
            "released_at": res.get("released_at") or "",
            "box_image_kr": box,
            "bs_code": bs,
            "collectory_id": cid,
            "msrp_pack_kr": res.get("pack", 0),
            "msrp_box_kr": res.get("box", 0),
            "pokemoncard_page": page,
            "title": res.get("title", ""),
            "status": "OK",
        }
        rows.append(row)
        print(
            f"{code:6} | {page:4} | {row['released_at']:12} | "
            f"{row['msrp_pack_kr']:6} | {row['msrp_box_kr']:7}"
        )

    ok = [r for r in rows if r.get("status") == "OK"]
    if len(ok) != len(BATCH3_CODES):
        fail = [r["code"] for r in rows if r.get("status") != "OK"]
        print(f"\nFAIL codes: {fail}")
        sys.exit(1)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    lines = [
        '"""3배치 15팩 — pokemoncard.co.kr 검증값"""',
        "from __future__ import annotations",
        "from dataclasses import dataclass",
        "",
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
        "",
        "BATCH3_VERIFIED: list[VerifiedSet] = [",
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
    lines.extend(["]", "", "BATCH3_CODES = [s.code for s in BATCH3_VERIFIED]", ""])
    with open(OUT_PY, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote {OUT_PY} ({len(ok)} sets)")


if __name__ == "__main__":
    main()
