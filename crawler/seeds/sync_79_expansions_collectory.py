"""79개 확장팩의 C/U/R 제외 카드 항목을 Collectory 한국판 기준으로 동기화."""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from kr_sets import COLLECTORY_IDS, KR_SETS
from utils.db import get_supabase

OUT = Path("_audit_out/collectory_79_expansions_sync_apply.json")
EXCLUDED_SETS = {"CEL"}  # 25주년 기념 컬렉션: 정규 확장팩 79개에서 제외
LOW_RARITIES = {"C", "U", "R", "N", "M", "CM", "UM", "SA"}
RMAP = {"PROMO": "PR"}
RANK = {
    "RR": 4, "RRR": 5, "AR": 6, "CHR": 6, "PR": 6, "P": 6, "K": 7,
    "SR": 7, "SAR": 8, "UR": 9, "HR": 9, "CSR": 9, "SSR": 9,
    "MUR": 10, "MA": 10, "BWR": 10, "FUR": 10,
}
# Collectory가 일반 트레이너를 ACE로 분류한 항목. 프로젝트의 기존 시드 정책과 동일하게 제외한다.
SEED_SKIP = {
    ("SV8", "142/187"), ("SV8", "146/187"), ("SV8", "148/187"),
    ("SV8", "152/187"), ("SV8", "159/187"), ("SV8", "184/187"),
    ("SV8", "187/187"),
}


def load_all(sb, table: str, fields: str, **filters: object) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        query = sb.table(table).select(fields)
        for field, value in filters.items():
            query = query.eq(field, value)
        batch = query.range(start, start + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        start += 1000


def normalized_rarity(value: str) -> str:
    return RMAP.get((value or "").strip().upper(), (value or "").strip().upper())


def normalized_number(value: str) -> str:
    value = re.sub(r"\s+", "", value or "")
    match = re.match(r"^(\d+)/(\d+)", value)
    return f"{int(match.group(1)):03d}/{int(match.group(2)):03d}" if match else value


def source_is_korean(row: dict) -> bool:
    return (
        (row.get("region") or "").lower() == "kr"
        or "/cards/kr/" in (row.get("cdn_image_url") or "")
        or "pokemonkorea.co.kr" in (row.get("image_url") or "")
    )


def delete_card(sb, row: dict) -> None:
    for table in ("prices_kr", "prices_jp"):
        sb.table(table).delete().eq("card_id", row["id"]).execute()
    sb.table("cards").delete().eq("id", row["id"]).execute()


def source_payload(row: dict, set_id: int) -> dict:
    rank = normalized_rarity(row.get("rarity") or "")
    return {
        "set_id": set_id,
        "card_number": normalized_number(row.get("card_number") or ""),
        "name_kr": (row.get("name_ko") or row.get("name") or "").strip(),
        "name_jp": (row.get("name_ja") or row.get("name") or "").strip(),
        "name_en": (row.get("name_en") or row.get("name") or "").strip(),
        "rarity": rank,
        "rarity_rank": RANK.get(rank, 7),
        # Image population is intentionally separate; the previous reset cleared all images.
        "image_url": None,
        "image_color": "from-slate-600 via-slate-700 to-slate-800",
    }


def main() -> None:
    sb = get_supabase()
    db_sets = {
        row["set_code"]: row
        for row in load_all(sb, "card_sets", "id,set_code,name_kr")
    }
    targets = [meta for meta in KR_SETS if meta.code not in EXCLUDED_SETS]
    report = {
        "policy": "79 regular expansions; Korean Collectory source; exclude C/U/R and undefined —/blank rarity; images remain empty",
        "excluded_sets": sorted(EXCLUDED_SETS),
        "sets": {},
        "deleted": [],
        "added": [],
        "updated": [],
        "replaced_name": [],
        "skipped_source": [],
    }
    client = httpx.Client(timeout=90, headers={"User-Agent": "pokemon-card-price-collectory-sync/1.0"})

    for meta in targets:
        code = meta.code
        stats = {"source_raw": 0, "source_eligible": 0, "db_before_eligible": 0, "deleted": 0, "deleted_low": 0, "added": 0, "updated": 0, "replaced_name": 0, "skipped_undefined": 0}
        if code not in db_sets or code not in COLLECTORY_IDS:
            report["skipped_source"].append({"set_code": code, "reason": "missing_db_set_or_collectory_mapping"})
            continue
        try:
            response = client.get(f"https://collectory.cc/api/sets/{COLLECTORY_IDS[code]}/cards")
            response.raise_for_status()
            raw = response.json().get("cards", []) or []
        except Exception as exc:
            report["skipped_source"].append({"set_code": code, "reason": f"collectory_api:{type(exc).__name__}"})
            continue
        stats["source_raw"] = len(raw)
        source = []
        for row in raw:
            if not source_is_korean(row):
                continue
            rank = normalized_rarity(row.get("rarity") or "")
            if rank in LOW_RARITIES:
                continue
            if not rank or rank in {"—", "-"}:
                stats["skipped_undefined"] += 1
                continue
            if (code, normalized_number(row.get("card_number") or "")) in SEED_SKIP:
                stats["skipped_undefined"] += 1
                continue
            source.append(row)
        source_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in source:
            source_by_key[(normalized_number(row.get("card_number") or ""), normalized_rarity(row.get("rarity") or ""))].append(row)
        stats["source_eligible"] = sum(len(rows) for rows in source_by_key.values())

        db_rows = load_all(
            sb, "cards", "id,card_number,name_kr,name_jp,name_en,rarity,rarity_rank,image_url",
            set_id=db_sets[code]["id"],
        )
        # C/U/R과 현대 세트에서 같은 의미로 쓰이는 저등급 행은 대상에서 제거한다.
        for row in db_rows:
            row_key = (code, normalized_number(row.get("card_number") or ""))
            if normalized_rarity(row.get("rarity") or "") in LOW_RARITIES or row_key in SEED_SKIP:
                delete_card(sb, row)
                stats["deleted_low"] += 1
                report["deleted"].append({
                    "set_code": code,
                    "card_id": row["id"],
                    "card_number": row.get("card_number"),
                    "name_kr": row.get("name_kr"),
                    "rarity": row.get("rarity"),
                    "reason": "excluded_low_rarity",
                })
        db_rows = [row for row in db_rows if row.get("id") not in {
            item["card_id"] for item in report["deleted"] if item["set_code"] == code
        }]
        eligible_db = [row for row in db_rows if normalized_rarity(row.get("rarity") or "") not in LOW_RARITIES]
        stats["db_before_eligible"] = len(eligible_db)
        db_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in eligible_db:
            db_by_key[(normalized_number(row.get("card_number") or ""), normalized_rarity(row.get("rarity") or ""))].append(row)

        retained: dict[tuple[str, str], list[dict]] = defaultdict(list)
        # Delete DB-only rows, duplicates, and rows whose key is absent from Collectory.
        for key, rows in db_by_key.items():
            expected = source_by_key.get(key, [])
            for index, row in enumerate(rows):
                if index >= len(expected):
                    delete_card(sb, row)
                    stats["deleted"] += 1
                    report["deleted"].append({"set_code": code, "card_id": row["id"], "card_number": row.get("card_number"), "name_kr": row.get("name_kr"), "rarity": row.get("rarity"), "reason": "db_only_or_duplicate"})
                else:
                    retained[key].append(row)

        # Update exact-key rows; if the name is different, replace the row entirely.
        for key, rows in retained.items():
            for index, row in enumerate(rows):
                source_row = source_by_key[key][index]
                payload = source_payload(source_row, db_sets[code]["id"])
                old_name = (row.get("name_kr") or "").strip()
                new_name = payload["name_kr"]
                if old_name and new_name and old_name != new_name:
                    delete_card(sb, row)
                    inserted = sb.table("cards").insert(payload).execute().data or []
                    stats["replaced_name"] += 1
                    report["replaced_name"].append({"set_code": code, "old_card_id": row["id"], "new_card_id": inserted[0]["id"] if inserted else None, "card_number": payload["card_number"], "old_name_kr": old_name, "new_name_kr": new_name, "rarity": payload["rarity"]})
                else:
                    changed = sb.table("cards").update(payload).eq("id", row["id"]).execute().data or []
                    if changed:
                        stats["updated"] += 1
                        report["updated"].append({"set_code": code, "card_id": row["id"], "card_number": payload["card_number"], "name_kr": payload["name_kr"], "rarity": payload["rarity"]})

        # Add Collectory cards absent from DB.
        for key, source_rows in source_by_key.items():
            for index, source_row in enumerate(source_rows):
                if index < len(retained.get(key, [])):
                    continue
                payload = source_payload(source_row, db_sets[code]["id"])
                inserted = sb.table("cards").insert(payload).execute().data or []
                stats["added"] += 1
                report["added"].append({"set_code": code, "card_id": inserted[0]["id"] if inserted else None, "card_number": payload["card_number"], "name_kr": payload["name_kr"], "rarity": payload["rarity"]})
        report["sets"][code] = stats
        print(code, json.dumps(stats, ensure_ascii=False), flush=True)

    report["summary"] = {
        key: sum(stats.get(key, 0) for stats in report["sets"].values())
        for key in ("source_raw", "source_eligible", "db_before_eligible", "deleted", "deleted_low", "added", "updated", "replaced_name", "skipped_undefined")
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
