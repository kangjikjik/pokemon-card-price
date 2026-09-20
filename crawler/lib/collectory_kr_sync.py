"""Collectory KR 세트 — 공식 name_ko·pokemonkorea 이미지 (트레이너·아이템)."""
from __future__ import annotations

import re
from functools import lru_cache

import httpx

from kr_sets import COLLECTORY_IDS

API = "https://collectory.cc/api"


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def _card_num_int(card_number: str) -> int | None:
    if not card_number or "/" not in card_number:
        return None
    try:
        return int(card_number.split("/")[0])
    except ValueError:
        return None


def _kr_image_url(card: dict) -> str | None:
    url = (card.get("image_url") or card.get("cdn_image_url") or "").strip()
    if not url:
        return None
    if "pokemonkorea.co.kr" not in url and "cards.image.pokemonkorea" not in url:
        # cdn collectory jp — pokemonkorea URL 패턴 유추 (M6/099 등)
        m = re.search(r"/cards/jp/(M\d+[a-z]?)/(\d+)_", url, re.I)
        if m:
            pack, num = m.group(1), m.group(2).lstrip("0") or "0"
            candidate = (
                f"https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/"
                f"{pack}/{pack}_{num.zfill(3)}.png"
            )
            try:
                r = httpx.head(candidate, timeout=10, follow_redirects=True)
                if r.status_code == 200:
                    return candidate
            except Exception:
                pass
        return None
    return url.split("?")[0]


@lru_cache(maxsize=32)
def _fetch_kr_cards(set_code: str) -> list[dict]:
    cid = COLLECTORY_IDS.get(set_code.upper(), "")
    if not cid:
        return []
    r = httpx.get(
        f"{API}/sets/{cid}/cards",
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    r.raise_for_status()
    return r.json().get("cards", [])


_cache: dict[str, dict] = {}


def _indexes(set_code: str) -> dict:
    code = set_code.upper()
    if code in _cache:
        return _cache[code]
    cards = _fetch_kr_cards(code)
    by_ja: dict[str, list[dict]] = {}
    by_ko: dict[str, list[dict]] = {}
    by_num: dict[int, list[dict]] = {}
    trainers: set[int] = set()
    for c in cards:
        ctype = (c.get("card_type") or "").upper()
        if ctype in ("TRAINER", "ENERGY", "ITEM"):
            n = _card_num_int(c.get("card_number") or "")
            if n is not None:
                trainers.add(n)
        for key in ("name_ja", "name_jp"):
            ja = (c.get(key) or "").strip()
            if ja:
                by_ja.setdefault(_norm(ja), []).append(c)
        ko = (c.get("name_ko") or c.get("name") or "").strip()
        if ko:
            by_ko.setdefault(_norm(ko), []).append(c)
        n = _card_num_int(c.get("card_number") or "")
        if n is not None:
            by_num.setdefault(n, []).append(c)
    out = {"by_ja": by_ja, "by_ko": by_ko, "by_num": by_num, "trainers": trainers, "all": cards}
    _cache[code] = out
    return out


def trainer_card_numbers(set_code: str) -> frozenset[int]:
    return frozenset(_indexes(set_code)["trainers"])


def is_trainer_by_collectory(set_code: str, card_number: str, name_jp: str = "") -> bool:
    n = _card_num_int(card_number)
    if n is not None and n in trainer_card_numbers(set_code):
        return True
    ja = (name_jp or "").strip()
    if not ja:
        return False
    return _norm(ja) in _indexes(set_code)["by_ja"]


def _pick_hit(hits: list[dict], rarity: str) -> dict | None:
    if not hits:
        return None
    r = (rarity or "").upper()
    if r:
        for c in hits:
            if (c.get("rarity") or "").upper() == r:
                return c
        # 경기장 L/R·일반 U — Collectory는 U 한 종만 등록
        if r == "U":
            for c in hits:
                if (c.get("rarity") or "").upper() == "U":
                    return c
    return hits[0]


def _mega_pack_code(set_code: str) -> str | None:
    m = {
        "MG4": "M4",
        "MG4A": "M4a",
        "MG5": "M5",
        "MG5A": "M5a",
        "MG6": "M5",
        "MG7": "M6",
    }
    return m.get(set_code.upper())


def _pokemonkorea_from_collectory_num(set_code: str, card_number: str) -> str | None:
    pack = _mega_pack_code(set_code)
    n = _card_num_int(card_number)
    if not pack or n is None:
        return None
    candidate = (
        f"https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/"
        f"{pack}/{pack}_{n:03d}.png"
    )
    try:
        r = httpx.get(
            candidate,
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.pokemoncard.co.kr/"},
        )
        if r.status_code == 200 and len(r.content) > 1000:
            return candidate
    except Exception:
        pass
    return None


def _resolve_kr_image(hit: dict, set_code: str) -> str | None:
    """동일 등급 Collectory row의 한국 공식 이미지만 — 타 등급 fallback 금지."""
    img = _kr_image_url(hit)
    if img:
        return img
    num = hit.get("card_number") or ""
    return _pokemonkorea_from_collectory_num(set_code, num)


def official_kr_by_ko_name(
    set_code: str,
    name_ko: str,
    rarity: str = "",
) -> tuple[str | None, str | None]:
    """Collectory KR name_ko + 등급 → (공식명, pokemonkorea image)."""
    idx = _indexes(set_code)
    hit = _pick_hit(idx["by_ko"].get(_norm(name_ko), []), rarity)
    if not hit:
        return None, None
    ko = (hit.get("name_ko") or hit.get("name") or "").strip()
    img = _resolve_kr_image(hit, set_code)
    return ko or name_ko.strip(), img


def official_kr_for_card(
    set_code: str,
    name_jp: str,
    card_number: str = "",
    rarity: str = "",
    name_ko_hint: str = "",
) -> tuple[str | None, str | None]:
    """name_jp 또는 name_ko_hint → (KR 공식 name_ko, pokemonkorea image)."""
    idx = _indexes(set_code)
    ja = (name_jp or "").strip()
    if ja:
        hit = _pick_hit(idx["by_ja"].get(_norm(ja), []), rarity)
        if hit:
            ko = (hit.get("name_ko") or hit.get("name") or "").strip()
            img = _resolve_kr_image(hit, set_code)
            if ko:
                return ko, img
    ko_hint = (name_ko_hint or "").strip()
    if ko_hint:
        return official_kr_by_ko_name(set_code, ko_hint, rarity)
    return None, None


def official_kr_for_name_jp(
    set_code: str,
    name_jp: str,
    rarity: str = "",
) -> tuple[str | None, str | None]:
    return official_kr_for_card(set_code, name_jp, "", rarity)
