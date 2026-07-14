"""
카탈로그 품질 전수 감사 (featured 79세트)

1) RR+ 이미지 누락
2) name_kr 일본어 잔존
3) rarity_rank 불일치
4) collectory RR+ 누락/등급 단일
5) JP MSRP 미기입

실행: python audit_catalog_quality.py
      python audit_catalog_quality.py --json  (리포트 저장)
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from fill_oldest_rr_plus import RR_PLUS, expected_catalog, MANUAL_SUPPLEMENTS
from kr_sets import KR_SETS, KR_BY_CODE
from lib.rarity_rank import rank_for_rarity
from seed_from_collectory import normalize_card_number

OUT = Path(__file__).with_name("_audit_out")
SAVE_JSON = "--json" in sys.argv

HANGUL = re.compile(r"[\uAC00-\uD7A3]")
JAPANESE = re.compile(r"[\u3040-\u30FF\u4E00-\u9FFF]")
MSRP_JSON = Path(__file__).with_name("_audit_out") / "jp_msrp_sources.json"


def load_msrp_missing() -> set[str]:
    if not MSRP_JSON.is_file():
        return set()
    rows = json.loads(MSRP_JSON.read_text(encoding="utf-8"))
    return {r["code"] for r in rows if not r.get("packJP")}


def has_japanese(t: str) -> bool:
    return bool(JAPANESE.search(t or ""))


def has_hangul(t: str) -> bool:
    return bool(HANGUL.search(t or ""))


def norm_key(num: str, rar: str) -> tuple[str, str]:
    n = normalize_card_number(num or "")
    if "/" in n:
        left, right = n.split("/", 1)
        if left.isdigit():
            left = left.zfill(3)
        n = f"{left}/{right}"
    return (n, rar or "")


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=90, follow_redirects=True)

    sets = sorted([s for s in KR_SETS if s.collectory_id], key=lambda s: (s.released_at, s.code))
    all_cards: list[dict] = []
    set_id_by_code: dict[str, int] = {}

    for s in sets:
        rows = sb.table("card_sets").select("id").eq("set_code", s.code).execute().data or []
        if not rows:
            continue
        set_id_by_code[s.code] = rows[0]["id"]
        cards = (
            sb.table("cards")
            .select("id,set_id,card_number,name_kr,name_jp,name_en,rarity,rarity_rank,image_url")
            .eq("set_id", rows[0]["id"])
            .execute()
            .data
            or []
        )
        for c in cards:
            c["_code"] = s.code
        all_cards.extend(cards)

    rr_cards = [c for c in all_cards if (c.get("rarity") or "") in RR_PLUS]
    no_img_rr = [c for c in rr_cards if not (c.get("image_url") or "").strip()]
    bad_names = [c for c in all_cards if has_japanese(c.get("name_kr") or "")]
    empty_kr = [c for c in all_cards if not has_hangul(c.get("name_kr") or "")]
    wrong_rank = [
        c for c in all_cards
        if rank_for_rarity(c.get("rarity")) != (c.get("rarity_rank") or 0)
    ]

    # per-set RR+ catalog vs DB
    rr_issues: list[dict] = []
    for s in sets:
        if s.code not in set_id_by_code:
            rr_issues.append({"code": s.code, "issue": "no_set_in_db"})
            continue
        db_cards = [c for c in all_cards if c["_code"] == s.code]
        db_rr = [c for c in db_cards if (c.get("rarity") or "") in RR_PLUS]
        grades = sorted({c.get("rarity") for c in db_rr})
        try:
            exp = expected_catalog(s.code, s.collectory_id, client)
        except Exception as e:
            rr_issues.append({"code": s.code, "issue": "catalog_error", "detail": str(e)})
            continue
        db_keys = {norm_key(c.get("card_number") or "", c.get("rarity") or "") for c in db_rr}
        exp_norm = {norm_key(k[0], k[1]): v for k, v in exp.items()}
        miss = [k for k in exp_norm if k not in db_keys]
        extra = [k for k in db_keys if k not in exp_norm]
        no_img_in_set = [c for c in db_rr if not c.get("image_url")]
        flags = []
        if miss:
            flags.append(f"miss={len(miss)}")
        if len(grades) <= 1 and len(db_rr) > 2:
            flags.append(f"single_grade={grades}")
        if len(db_rr) <= 2 and len(exp) > 5:
            flags.append("sparse")
        if no_img_in_set:
            flags.append(f"no_img={len(no_img_in_set)}")
        if flags:
            rr_issues.append({
                "code": s.code,
                "name_kr": s.name_kr,
                "db_rr": len(db_rr),
                "exp_rr": len(exp),
                "grades": grades,
                "flags": flags,
                "miss": [{"num": k[0], "rar": k[1], "name": exp_norm[k].get("name_ko") or exp_norm[k].get("name_en")} for k in miss[:20]],
                "no_img": [
                    {"num": c.get("card_number"), "rar": c.get("rarity"), "name": c.get("name_kr")}
                    for c in no_img_in_set[:10]
                ],
            })

    report = {
        "summary": {
            "sets": len(sets),
            "total_cards": len(all_cards),
            "rr_plus_cards": len(rr_cards),
            "no_image_rr": len(no_img_rr),
            "bad_name_kr_japanese": len(bad_names),
            "empty_name_kr": len(empty_kr),
            "wrong_rarity_rank": len(wrong_rank),
            "sets_with_rr_issues": len(rr_issues),
            "msrp_missing_jp": sorted(load_msrp_missing()),
            "manual_supplement_sets": list(MANUAL_SUPPLEMENTS.keys()),
        },
        "no_image_rr_samples": [
            {"code": c["_code"], "num": c.get("card_number"), "rar": c.get("rarity"), "name": c.get("name_kr")}
            for c in no_img_rr[:30]
        ],
        "bad_name_samples": [
            {"code": c["_code"], "name_kr": c.get("name_kr"), "name_jp": c.get("name_jp")}
            for c in bad_names[:30]
        ],
        "rr_issues": rr_issues,
    }

    print("=== 카탈로그 품질 감사 ===")
    for k, v in report["summary"].items():
        print(f"  {k}: {v}")
    print(f"\n문제 세트 (RR+/이미지): {len(rr_issues)}")
    for item in rr_issues:
        print(f"  {item['code']:8} {item.get('flags', [item.get('issue')])}")

    if SAVE_JSON:
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / "catalog_quality_report.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
