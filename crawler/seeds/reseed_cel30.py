"""Collectory KR 데이터로 CEL30(30th CELEBRATION) 시드."""

from __future__ import annotations

import os
import sys

import httpx
from collections import defaultdict
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.rarity_rank import is_displayable_rarity, rank_for_rarity  # noqa: E402
from seed_from_collectory import (  # noqa: E402
    normalize_card_number,
    parse_rarity,
    pick_name_ko,
)
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()
APPLY = "--apply" in sys.argv

SET_CODE = "CEL30"
COLLECTORY_ID = "bfc5bc98-87f1-46b2-b68d-e82152e744d4"
SET_NAME_KR = "30th CELEBRATION"
RELEASED_AT = "2026-09-16"
PACK_IMAGE = "https://cdn.collectory.cc/cards/us/30th/set-logo2.webp"

RARITY_FROM_COLLECTORY = {
    "Futuristic Rare": "FUR",
    "Pikachu Rare": "K",
}

# collectory KR 행에 레어도가 없는 30주년 역사 카드 reprint
RARITY_OVERRIDES: dict[str, str] = {
    "137/103": "SL",
    "142/103": "SL",
    "160/103": "SL",
    "163/103": "SL",
    "165/103": "SL",
}


def resolve_rarity(card: dict, siblings: list[dict]) -> str:
    raw = (card.get("rarity") or "").strip()
    if not raw:
        raw = next((s.get("rarity") or "" for s in siblings if s.get("rarity")), "").strip()
    raw = RARITY_FROM_COLLECTORY.get(raw, raw)
    if raw:
        return raw
    num = normalize_card_number(card.get("card_number") or "")
    if num in RARITY_OVERRIDES:
        return RARITY_OVERRIDES[num]
    parsed = parse_rarity(card)
    return parsed or ""


def fetch_cards() -> list[dict]:
    with httpx.Client(timeout=90, headers={"User-Agent": "pokemon-card-price-cel30/1.0"}) as client:
        resp = client.get(f"https://collectory.cc/api/sets/{COLLECTORY_ID}/cards")
        resp.raise_for_status()
        return resp.json().get("cards") or []


def main() -> None:
    cards = fetch_cards()
    by_number: dict[str, list[dict]] = defaultdict(list)
    for card in cards:
        by_number[normalize_card_number(card.get("card_number") or "")].append(card)

    candidates: list[tuple[str, dict, str]] = []
    for number, rows in sorted(by_number.items()):
        if not number:
            continue
        kr = next((r for r in rows if "/kr/" in (r.get("cdn_image_url") or r.get("image_url") or "")), None)
        if not kr:
            continue
        rarity = resolve_rarity(kr, rows)
        if not is_displayable_rarity(rarity):
            continue
        candidates.append((number, kr, rarity))

    print(f"mode={'APPLY' if APPLY else 'DRY-RUN'}")
    print(f"KR displayable cards={len(candidates)}")

    set_patch = {
        "set_code": SET_CODE,
        "name_kr": SET_NAME_KR,
        "name_en": "30th Celebration",
        "released_at": RELEASED_AT,
        "image_url": PACK_IMAGE,
    }

    existing_set = sb.table("card_sets").select("id").eq("set_code", SET_CODE).execute().data or []
    if existing_set:
        set_id = existing_set[0]["id"]
        if APPLY:
            sb.table("card_sets").update(set_patch).eq("id", set_id).execute()
    elif APPLY:
        set_id = sb.table("card_sets").insert(set_patch).execute().data[0]["id"]
    else:
        set_id = -1

    inserted = updated = 0
    for number, card, rarity in candidates:
        image_url = (card.get("cdn_image_url") or card.get("image_url") or "").strip()
        payload = {
            "set_id": set_id,
            "card_number": number,
            "name_kr": pick_name_ko(card, None),
            "name_jp": (card.get("name_ja") or "").strip(),
            "name_en": (card.get("name_en") or card.get("name") or "").strip(),
            "rarity": rarity,
            "rarity_rank": rank_for_rarity(rarity),
            "image_url": image_url,
        }
        if not APPLY:
            print(f"  [dry] {number} {payload['name_kr']} {rarity}")
            continue

        existing = (
            sb.table("cards")
            .select("id")
            .eq("set_id", set_id)
            .eq("card_number", number)
            .execute()
            .data
            or []
        )
        if existing:
            sb.table("cards").update(payload).eq("id", existing[0]["id"]).execute()
            updated += 1
        else:
            sb.table("cards").insert(payload).execute()
            inserted += 1

    print(f"set_id={set_id} insert={inserted} update={updated}")


if __name__ == "__main__":
    main()
