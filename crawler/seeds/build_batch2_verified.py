"""batch2 검증값 확정 — pokemoncard 페이지 스크랩 + 박스이미지"""
from __future__ import annotations

import json
import sys
import time

import httpx

from scrape_batch2 import BATCH2_SETS, pick_box_from_html
from verify_batch1_kr import scrape_page

# verify_batch2_pages + 수동 보완 (S1W/S1H/SM12a)
PAGE_MAP: dict[str, int] = {
    "S2": 297,
    "S1a": 291,
    "S1W": 286,
    "S1H": 286,
    "SM12a": 271,
    "SM12": 261,
    "SM11b": 257,
    "SM11a": 211,
    "SM10": 180,
    "SM9": 166,
    "SM8b": 163,
    "SM9a": 156,
    "SM8": 152,
    "SM7": 149,
    "SM7a": 120,
}

OUT_PY = __file__.replace("build_batch2_verified.py", "batch2_verified.py")
OUT_JSON = __file__.replace("build_batch2_verified.py", "batch2_scraped.json")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    client = httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    meta_by = {cid: (code, name, bs) for code, name, cid, bs in BATCH2_SETS}
    rows = []

    for code, name_kr, cid, bs in BATCH2_SETS:
        page = PAGE_MAP[code]
        res = scrape_page(page)
        time.sleep(0.15)
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
        print(f"{code:6} {row['released_at']} p{page} {row['msrp_pack_kr']}/{row['msrp_box_kr']}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    lines = [
        '"""2배치 15팩 — pokemoncard.co.kr 검증값"""',
        "from __future__ import annotations",
        "",
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
        "BATCH2_VERIFIED: list[VerifiedSet] = [",
    ]
    for r in rows:
        lines.append(
            f'    VerifiedSet(\n'
            f'        "{r["code"]}", "{r["name_kr"]}", "{r["released_at"]}",\n'
            f'        "{r["box_image_kr"]}",\n'
            f'        "{r["bs_code"]}", "{r["collectory_id"]}",\n'
            f'        {r["msrp_pack_kr"]}, {r["msrp_box_kr"]}, {r["pokemoncard_page"]},\n'
            f"    ),"
        )
    lines.extend([
        "]",
        "",
        "BATCH2_CODES = [s.code for s in BATCH2_VERIFIED]",
        "",
    ])
    with open(OUT_PY, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote {OUT_PY}")


if __name__ == "__main__":
    main()
