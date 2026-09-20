"""2018-2022 세트의 현재 이미지 URL을 Collectory 한국판 원본과 읽기 전용 대조."""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from kr_sets import COLLECTORY_IDS
from utils.db import get_supabase

OUT = Path("_audit_out/legacy_image_source_audit.json")
LOW = {"C", "U", "R", "N", "CM", "UM"}
RMAP = {"PROMO": "PR"}


def num(value: str) -> int | None:
    match = re.search(r"(\d+)", value or "")
    return int(match.group(1)) if match else None


def rarity(value: str) -> str:
    return RMAP.get((value or "").upper(), (value or "").upper())


def key(number: str, rank: str) -> tuple[int | None, str]:
    return num(number), rarity(rank)


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


def korean_image(row: dict) -> str:
    for value in (row.get("cdn_image_url"), row.get("image_url")):
        value = (value or "").split("?", 1)[0]
        if "/cards/kr/" in value or "pokemonkorea.co.kr" in value:
            return value
    return ""


def url_hint(url: str) -> tuple[int, int] | None:
    path = urlparse((url or "").split("?", 1)[0]).path
    match = re.search(r"(?:^|/)(\d{1,3})_(\d{1,3})(?:[^/]*)\.(?:png|jpe?g|webp)$", path, re.I)
    return (int(match.group(1)), int(match.group(2))) if match else None


def main() -> None:
    sb = get_supabase()
    sets = load_all(sb, "card_sets", "id,set_code,name_kr,released_at")
    targets = [
        row for row in sets
        if row.get("released_at")
        and "2018-01-01" <= row["released_at"] <= "2022-12-31"
        and row["set_code"] in COLLECTORY_IDS
    ]
    report = {
        "scope": "2018-2022 sets; all DB cards with images; Korean Collectory reference",
        "sets_checked": len(targets),
        "cards_checked": 0,
        "definite_url_number_mismatches": [],
        "definite_collectory_reference_mismatches": [],
        "non_korean_or_untrusted_sources": [],
        "no_collectory_reference": [],
        "by_set": {},
    }
    client = httpx.Client(timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    for meta in targets:
        code = meta["set_code"]
        try:
            raw = client.get(f"https://collectory.cc/api/sets/{COLLECTORY_IDS[code]}/cards").raise_for_status()
            source_raw = raw.json().get("cards", [])
        except Exception as exc:
            report["by_set"][code] = {"name": meta["name_kr"], "api_error": type(exc).__name__}
            continue
        source = defaultdict(list)
        for row in source_raw:
            image = korean_image(row)
            if image:
                source[key(row.get("card_number", ""), row.get("rarity", ""))].append(image)
        cards = [
            row for row in load_all(
                sb, "cards", "id,set_id,card_number,name_kr,rarity,image_url", set_id=meta["id"]
            ) if (row.get("image_url") or "").strip()
        ]
        stats = {"cards_with_images": len(cards), "url_number_mismatch": 0, "collectory_mismatch": 0, "non_korean": 0, "no_reference": 0}
        for card in cards:
            report["cards_checked"] += 1
            current = (card.get("image_url") or "").split("?", 1)[0]
            current_host = urlparse(current).netloc
            item = {
                "set_code": code,
                "set_name": meta["name_kr"],
                "card_id": card["id"],
                "card_number": card.get("card_number"),
                "name_kr": card.get("name_kr"),
                "rarity": card.get("rarity"),
                "image_url": card.get("image_url"),
                "source_host": current_host,
            }
            hint = url_hint(current)
            expected_num = (
                (num(card.get("card_number", "")), int((card.get("card_number") or "").split("/")[-1]))
                if "/" in (card.get("card_number") or "") else None
            )
            if hint and expected_num and hint != expected_num:
                stats["url_number_mismatch"] += 1
                report["definite_url_number_mismatches"].append({**item, "url_number_hint": hint})
            refs = source.get(key(card.get("card_number", ""), card.get("rarity", "")), [])
            if not refs:
                stats["no_reference"] += 1
                report["no_collectory_reference"].append(item)
            elif current not in refs:
                if "/cards/kr/" in current or "pokemonkorea.co.kr" in current:
                    stats["collectory_mismatch"] += 1
                    report["definite_collectory_reference_mismatches"].append({**item, "expected_korean_images": refs})
            if not ("/cards/kr/" in current or "pokemonkorea.co.kr" in current):
                stats["non_korean"] += 1
                report["non_korean_or_untrusted_sources"].append(item)
        report["by_set"][code] = {"name": meta["name_kr"], **stats}
    for field in (
        "definite_url_number_mismatches",
        "definite_collectory_reference_mismatches",
        "non_korean_or_untrusted_sources",
        "no_collectory_reference",
    ):
        report[field].sort(key=lambda row: (row["set_name"], row.get("card_number") or "", row["card_id"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "sets_checked": report["sets_checked"],
        "cards_checked": report["cards_checked"],
        "url_number_mismatches": len(report["definite_url_number_mismatches"]),
        "collectory_reference_mismatches": len(report["definite_collectory_reference_mismatches"]),
        "non_korean_or_untrusted": len(report["non_korean_or_untrusted_sources"]),
        "no_collectory_reference": len(report["no_collectory_reference"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
