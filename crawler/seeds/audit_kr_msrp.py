"""
featured 79세트 한국판 발매가(packKR/boxKR) 전수 감사.

출처: https://pokemoncard.co.kr/card/{pokemoncard_page}

실행:
  python audit_kr_msrp.py           # 리포트
  python audit_kr_msrp.py --json    # _audit_out/kr_msrp_audit.json 저장
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from kr_sets import KR_SETS  # noqa: E402
from verify_batch1_kr import scrape_page  # noqa: E402

OUT = Path(__file__).with_name("_audit_out") / "kr_msrp_audit.json"
SAVE = "--json" in sys.argv


def main() -> None:
    rows: list[dict] = []
    ok = mismatch = no_page = fail = 0

    print(f"{'code':6} {'page':>4} | {'exp_pack':>8} {'got_pack':>8} | {'exp_box':>8} {'got_box':>8} | status")
    print("-" * 72)

    for s in KR_SETS:
        page = s.pokemoncard_page
        if not page:
            rows.append(
                {
                    "code": s.code,
                    "name_kr": s.name_kr,
                    "page": 0,
                    "packKR": 0,
                    "boxKR": 0,
                    "expected_pack": s.msrp_pack_kr,
                    "expected_box": s.msrp_box_kr,
                    "status": "NO_PAGE",
                    "url": "",
                }
            )
            no_page += 1
            print(f"{s.code:6} {'—':>4} | {s.msrp_pack_kr:8} {'—':>8} | {s.msrp_box_kr:8} {'—':>8} | NO_PAGE")
            continue

        data = scrape_page(page)
        got_pack = data.get("pack") or 0
        got_box = data.get("box") or 0
        if data.get("status") != "OK":
            status = "SCRAPE_FAIL"
            fail += 1
        elif got_pack == s.msrp_pack_kr and got_box == s.msrp_box_kr:
            status = "OK"
            ok += 1
        else:
            status = "MISMATCH"
            mismatch += 1

        url = f"https://pokemoncard.co.kr/card/{page}"
        rows.append(
            {
                "code": s.code,
                "name_kr": s.name_kr,
                "page": page,
                "packKR": got_pack,
                "boxKR": got_box,
                "expected_pack": s.msrp_pack_kr,
                "expected_box": s.msrp_box_kr,
                "title": data.get("title", ""),
                "released_at": data.get("released_at", ""),
                "status": status,
                "url": url,
            }
        )
        print(
            f"{s.code:6} {page:4} | {s.msrp_pack_kr:8} {got_pack:8} | "
            f"{s.msrp_box_kr:8} {got_box:8} | {status}"
        )

    summary = {
        "sets": len(KR_SETS),
        "ok": ok,
        "mismatch": mismatch,
        "scrape_fail": fail,
        "no_page": no_page,
        "verified": ok,
    }
    print("-" * 72)
    print(summary)

    if SAVE:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(
            json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"saved {OUT}")


if __name__ == "__main__":
    main()
