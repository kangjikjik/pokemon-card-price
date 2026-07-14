"""Apply catalog quality fixes: images, duplicate removal, name_kr."""
from __future__ import annotations

import os
import re
import sys

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from seed_from_collectory import pick_name_ko  # noqa: E402

APPLY = "--apply" in sys.argv
HANGUL = re.compile(r"[\uAC00-\uD7A3]")

# collectory CDN / pokemonkorea — 검증된 URL
IMAGE_FIXES: list[tuple[str, str, str, str]] = [
    ("S2", "110/096", "HR", "https://cdn.collectory.cc/cards/jp/S2/110_096.webp"),
    ("S2", "111/096", "HR", "https://cdn.collectory.cc/cards/jp/S2/111_096.webp"),
    ("S7D", "071/067", "SR", "https://cdn.collectory.cc/cards/jp/s7d/071_067.webp"),
    ("S7D", "072/067", "SR", "https://cdn.collectory.cc/cards/jp/s7d/072_067.webp"),
    ("S7F", "039/100", "RR", "https://cards.image.pokemonkorea.co.kr/data/wmimages/S/S8/S8_039.png?w=512"),
    ("S7F", "112/100", "SR", "https://cdn.collectory.cc/cards/jp/S8/112_100.webp"),
    ("S7F", "113/100", "SR", "https://cdn.collectory.cc/cards/jp/S8/113_100.webp"),
    ("S7F", "114/100", "SR", "https://cdn.collectory.cc/cards/jp/S8/114_100.webp"),
    ("S7F", "115/100", "SR", "https://cdn.collectory.cc/cards/jp/S8/115_100.webp"),
    ("S7F", "117/100", "HR", "https://cdn.collectory.cc/cards/jp/S8/117_100.webp"),
    ("S7F", "121/100", "HR", "https://cdn.collectory.cc/cards/jp/S8/121_100.webp"),
    ("S7F", "123/100", "HR", "https://cdn.collectory.cc/cards/jp/S8/123_100.webp"),
    ("S7F", "124/100", "HR", "https://cdn.collectory.cc/cards/jp/S8/124_100.webp"),
    ("S7F", "125/100", "UR", "https://cdn.collectory.cc/cards/jp/S8/125_100.webp"),
    ("SM9", "069/055", "UR", "https://cdn.collectory.cc/cards/jp/SM9a/069_055UR.webp"),
]

# 오삽입 중복 (동일 카드 UR/H R 버전 이미 존재)
DELETE_DUPES: list[tuple[str, str, str]] = [
    ("S11", "131/100", "SSR"),  # 125/100 UR 기라티나 VSTAR 와 중복
    ("S12", "137/098", "SSR"),  # 123/098 UR 루기아 VSTAR 와 중복
]

# name_en -> name_kr (공식 한국어명)
NAME_FIXES: dict[str, str] = {
    "Emcee's Hype": "MC의 호응유도",
    "Ethan's Adventure": "심향의 모험",
    "Team Rocket's Archer": "로켓단의 아폴로",
    "Team Rocket's Ariana": "로켓단의 아테나",
    "Team Rocket's Giovanni": "로켓단의 비주기",
    "Team Rocket's Petrel": "로켓단의 람다",
    "Team Rocket's Proton": "로켓단의 랜스",
    "Jamming Tower": "재밍타워",
    "Levincia": "누룩스시티",
}

# name_jp -> name_kr
JP_NAME_FIXES: dict[str, str] = {
    "ハヤト": "비상",
    "ロケット団のラムダ": "로켓단의 람다",
    "ロケット団のランス": "로켓단의 랜스",
}


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    sets = {r["set_code"]: r["id"] for r in sb.table("card_sets").select("id,set_code").execute().data or []}

    # 110/100 요씽리스 V → 111/100 과 동일 이미지
    s7f_id = sets["S7F"]
    ref = (
        sb.table("cards")
        .select("image_url")
        .eq("set_id", s7f_id)
        .eq("card_number", "111/100")
        .single()
        .execute()
        .data
    )
    if ref and ref.get("image_url"):
        IMAGE_FIXES.append(("S7F", "110/100", "SR", ref["image_url"]))

    client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    img_fixed = 0
    for code, num, rar, url in IMAGE_FIXES:
        sid = sets.get(code)
        if not sid:
            continue
        rows = (
            sb.table("cards")
            .select("id,image_url")
            .eq("set_id", sid)
            .eq("card_number", num)
            .eq("rarity", rar)
            .execute()
            .data
            or []
        )
        if not rows:
            print(f"  skip image {code} {num} {rar}: not found")
            continue
        r = client.get(url)
        if r.status_code != 200 or len(r.content) < 5000:
            print(f"  fail verify {code} {num} {rar}: {r.status_code}")
            continue
        print(f"  image {code} {num} {rar}")
        if APPLY:
            sb.table("cards").update({"image_url": url}).eq("id", rows[0]["id"]).execute()
        img_fixed += 1

    deleted = 0
    for code, num, rar in DELETE_DUPES:
        sid = sets.get(code)
        rows = (
            sb.table("cards")
            .select("id,name_kr")
            .eq("set_id", sid)
            .eq("card_number", num)
            .eq("rarity", rar)
            .execute()
            .data
            or []
        )
        for row in rows:
            print(f"  delete dupe {code} {num} {rar} {row.get('name_kr')}")
            if APPLY:
                sb.table("prices_kr").delete().eq("card_id", row["id"]).execute()
                sb.table("cards").delete().eq("id", row["id"]).execute()
            deleted += 1

    name_fixed = 0
    cards = sb.table("cards").select("id,name_kr,name_en,name_jp").execute().data or []
    for c in cards:
        kr = c.get("name_kr") or ""
        if HANGUL.search(kr):
            continue
        en = (c.get("name_en") or "").strip()
        if en in NAME_FIXES:
            new_kr = NAME_FIXES[en]
            print(f"  name {en} -> {new_kr}")
            if APPLY:
                sb.table("cards").update({"name_kr": new_kr}).eq("id", c["id"]).execute()
            name_fixed += 1
        elif en:
            new_kr = pick_name_ko({"name_en": en, "name_ko": kr}, kr)
            if HANGUL.search(new_kr):
                print(f"  name pick {en} -> {new_kr}")
                if APPLY:
                    sb.table("cards").update({"name_kr": new_kr}).eq("id", c["id"]).execute()
                name_fixed += 1
        jp = (c.get("name_jp") or "").strip()
        if jp in JP_NAME_FIXES and not HANGUL.search(kr):
            new_kr = JP_NAME_FIXES[jp]
            print(f"  name jp {jp} -> {new_kr}")
            if APPLY:
                sb.table("cards").update({"name_kr": new_kr}).eq("id", c["id"]).execute()
            name_fixed += 1

    print(f"\nimages={img_fixed} deleted_dupes={deleted} names={name_fixed} apply={APPLY}")


if __name__ == "__main__":
    main()
