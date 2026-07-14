"""신규 featured 10세트 — collectory 시드 + 메타 갱신"""
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from kr_sets import KR_BY_CODE
from lib.rarity_rank import rank_for_rarity
from collectory_map import COLLECTORY_API
from box_images import pick_box_image
from seed_from_collectory import (
    parse_rarity,
    normalize_card_number,
    pick_name_ko,
    RARITY_OVERRIDES,
    HANGUL_RE,
)

NEW_CODES = [
    "SV5M", "SV4x", "SV4", "SV4a", "SV4K",
    "SV4M", "SV3a", "SV3", "SV2a", "SV2D",
]


def fetch_set_cards(client: httpx.Client, set_id: str) -> list[dict]:
    resp = client.get(f"{COLLECTORY_API}/sets/{set_id}/cards", timeout=90)
    resp.raise_for_status()
    return resp.json().get("cards") or []


def fetch_set_meta(client: httpx.Client, set_id: str) -> dict | None:
    resp = client.get(f"{COLLECTORY_API}/sets", timeout=60)
    resp.raise_for_status()
    for s in resp.json().get("sets") or []:
        if s.get("id") == set_id:
            return s
    return None


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(headers={"User-Agent": "pokemon-card-price-seed/1.0"})

    for code in NEW_CODES:
        meta = KR_BY_CODE.get(code)
        if not meta or not meta.collectory_id:
            print(f"[{code}] SKIP — kr_sets 없음")
            continue

        print(f"\n[{code}] {meta.name_kr}")

        row = (
            sb.table("card_sets")
            .upsert(
                {
                    "set_code": code,
                    "name_kr": meta.name_kr,
                    "name_jp": meta.name_kr,
                    "name_en": meta.name_kr,
                    "released_at": meta.released_at,
                    "image_url": meta.box_image_kr,
                },
                on_conflict="set_code",
            )
            .execute()
            .data[0]
        )
        set_id = row["id"]

        col_meta = fetch_set_meta(client, meta.collectory_id)
        raw_cards = fetch_set_cards(client, meta.collectory_id)
        print(f"  collectory cards: {len(raw_cards)}")

        box_url = pick_box_image(code, col_meta.get("image_url") if col_meta else None, raw_cards)
        if box_url:
            sb.table("card_sets").update({"image_url": box_url}).eq("id", set_id).execute()

        existing = (
            sb.table("cards")
            .select("id,card_number,rarity,name_kr,name_jp")
            .eq("set_id", set_id)
            .execute()
            .data
            or []
        )
        by_number: dict[str, list] = {}
        for r in existing:
            by_number.setdefault(r.get("card_number") or "", []).append(r)

        seen: set[tuple[str, str]] = set()
        inserted = updated = skipped = 0

        for card in raw_cards:
            rarity = parse_rarity(card)
            if not rarity:
                skipped += 1
                continue
            card_number = normalize_card_number(card.get("card_number") or "")
            if (code, card_number) in RARITY_OVERRIDES:
                rarity = RARITY_OVERRIDES[(code, card_number)]
            if card_number.endswith("M") or "CM" in (card.get("card_number") or ""):
                skipped += 1
                continue
            key = (card_number, rarity)
            if key in seen:
                continue
            seen.add(key)

            image_url = (card.get("cdn_image_url") or card.get("image_url") or "").strip()
            name_en = (card.get("name_en") or card.get("name") or "").strip()
            name_jp = (card.get("name_ja") or "").strip()

            match = None
            for r in by_number.get(card_number, []):
                if r.get("rarity") == rarity:
                    match = r
                    break
            if not match and by_number.get(card_number):
                match = by_number[card_number][0]

            payload = {
                "set_id": set_id,
                "card_number": card_number,
                "rarity": rarity,
                "rarity_rank": rank_for_rarity(rarity),
                "name_kr": pick_name_ko(card, match["name_kr"] if match else None),
                "name_jp": name_jp or (match["name_jp"] if match else "") or name_en,
                "name_en": name_en,
                "image_url": image_url,
            }
            if match:
                sb.table("cards").update(payload).eq("id", match["id"]).execute()
                updated += 1
            else:
                sb.table("cards").insert(payload).execute()
                inserted += 1

        cnt = sb.table("cards").select("id", count="exact").eq("set_id", set_id).execute().count
        print(f"  inserted={inserted} updated={updated} skipped={skipped} db={cnt}")
        time.sleep(0.3)

    print("\n[완료]")


if __name__ == "__main__":
    main()
