"""MG6 한국 공식(name_ko·image) — 포켓몬코리아 Collectory KR 세트 기준.

DB 카드번호는 일본(102=아이언디펜더)이지만, 한국 팩 번호·이미지·표기는 다름.
→ name_jp(일본어명)로 KR 공식 카드와 매칭.
"""
from __future__ import annotations

import re
from functools import lru_cache

import httpx

JP_SET_ID = "611cf371-dafe-42fc-b86d-895aa433e10d"
KR_SET_ID = "111a2e55-8991-414b-a5da-009b3553e6cd"

# JP Collectory 영문명 → KR 공식 name_ko (포켓몬코리아 KR 세트)
EN_TO_KR_NAME: dict[str, str] = {
    "Iron Defender": "아이언 디펜드업",
    "Energy Switch": "에너지 갈아 달기",
    "Crushing Hammer": "크래시 해머",
    "Dark Bell": "다크벨",
    "Heroic Bomb": "호쾌봄",
    "Brave Bangle": "브레이브뱅글",
    "Misty's Energy": "이슬의 기력",
    "Gladion's Fighting Spirit": "글라디오의 결전",
    "Rust Syndicate Grunts": "녹청파의 조무래기",
    "Gwynn": "무쿠",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


@lru_cache(maxsize=1)
def _fetch_set_cards(set_id: str) -> list[dict]:
    r = httpx.get(
        f"https://collectory.cc/api/sets/{set_id}/cards",
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    r.raise_for_status()
    return r.json().get("cards", [])


@lru_cache(maxsize=1)
def _kr_by_name_ko() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for c in _fetch_set_cards(KR_SET_ID):
        ko = (c.get("name_ko") or "").strip()
        if ko:
            out[_norm(ko)] = c
    return out


@lru_cache(maxsize=1)
def _jp_by_name_jp() -> dict[str, dict]:
    """JP 세트: card_number → card (영문 name 포함)."""
    out: dict[str, dict] = {}
    for c in _fetch_set_cards(JP_SET_ID):
        num = (c.get("card_number") or "").strip()
        if num:
            out[num] = c
    return out


def _kr_image_url(card: dict) -> str | None:
    url = (card.get("image_url") or card.get("cdn_image_url") or "").strip()
    if not url:
        return None
    # 한국 공식 CDN만 (일판 jp/M5·중판 TW 제외)
    if "pokemonkorea.co.kr" not in url and "cards.image.pokemonkorea" not in url:
        return None
    return url.split("?")[0]


def official_for_name_jp(name_jp: str, rarity: str = "") -> tuple[str | None, str | None]:
    """name_jp → (KR 공식 name_ko, KR 공식 image_url)."""
    jp_cards = _fetch_set_cards(JP_SET_ID)
    en_name = ""
    for c in jp_cards:
        if (c.get("name_ja") or c.get("name_jp") or "") == name_jp:
            en_name = c.get("name") or ""
            break
    if not en_name:
        # DB name_jp 직접 매칭 (Collectory name_ja 필드 없을 때)
        from lib.trainer_item_cards import MG6_NAME_JP_TO_EN

        en_name = MG6_NAME_JP_TO_EN.get(name_jp, "")

    kr_name = EN_TO_KR_NAME.get(en_name, "")
    if not kr_name:
        return None, None

    r = (rarity or "").upper()
    kr_index = _kr_by_name_ko()
    hit = kr_index.get(_norm(kr_name))
    if not hit and r == "SAR":
        # SAR 풀아트 — 동명 SR과 구분 (무쿠·글라디오)
        for c in _fetch_set_cards(KR_SET_ID):
            if _norm(c.get("name_ko") or "") == _norm(kr_name) and (c.get("rarity") or "").upper() == "SAR":
                hit = c
                break
    if not hit:
        hit = kr_index.get(_norm(kr_name))

    if not hit:
        return kr_name, None

    img = _kr_image_url(hit)
    if not img:
        num_s = (hit.get("card_number") or "").split("/")[0]
        if num_s.isdigit():
            candidate = pokemonkorea_m5_image(int(num_s))
            try:
                r = httpx.head(candidate, timeout=10, follow_redirects=True)
                if r.status_code == 200:
                    img = candidate
            except Exception:
                pass
    ko = (hit.get("name_ko") or kr_name).strip()
    return ko, img


def pokemonkorea_m5_image(kr_pack_num: int) -> str:
    return f"https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M5/M5_{kr_pack_num}.png"


# DB card_number(일본 팩 번호) → name_jp (트레이너·아이템·SAR)
_JP_NUM_TO_NAME_JP: dict[int, str] = {
    102: "アイアンディフェンダー",
    103: "エネルギーつけかえ",
    104: "クラッシュハンマー",
    105: "ダークベル",
    106: "ごうかいボム",
    107: "ブレイブバングル",
    108: "カスミの元気",
    109: "グラジオの決戦",
    110: "サビ組のしたっぱ",
    111: "ムク",
    116: "グラジオの決戦",
    117: "ムク",
}


def official_name_ko(jp_card_num: int, rarity: str = "SR") -> str | None:
    name_jp = _JP_NUM_TO_NAME_JP.get(jp_card_num)
    if not name_jp:
        return None
    ko, _ = official_for_name_jp(name_jp, rarity)
    return ko


def official_image_url(jp_card_num: int, rarity: str = "SR") -> str | None:
    name_jp = _JP_NUM_TO_NAME_JP.get(jp_card_num)
    if not name_jp:
        return None
    _, img = official_for_name_jp(name_jp, rarity)
    return img
