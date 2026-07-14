"""
collectory.cc에서 확장팩 박스 이미지·카드 목록(레어도 포함) 동기화
실행: python seeds/seed_from_collectory.py
"""
import os
import re
import sys
import time

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

from lib.rarity_rank import rank_for_rarity, normalize_rarity, is_displayable_rarity
from collectory_map import COLLECTORY_API, COLLECTORY_SETS
from box_images import pick_box_image

SKIP_RARITIES = {"U", "C", "SA", "N", "CM", "UM", "PROMO", "R", "M"}
RARITY_SUFFIXES = (
    "UR-ex", "SAR", "MUR", "CSR", "CHR", "RRR", "UR", "HR", "SR", "AR", "ACE", "RR",
)
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
EX_NAME_RE = re.compile(r"(?:\bEX\b|ＥＸ|(?<![A-Za-z])ex(?![A-Za-z]))")

# collectory 레어도 보정 (세트코드, 카드번호) → 레어도
RARITY_OVERRIDES: dict[tuple[str, str], str] = {
    ("MG6", "118/081"): "MUR",
}

# collectory가 ACE로 잘못 표기한 일반 카드 — 시드에서 제외
SEED_SKIP: set[tuple[str, str]] = {
    ("SV8", "142/187"),  # 밤의 들것
    ("SV8", "146/187"),  # 카운터 캐처
    ("SV8", "148/187"),  # 테크노레이더
    ("SV8", "152/187"),  # 기술머신 데볼루션
    ("SV8", "159/187"),  # 부스트에너지 미래
    ("SV8", "184/187"),  # 축제회장
    ("SV8", "187/187"),  # 제트 에너지
}

# collectory에 빠진 시크릿 카드 수동 보완
MANUAL_SUPPLEMENTS: dict[str, list[dict]] = {
    "BW4": [
        {
            "card_number": "074/069",
            "rarity": "UR",
            "name_kr": "가디안",
            "name_en": "Gardevoir",
            "image_url": "/card-images/BW4/074-069-UR.jpg",
        },
        {
            "card_number": "075/069",
            "rarity": "UR",
            "name_kr": "아케오스",
            "name_en": "Archeops",
            "image_url": "/card-images/BW4/075-069-UR.jpg",
        },
        {
            "card_number": "076/069",
            "rarity": "UR",
            "name_kr": "포켓몬 캐처",
            "name_en": "Pokémon Catcher",
            "image_url": "/card-images/BW4/076-069-UR.jpg",
        },
    ],
}


def normalize_card_number(raw: str) -> str:
    num = (raw or "").strip()
    if not num or "/" not in num:
        return num
    left, right = num.split("/", 1)
    for suffix in RARITY_SUFFIXES:
        if right.upper().endswith(suffix):
            right = right[: -len(suffix)]
            break
    if right.endswith("M"):
        right = right[:-1]
    if right and right[-1] in "CUR" and right[:-1].isdigit():
        right = right[:-1]
    return f"{left}/{right}" if right else left


def rarity_from_card_number(raw_num: str) -> str | None:
    """카드번호 접미사 기준 레어도 — collectory 라벨보다 우선"""
    if "/" not in raw_num:
        return None
    suffix = raw_num.split("/")[-1].upper()
    for prefix in sorted(RARITY_SUFFIXES, key=len, reverse=True):
        if suffix.endswith(prefix):
            return prefix
    if suffix.endswith("RM"):
        return None
    if suffix.endswith("M"):
        return None
    if re.match(r"^\d+R$", suffix):
        return "R"
    if re.match(r"^\d+RR$", suffix):
        return "RR"
    return None


def parse_rarity(card: dict) -> str | None:
    num = card.get("card_number") or ""
    from_num = rarity_from_card_number((num or "").upper())
    if from_num in SKIP_RARITIES:
        return None
    if from_num and from_num not in SKIP_RARITIES:
        return from_num

    rarity = (card.get("rarity") or "").strip()

    if rarity in SKIP_RARITIES and "/" in num:
        suffix = num.split("/")[-1].upper()
        for prefix in RARITY_SUFFIXES:
            if suffix.endswith(prefix):
                return prefix
        if suffix.endswith("M"):
            return None
    if rarity in SKIP_RARITIES:
        return None
    if rarity == "RM":
        return None
    mapped = normalize_rarity(rarity)
    if mapped in SKIP_RARITIES:
        return None
    if mapped in ("MUR", "MA", "BWR", "FUR", "SAR", "UR", "HR", "SR", "CSR", "CHR", "AR", "ACE", "RRR", "RR", "A", "K", "PR", "SSR", "TR", "S", "H", "SL", "P"):
        return mapped
    return mapped if mapped and mapped not in SKIP_RARITIES else None


def is_ex_card(card: dict) -> bool:
    for key in ("name_ko", "name_kr", "name", "name_en", "name_ja"):
        if EX_NAME_RE.search(card.get(key) or ""):
            return True
    return False


def resolve_rarity(card: dict, set_has_native_rr: bool) -> str | None:
    """표시 등급. RR 심볼 없던 팩의 포켓몬 EX(R)는 RR로 승격."""
    rarity = parse_rarity(card)
    if rarity:
        return rarity
    raw = (card.get("rarity") or "").strip().upper()
    if not set_has_native_rr and raw == "R" and is_ex_card(card):
        return "RR"
    return None


def pick_name_ko(card: dict, existing_kr: str | None) -> str:
    for key in ("name_ko", "name_kr"):
        val = (card.get(key) or "").strip()
        if val and HANGUL_RE.search(val):
            return val
    if existing_kr and HANGUL_RE.search(existing_kr):
        return existing_kr
    return (card.get("name_en") or card.get("name") or existing_kr or "").strip()


def fetch_set_cards(client: httpx.Client, set_id: str) -> list[dict]:
    url = f"{COLLECTORY_API}/sets/{set_id}/cards"
    resp = client.get(url, timeout=90)
    resp.raise_for_status()
    return resp.json().get("cards") or []


def fetch_set_meta(client: httpx.Client, set_id: str) -> dict | None:
    resp = client.get(f"{COLLECTORY_API}/sets", timeout=60)
    resp.raise_for_status()
    for s in resp.json().get("sets") or []:
        if s.get("id") == set_id:
            return s
    return None


# MG6는 seed_abyss_eye.py 전용 — collectory 배치에서 제외
SKIP_SETS = {"MG6"}

def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(headers={"User-Agent": "pokemon-card-price-seed/1.0"})

    total_inserted = 0
    total_updated = 0

    for set_code, cfg in COLLECTORY_SETS.items():
        if set_code in SKIP_SETS:
            print(f"\n[{set_code}] SKIP (전용 시드)")
            continue
        collectory_id = cfg["id"]
        print(f"\n[{set_code}] collectory={collectory_id}")

        set_row = sb.table("card_sets").select("id").eq("set_code", set_code).single().execute().data
        if not set_row:
            print(f"  SKIP: DB에 세트 없음")
            continue
        set_id = set_row["id"]

        meta = fetch_set_meta(client, collectory_id)
        set_patch: dict = {}
        if meta:
            # 한국 BS 코드 + release_date_ko 있을 때만 collectory 날짜 반영
            if meta.get("set_code_ko") and meta.get("release_date_ko"):
                set_patch["released_at"] = meta["release_date_ko"]
            if meta.get("name_ko") and HANGUL_RE.search(meta["name_ko"] or ""):
                set_patch["name_kr"] = meta["name_ko"]

        raw_cards = fetch_set_cards(client, collectory_id)
        print(f"  fetched {len(raw_cards)} cards")
        set_has_native_rr = any((c.get("rarity") or "").strip().upper() == "RR" for c in raw_cards)

        box_url = pick_box_image(set_code, meta.get("image_url") if meta else None, raw_cards)
        if box_url:
            set_patch["image_url"] = box_url
            print(f"  box image -> {box_url[:72]}...")
        if set_patch:
            sb.table("card_sets").update(set_patch).eq("id", set_id).execute()

        existing_rows = (
            sb.table("cards")
            .select("id,card_number,rarity,name_kr,name_jp")
            .eq("set_id", set_id)
            .execute()
            .data
            or []
        )
        by_number: dict[str, list] = {}
        for row in existing_rows:
            by_number.setdefault(row.get("card_number") or "", []).append(row)

        seen_keys: set[tuple[str, str]] = set()
        inserted = updated = skipped = 0

        cards_to_seed = list(raw_cards)
        for manual in MANUAL_SUPPLEMENTS.get(set_code, []):
            cards_to_seed.append({
                "card_number": manual["card_number"],
                "rarity": manual["rarity"],
                "name_ko": manual.get("name_kr", ""),
                "name_en": manual.get("name_en", ""),
                "cdn_image_url": manual.get("image_url", ""),
                "image_url": manual.get("image_url", ""),
            })

        for card in cards_to_seed:
            rarity = resolve_rarity(card, set_has_native_rr)
            if not rarity:
                skipped += 1
                continue

            card_number = normalize_card_number(card.get("card_number") or "")
            if (set_code, card_number) in SEED_SKIP:
                skipped += 1
                continue
            if (set_code, card_number) in RARITY_OVERRIDES:
                rarity = RARITY_OVERRIDES[(set_code, card_number)]
            if not is_displayable_rarity(rarity):
                skipped += 1
                continue
            if card_number.endswith("M") or "CM" in (card.get("card_number") or ""):
                skipped += 1
                continue

            dedupe_key = (card_number, rarity)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            image_url = (card.get("cdn_image_url") or card.get("image_url") or "").strip()
            name_en = (card.get("name_en") or card.get("name") or "").strip()
            name_jp = (card.get("name_ja") or "").strip()

            match = None
            for row in by_number.get(card_number, []):
                if row.get("rarity") == rarity:
                    match = row
                    break
            if not match and by_number.get(card_number):
                # 같은 번호에 RR/SR 등 다른 등급이 있으면 새로 넣음
                if any(r.get("rarity") == rarity for r in by_number[card_number]):
                    match = next(r for r in by_number[card_number] if r.get("rarity") == rarity)
                else:
                    match = None
            if not match and name_jp:
                for row in existing_rows:
                    if row.get("name_jp") == name_jp and row.get("rarity") == rarity:
                        match = row
                        break

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

        print(f"  inserted={inserted} updated={updated} skipped={skipped} kept={inserted+updated}")
        total_inserted += inserted
        total_updated += updated
        time.sleep(0.3)

    print(f"\n[완료] insert={total_inserted} update={total_updated}")


if __name__ == "__main__":
    main()
