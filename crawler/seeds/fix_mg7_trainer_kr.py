"""스톰에메랄da(MG7) 트레이너·아이템 — 등급별 Collectory KR name_ko + 한국판 이미지."""
from __future__ import annotations

import os
import re
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from lib.collectory_kr_sync import (
    _indexes,
    _norm,
    _pick_hit,
    official_kr_by_ko_name,
    official_kr_for_card,
)
from lib.trainer_item_cards import is_trainer_or_item_card
from utils.db import get_supabase

SET_CODE = "MG7"
APPLY = "--apply" in sys.argv

# DB name_jp → Collectory KR name_ko
JP_TO_KO: dict[str, str] = {
    "おいしいおむすび": "맛있는 주먹밥",
    "とくちゅうチョッキ": "특별주문조끼",
    "メガレックウザキャップ": "메가레쿠쟈캡",
    "MCの盛り上げ": "MC의 호응유도",
    "フウとランの修行": "풍&란의 수행",
    "ヒガナの信頼": "피아나의 신뢰",
    "ぼうけんのランタン": "모험 랜턴",
    "ポケモンキャッチャー": "포켓몬 캐처",
    "ギリー": "성한",
    "グロウ草エネルギー": "그로우 풀에너지",
    "ニトロ炎エネルギー": "니트로 불꽃에너지",
    "バブル水エネルギー": "버블 물에너지",
}

# 경기장 L/R — Collectory KR 단일 U + 공식 이미지 번호
STADIUM_KO_IMG: dict[str, tuple[str, str]] = {
    "伝説の海溝": ("전설의 해구", "https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M6/M6_075.png"),
    "伝説の山頂": ("전설의 산정", "https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M6/M6_071.png"),
    "伝説の溶岩洞": ("전설의 용암동굴", "https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M6/M6_073.png"),
}


def _is_pokemonkorea(url: str) -> bool:
    return "pokemonkorea" in (url or "")


def _wrong_u_kr_on_high_rarity(rarity: str, image_url: str) -> bool:
    """SR/SAR에 U/C 한국판 이미지(M6_063~076)가 붙은 경우."""
    r = (rarity or "").upper()
    if r not in ("SR", "SAR", "HR", "UR"):
        return False
    if not _is_pokemonkorea(image_url):
        return False
    m = re.search(r"M6_(\d{3})\.png", image_url or "")
    if not m:
        return False
    n = int(m.group(1))
    return 63 <= n <= 76


def _sr_jp_fallback(name_jp: str, rarity: str) -> str | None:
    """한국 SR 이미지 없을 때 — 등급 맞는 Collectory JP webp (U 한국판 오적용 방지)."""
    hits = _indexes(SET_CODE)["by_ja"].get(_norm(name_jp), [])
    hit = _pick_hit(hits, rarity)
    if not hit:
        ko = JP_TO_KO.get(name_jp, "")
        if ko:
            hit = _pick_hit(_indexes(SET_CODE)["by_ko"].get(_norm(ko), []), rarity)
    if not hit:
        return None
    url = (hit.get("cdn_image_url") or hit.get("image_url") or "").strip()
    return url.split("?")[0] if url else None


def resolve_mg7(name_jp: str, rarity: str, card_number: str) -> tuple[str | None, str | None]:
    if name_jp in STADIUM_KO_IMG and (rarity or "").upper() == "U":
        return STADIUM_KO_IMG[name_jp]

    ko_hint = JP_TO_KO.get(name_jp, "")
    ko, img = official_kr_for_card(SET_CODE, name_jp, card_number, rarity, name_ko_hint=ko_hint)
    if not ko and ko_hint:
        ko, img = official_kr_by_ko_name(SET_CODE, ko_hint, rarity)
    if ko:
        if not img:
            return ko, _sr_jp_fallback(name_jp, rarity)
        return ko, img
    return None, None


def _is_target(c: dict) -> bool:
    name_jp = (c.get("name_jp") or "").strip()
    if name_jp in JP_TO_KO or name_jp in STADIUM_KO_IMG:
        return True
    return is_trainer_or_item_card(SET_CODE, c.get("card_number") or "", name_jp)


def main() -> None:
    sb = get_supabase()
    set_row = sb.table("card_sets").select("id").eq("set_code", SET_CODE).single().execute().data
    _indexes(SET_CODE)  # warm cache

    db_cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,name_jp,rarity,image_url")
        .eq("set_id", set_row["id"])
        .execute()
        .data
        or []
    )

    n = 0
    for c in db_cards:
        name_jp = (c.get("name_jp") or "").strip()
        if not _is_target(c):
            continue

        rarity = (c.get("rarity") or "").strip()
        old_name = (c.get("name_kr") or "").strip()
        old_img = (c.get("image_url") or "").split("?")[0]

        new_name, new_img = resolve_mg7(name_jp, rarity, c.get("card_number") or "")

        # SR/SAR에 U 한국판 이미지 오적용 제거 → 등급 맞는 JP SR art
        if _wrong_u_kr_on_high_rarity(rarity, old_img):
            jp_fb = _sr_jp_fallback(name_jp, rarity)
            if jp_fb:
                new_img = jp_fb

        if not new_name:
            print(f"  SKIP {c.get('card_number')} {name_jp} {rarity} — 매칭 없음")
            continue

        payload: dict = {}
        if old_name != new_name:
            payload["name_kr"] = new_name
        if new_img and old_img != new_img.split("?")[0]:
            payload["image_url"] = new_img.split("?")[0]

        # 등급 맞는 KR/ JP(SR) 이미지로 교체 필요한데 new_img 없고 SR 오적용만 있는 경우
        if not payload and _wrong_u_kr_on_high_rarity(rarity, old_img):
            jp_fb = _sr_jp_fallback(name_jp, rarity)
            if jp_fb and old_img != jp_fb:
                payload = {"image_url": jp_fb}

        if not payload:
            continue

        print(f"  [{c['card_number']}] {rarity} {name_jp}")
        if "name_kr" in payload:
            print(f"    name: {old_name!r} → {payload['name_kr']!r}")
        if "image_url" in payload:
            tag = "KR" if _is_pokemonkorea(payload["image_url"]) else "JP(등급맞음)"
            print(f"    img → {tag} …{payload['image_url'][-36:]}")

        if APPLY:
            sb.table("cards").update(payload).eq("id", c["id"]).execute()
        n += 1

    print(f"\n{'적용' if APPLY else '드라이런'}: {n}장")


if __name__ == "__main__":
    main()
