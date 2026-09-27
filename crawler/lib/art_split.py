"""그림이 다른 같은 이름·같은 등급은 제목의 카드번호 또는 팩 이름으로만 수집한다.

그림이 같은 묶음(web/lib/same-art-price-groups.ts)은 한 카드로 보고 이 제한을 쓰지 않는다.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from pathlib import Path

from lib.price_search import (
    CARD_NUMBER_RE,
    normalize_card_number,
    normalize_mega_spelling,
)

_LOCK = threading.Lock()
_INDEX: "SplitIndex | None" = None

_GROUPS_PATH = (
    Path(__file__).resolve().parents[2] / "web" / "lib" / "same-art-price-groups.ts"
)


@dataclass(frozen=True)
class ArtCard:
    id: int
    name_key: str
    rarity: str
    card_number: str
    set_code: str
    set_name: str
    art_key: frozenset[int]


class SplitIndex:
    def __init__(self, cards: list[ArtCard]) -> None:
        self.by_cohort: dict[tuple[str, str], list[ArtCard]] = {}
        for card in cards:
            self.by_cohort.setdefault((card.name_key, card.rarity), []).append(card)

    def accepts(
        self,
        title: str,
        name_kr: str,
        rarity: str,
        card_number: str,
        set_code: str,
    ) -> bool:
        cohort = self.by_cohort.get((_name_key(name_kr), (rarity or "").upper()), [])
        if len({c.art_key for c in cohort}) < 2:
            return True
        mine = _match_card(cohort, card_number, set_code)
        if mine is None:
            return True
        own = [c for c in cohort if c.art_key == mine.art_key]
        other = [c for c in cohort if c.art_key != mine.art_key]
        return _title_picks_art(title, own, other)


def title_matches_split_art(
    title: str,
    name_kr: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    set_name_kr: str = "",
) -> bool:
    """나눌 카드가 아니면 통과. 나누면 제목의 번호 또는 팩 이름이 이 그림과 같아야 한다."""
    del set_name_kr  # 팩 이름은 DB 세트명으로 비교한다.
    return get_index().accepts(title, name_kr, rarity, card_number, set_code)


def extra_split_art_queries(
    set_name: str,
    name_kr: str,
    rarity: str,
    card_number: str,
    set_code: str,
    *,
    jp: bool = False,
) -> list[str]:
    """그림이 다른 카드의 검색어에 팩 이름·카드번호를 붙인다."""
    if not _is_split(name_kr, rarity, card_number, set_code):
        return []
    r = (rarity or "").upper()
    base = normalize_mega_spelling((name_kr or "").strip())
    labels = [x.strip() for x in ((set_name or ""), (card_number or "")) if x and x.strip()]
    out: list[str] = []
    for label in labels:
        if r == "S":
            q = f"{base} 이로치 {label}"
        else:
            q = f"{base} {r} {label}"
        if jp:
            q = f"{q} 일판"
        q = re.sub(r"\s+", " ", q).strip()
        if q:
            out.append(q)
    return out


def get_index() -> SplitIndex:
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    with _LOCK:
        if _INDEX is None:
            _INDEX = _load_index()
        return _INDEX


def _is_split(name_kr: str, rarity: str, card_number: str, set_code: str) -> bool:
    index = get_index()
    cohort = index.by_cohort.get((_name_key(name_kr), (rarity or "").upper()), [])
    if len({c.art_key for c in cohort}) < 2:
        return False
    return _match_card(cohort, card_number, set_code) is not None


def _name_key(name: str) -> str:
    return re.sub(r"\s+", "", normalize_mega_spelling(name or "")).lower()


def _match_card(cohort: list[ArtCard], card_number: str, set_code: str) -> ArtCard | None:
    num = normalize_card_number(card_number)
    code = (set_code or "").upper()
    for card in cohort:
        if card.set_code.upper() == code and normalize_card_number(card.card_number) == num:
            return card
    return None


def _title_numbers(title: str) -> set[str]:
    return {normalize_card_number(m) for m in CARD_NUMBER_RE.findall(title or "")}


def _set_tokens(name: str) -> set[str]:
    compact = re.sub(r"\s+", "", name or "").lower()
    hangul = re.sub(r"\s+", "", "".join(re.findall(r"[가-힣]+", name or ""))).lower()
    out: set[str] = set()
    if len(compact) >= 4:
        out.add(compact)
    if len(hangul) >= 2:
        out.add(hangul)
    return out


def _token_in_title(title: str, token: str) -> bool:
    compact = re.sub(r"\s+", "", title or "").lower()
    return len(token) >= 2 and token in compact


def _distinctive_tokens(own: list[ArtCard], other: list[ArtCard]) -> set[str]:
    own_tokens: set[str] = set()
    for card in own:
        own_tokens |= _set_tokens(card.set_name)
    other_tokens: set[str] = set()
    for card in other:
        other_tokens |= _set_tokens(card.set_name)
    kept: set[str] = set()
    for token in own_tokens:
        if any(token in other or other in token for other in other_tokens):
            continue
        kept.add(token)
    return kept


def _title_picks_art(title: str, own: list[ArtCard], other: list[ArtCard]) -> bool:
    title_nums = _title_numbers(title)
    own_nums = {normalize_card_number(c.card_number) for c in own if c.card_number}
    other_nums = {normalize_card_number(c.card_number) for c in other if c.card_number}
    own_nums.discard("")
    other_nums.discard("")
    has_own_num = bool(title_nums & own_nums)
    has_other_num = bool(title_nums & other_nums)
    if has_own_num and not has_other_num:
        return True
    if has_other_num and not has_own_num:
        return False
    own_sets = _distinctive_tokens(own, other)
    other_sets = _distinctive_tokens(other, own)
    has_own_set = any(_token_in_title(title, token) for token in own_sets)
    has_other_set = any(_token_in_title(title, token) for token in other_sets)
    return has_own_set and not has_other_set


def _load_same_art_groups() -> dict[int, frozenset[int]]:
    text = _GROUPS_PATH.read_text(encoding="utf-8")
    groups: dict[int, frozenset[int]] = {}
    for raw in re.findall(r"\[(\d+(?:\s*,\s*\d+)+)\]", text):
        ids = frozenset(int(n) for n in raw.split(","))
        for card_id in ids:
            groups[card_id] = ids
    return groups


def _load_index() -> SplitIndex:
    from utils.db import get_supabase  # noqa: PLC0415

    sb = get_supabase()
    groups = _load_same_art_groups()
    set_rows: list[dict] = []
    start = 0
    while True:
        batch = (
            sb.table("card_sets")
            .select("id,set_code,name_kr")
            .order("id")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        set_rows.extend(batch)
        if len(batch) < 1000:
            break
        start += 1000
    sets = {row["id"]: row for row in set_rows}

    cards: list[ArtCard] = []
    start = 0
    while True:
        batch = (
            sb.table("cards")
            .select("id,name_kr,rarity,card_number,set_id")
            .order("id")
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        for row in batch:
            meta = sets.get(row.get("set_id")) or {}
            card_id = int(row["id"])
            cards.append(
                ArtCard(
                    id=card_id,
                    name_key=_name_key(row.get("name_kr") or ""),
                    rarity=(row.get("rarity") or "").upper(),
                    card_number=row.get("card_number") or "",
                    set_code=meta.get("set_code") or "",
                    set_name=meta.get("name_kr") or "",
                    art_key=groups.get(card_id, frozenset({card_id})),
                )
            )
        if len(batch) < 1000:
            break
        start += 1000
    return SplitIndex(cards)
