"""
프로모 카드 시드 — collectory KR 프로모 소스 + featured 팩 내 PROMO.

  python seed_promo_cards.py           # 드라이런
  python seed_promo_cards.py --apply
"""
from __future__ import annotations

import os
import re
import sys
import time

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.rarity_rank import rank_for_rarity  # noqa: E402
from kr_sets import KR_SETS, KR_BY_CODE  # noqa: E402
from promo_catalog import (  # noqa: E402
    COLLECTORY_API,
    PROMO_MISC,
    PROMO_RARITY_RAW,
    PROMO_SOURCES,
)
from reseed_cel25pk_official import OFFICIAL_CARDS, main as reseed_official_25pk  # noqa: E402
from seed_from_collectory import normalize_card_number, pick_name_ko  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()
APPLY = "--apply" in sys.argv
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def is_promo_raw(card: dict) -> bool:
    return (card.get("rarity") or "").strip().upper() in PROMO_RARITY_RAW


def fetch_cards(client: httpx.Client, collectory_id: str) -> list[dict]:
    resp = client.get(f"{COLLECTORY_API}/sets/{collectory_id}/cards", timeout=90)
    resp.raise_for_status()
    return resp.json().get("cards") or []


def fetch_meta(client: httpx.Client, collectory_id: str) -> dict | None:
    resp = client.get(f"{COLLECTORY_API}/sets", timeout=60)
    resp.raise_for_status()
    for s in resp.json().get("sets") or []:
        if s.get("id") == collectory_id:
            return s
    return None


def ensure_promo_set(source) -> int | None:
    row = sb.table("card_sets").select("id").eq("set_code", source.code).execute().data
    patch = {
        "set_code": source.code,
        "name_kr": source.name_kr,
        "name_en": source.name_kr,
        "released_at": source.released_at or None,
    }
    if getattr(source, "image_url", ""):
        patch["image_url"] = source.image_url
    meta = None
    if source.collectory_id:
        try:
            meta = fetch_meta(httpx.Client(timeout=30), source.collectory_id)
        except Exception:
            meta = None
    if meta:
        if meta.get("name_ko") and HANGUL_RE.search(meta["name_ko"] or ""):
            patch["name_kr"] = meta["name_ko"]
        if meta.get("image_url"):
            patch["image_url"] = meta["image_url"]
        if meta.get("release_date_ko") and not source.released_at:
            patch["released_at"] = meta["release_date_ko"]

    if row:
        set_id = row[0]["id"]
        if APPLY:
            sb.table("card_sets").update(patch).eq("id", set_id).execute()
        return set_id

    if not APPLY:
        print(f"  [dry] would create set {source.code}")
        return -1

    ins = sb.table("card_sets").insert(patch).execute().data
    return ins[0]["id"] if ins else None


def upsert_card(set_id: int, card: dict, *, dry_id: int = -1) -> str:
    if set_id < 0:
        return "skip"

    card_number = normalize_card_number(card.get("card_number") or "")
    if not card_number:
        return "skip"

    image_url = (card.get("cdn_image_url") or card.get("image_url") or "").strip()
    name_en = (card.get("name_en") or card.get("name") or "").strip()
    name_jp = (card.get("name_ja") or "").strip()
    rarity = "P"

    existing = (
        sb.table("cards")
        .select("id,name_kr,name_jp")
        .eq("set_id", set_id)
        .eq("card_number", card_number)
        .eq("rarity", rarity)
        .execute()
        .data
        or []
    )
    match = existing[0] if existing else None

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

    if not APPLY:
        return "dry"

    if match:
        sb.table("cards").update(payload).eq("id", match["id"]).execute()
        return "update"
    sb.table("cards").insert(payload).execute()
    return "insert"


def seed_source(client: httpx.Client, source) -> tuple[int, int, int]:
    print(f"\n[{source.code}] {source.name_kr}")
    set_id = ensure_promo_set(source)
    raw = fetch_cards(client, source.collectory_id)
    candidates = [c for c in raw if is_promo_raw(c)] or raw
    print(f"  collectory={len(raw)} promo={len(candidates)}")

    ins = upd = skip = 0
    seen: set[str] = set()
    for card in candidates:
        num = normalize_card_number(card.get("card_number") or "")
        if not num or num in seen:
            skip += 1
            continue
        seen.add(num)
        action = upsert_card(set_id, card)
        if action == "insert":
            ins += 1
        elif action == "update":
            upd += 1
        else:
            skip += 1

    print(f"  insert={ins} update={upd} skip={skip}")
    return ins, upd, skip


def seed_embedded_in_featured(client: httpx.Client) -> tuple[int, int]:
    """featured 확장팩 안 PROMO 카드 → 해당 팩 set_id에 P 등급으로."""
    print("\n[embedded] featured 팩 내 PROMO")
    ins = upd = 0
    for meta in KR_SETS:
        if not meta.collectory_id:
            continue
        set_row = sb.table("card_sets").select("id").eq("set_code", meta.code).execute().data
        if not set_row:
            continue
        set_id = set_row[0]["id"]
        try:
            raw = fetch_cards(client, meta.collectory_id)
        except Exception as e:
            print(f"  skip {meta.code}: {e}")
            continue
        promos = [c for c in raw if is_promo_raw(c)]
        if not promos:
            continue
        for card in promos:
            action = upsert_card(set_id, card)
            if action == "insert":
                ins += 1
            elif action == "update":
                upd += 1
        print(f"  {meta.code}: {len(promos)} promo cards")
    return ins, upd


def main() -> None:
    print(f"mode={'APPLY' if APPLY else 'DRY-RUN'}")
    client = httpx.Client(headers={"User-Agent": "pokemon-card-price-promo-seed/1.0"})
    total_i = total_u = 0

    for source in PROMO_SOURCES:
        if source.code == PROMO_MISC.code:
            continue
        if source.code == "CEL25PK":
            print(f"\n[{source.code}] {source.name_kr} (official checklist)")
            if APPLY:
                reseed_official_25pk()
            else:
                print(f"  [dry] would upsert official cards={len(OFFICIAL_CARDS)}")
            total_u += len(OFFICIAL_CARDS)
            continue
        i, u, _ = seed_source(client, source)
        total_i += i
        total_u += u
        time.sleep(0.2)

    ensure_promo_set(PROMO_MISC)
    print(f"\n[{PROMO_MISC.code}] {PROMO_MISC.name_kr} (empty shell)")

    ei, eu = seed_embedded_in_featured(client)
    total_i += ei
    total_u += eu

    print(f"\n[완료] insert={total_i} update={total_u}")


if __name__ == "__main__":
    main()
