"""Collectory 데이터로 CEL30(30th CELEBRATION) 시드 — Classic Collection(CC) 136~165 포함."""

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
SET_NAME_KR = "30주년 기념"
RELEASED_AT = "2026-09-16"
PACK_IMAGE = "/set-boxes/CEL30.png"

RARITY_FROM_COLLECTORY = {
    "Futuristic Rare": "FUR",
    "Pikachu Rare": "PKR",
}

# KR 017/103~046/103 — 30종 일러스트 피카츄 (PKR)
PIKACHU_PKR_FIRST = 17
PIKACHU_PKR_LAST = 46

CLASSIC_COLLECTION_FIRST = 136
CLASSIC_COLLECTION_LAST = 165

# Classic Collection 136/103~165/103 — 공식 한글명 (Collectory KR 없을 때)
CLASSIC_NAME_KR: dict[str, str] = {
    "136/103": "피카츄",
    "137/103": "리자몽",
    "138/103": "이슬",
    "139/103": "푸린",
    "140/103": "포푸니",
    "141/103": "빛나는 세레비",
    "142/103": "루기아",
    "143/103": "델케티",
    "144/103": "나쁜 마기라스",
    "145/103": "핫삼 ex",
    "146/103": "메타그로스",
    "147/103": "펄기아 LV.X",
    "148/103": "유크시",
    "149/103": "크로뱃",
    "150/103": "팬텀",
    "151/103": "다크라이&크레세리아 LEGEND",
    "152/103": "다크라이&크레세리아 LEGEND",
    "153/103": "N",
    "154/103": "레쿠쟈 EX",
    "155/103": "게노세크트 EX",
    "156/103": "M 가디안 EX",
    "157/103": "개굴닌자 BREAK",
    "158/103": "솔가레오",
    "159/103": "매시붕 GX",
    "160/103": "피카츄&제크로무 GX",
    "161/103": "자시안 V",
    "162/103": "라이코",
    "163/103": "뮤 VMAX",
    "164/103": "아르세우스 VSTAR",
    "165/103": "잉어킹",
}


def pikachu_pkr_index(card_number: str) -> int | None:
    num = normalize_card_number(card_number)
    try:
        n = int(num.split("/")[0])
    except ValueError:
        return None
    if num.endswith("/103") and PIKACHU_PKR_FIRST <= n <= PIKACHU_PKR_LAST:
        return n - PIKACHU_PKR_FIRST + 1
    return None


def pikachu_pkr_name_kr(card_number: str) -> str | None:
    idx = pikachu_pkr_index(card_number)
    return f"{idx}번 피카츄" if idx else None


def is_classic_collection(card_number: str) -> bool:
    num = normalize_card_number(card_number)
    if "/" not in num:
        return False
    try:
        n = int(num.split("/")[0])
    except ValueError:
        return False
    return num.endswith("/103") and CLASSIC_COLLECTION_FIRST <= n <= CLASSIC_COLLECTION_LAST


def pick_kr_row(rows: list[dict]) -> dict | None:
    return next(
        (r for r in rows if "/kr/" in (r.get("cdn_image_url") or r.get("image_url") or "")),
        None,
    )


def pick_jp_row(rows: list[dict]) -> dict | None:
    return next(
        (r for r in rows if "/jp/" in (r.get("cdn_image_url") or r.get("image_url") or "")),
        None,
    )


def pick_card_row(number: str, rows: list[dict]) -> dict | None:
    kr = pick_kr_row(rows)
    if is_classic_collection(number):
        return kr or pick_jp_row(rows) or (rows[0] if rows else None)
    return kr


def resolve_rarity(card: dict, siblings: list[dict], number: str) -> str:
    if is_classic_collection(number):
        return "CC"
    num = normalize_card_number(number)
    if pikachu_pkr_index(num):
        return "PKR"
    raw = (card.get("rarity") or "").strip()
    if not raw:
        raw = next((s.get("rarity") or "" for s in siblings if s.get("rarity")), "").strip()
    raw = RARITY_FROM_COLLECTORY.get(raw, raw)
    if raw:
        return raw
    parsed = parse_rarity(card)
    return parsed or ""


def resolve_name_kr(number: str, card: dict) -> str:
    pkr = pikachu_pkr_name_kr(number)
    if pkr:
        return pkr
    num = normalize_card_number(number)
    if num in CLASSIC_NAME_KR:
        return CLASSIC_NAME_KR[num]
    from_collectory = pick_name_ko(card, None)
    if from_collectory and any("\uac00" <= c <= "\ud7a3" for c in from_collectory):
        return from_collectory
    return from_collectory or num


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
    classic_seen = 0
    for number, rows in sorted(by_number.items()):
        if not number:
            continue
        card = pick_card_row(number, rows)
        if not card:
            continue
        rarity = resolve_rarity(card, rows, number)
        if not is_displayable_rarity(rarity):
            continue
        if is_classic_collection(number):
            classic_seen += 1
        candidates.append((number, card, rarity))

    print(f"mode={'APPLY' if APPLY else 'DRY-RUN'}")
    print(f"displayable cards={len(candidates)} (CC classic={classic_seen})")

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
        name_kr = resolve_name_kr(number, card)
        payload = {
            "set_id": set_id,
            "card_number": number,
            "name_kr": name_kr,
            "name_jp": (card.get("name_ja") or "").strip(),
            "name_en": (card.get("name_en") or card.get("name") or "").strip(),
            "rarity": rarity,
            "rarity_rank": rank_for_rarity(rarity),
            "image_url": image_url,
        }
        if not APPLY:
            img_lang = "KR" if "/kr/" in image_url else "JP" if "/jp/" in image_url else "?"
            print(f"  [dry] {number} {name_kr} {rarity} img={img_lang}")
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
