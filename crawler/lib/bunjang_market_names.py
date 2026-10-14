"""번개장터 검색·제목매칭용 한글 이름.

번개장터는 한국 사이트 → 검색어·매칭에 **한글 시장 표기만** 사용.
일본어(name_jp)는 SNK/Collectory 전용.

공식 name_kr(포켓몬 카드 게임 한글명)과 번개 매물 제목 표기가 다를 때 alias로 보완.
"""
from __future__ import annotations

import re

from lib.price_search import name_matches_spaced_title, normalize_mega_spelling

# DB/시드에 잘못 들어간 name_kr → 공식 한글명
KR_DISPLAY_FIXUPS: dict[str, str] = {
    "다크 펜던트": "다크벨",
}

# name_jp → 번개에서 쓰는 추가 한글 검색어 (공식명과 별도)
JP_BUNJANG_ALIASES: dict[str, list[str]] = {
    "アイアンディフェンダー": ["아이언 디펜드업", "아이언디펜더"],
    "エネルギーつけかえ": ["에너지 갈아 달기", "에너지갈아달기", "에너지 갈아달기"],
    "クラッシュハンマー": ["크래시 해머", "크래시해머"],
    "ダークベル": [],
    "ごうかいボム": ["호쾌봄", "고우카이봄"],
    "ブレイブバングル": ["브레이브뱅글", "브레이브 뱅글"],
    "カスミの元気": ["이슬의 기력", "카스미의 원기"],
    "グラジオの決戦": ["글\uB77C\uB514\uC624\uC758 \uACB0\uC804", "글래디온의 승부"],
    "サビ組のしたっぱ": ["녹청파의 조무래기", "러스트 신디케이트 조무래기"],
}

_EX_SUFFIXES = (" ex", " EX", " VSTAR", " VMAX", " V", " GX")
MEGA_PREFIX = "메가"


def _dedupe_hangul_queries(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen and _has_hangul(q):
            seen.add(q)
            out.append(q)
    return out


def fix_display_name_kr(name_kr: str) -> str:
    n = normalize_mega_spelling((name_kr or "").strip())
    return KR_DISPLAY_FIXUPS.get(n, n)


def _strip_ex(name: str) -> str:
    core = name.strip()
    for suf in _EX_SUFFIXES:
        if core.endswith(suf):
            return core[: -len(suf)].strip()
    return core


def pokemon_core_name(name_kr: str) -> str:
    """메가다크라이 ex → 다크라이 (MUR 등 짧은 검색용)."""
    core = _strip_ex(name_kr)
    compact = re.sub(r"\s+", "", core)
    if compact.startswith(MEGA_PREFIX) and len(compact) > len(MEGA_PREFIX):
        return compact[len(MEGA_PREFIX) :].strip()
    return core


def _has_hangul(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


def bunjang_search_names(
    name_kr: str,
    name_jp: str = "",
    name_en: str = "",
    rarity: str = "",
    card_number: str = "",
    set_code: str = "",
) -> list[str]:
    """번개 검색·제목매칭용 한글 이름 (일본어·영문 원문 제외)."""
    seen: set[str] = set()
    out: list[str] = []

    def add(s: str) -> None:
        s = re.sub(r"\s+", " ", (s or "").strip())
        if len(s) < 2 or not _has_hangul(s):
            return
        if s not in seen:
            seen.add(s)
            out.append(s)

    kr = fix_display_name_kr(name_kr)
    jp = (name_jp or "").strip()
    r = (rarity or "").upper()

    if kr:
        add(kr)
        compact = re.sub(r"\s+", "", kr)
        if compact != kr:
            add(compact)
        core = _strip_ex(kr)
        if core != kr:
            add(core)
            add(f"{core} ex")
            add(f"{core} EX")
        if compact.startswith(MEGA_PREFIX) and len(compact) > len(MEGA_PREFIX):
            rest = compact[len(MEGA_PREFIX) :].strip()
            add(f"{MEGA_PREFIX} {rest}")
            add(f"{MEGA_PREFIX} {rest} ex")
            add(f"{MEGA_PREFIX} {rest} EX")
            if rest:
                add(rest)
                add(f"{rest} ex")

    for alias in JP_BUNJANG_ALIASES.get(jp, []):
        add(alias)

    r = (rarity or "").upper()
    if r == "MUR" and kr:
        poke = pokemon_core_name(kr)
        poke_stripped = _strip_ex(poke) if poke else poke
        mur_first: list[str] = []
        for label in filter(
            None,
            [poke_stripped, poke, f"메가{poke_stripped}", f"메가 {poke_stripped}", f"메가{poke_stripped}ex"],
        ):
            if label not in seen and _has_hangul(label):
                seen.add(label)
                mur_first.append(label)
        out = mur_first + out

    return out


def build_bunjang_jp_queries(
    set_name_kr: str,
    name_kr: str,
    name_jp: str,
    rarity: str,
    card_number: str = "",
    set_code: str = "",
    *,
    name_en: str = "",
    slim: bool = False,
) -> list[str]:
    """번개 일판 검색어 — **카드명 + 등급 + 일판** (M5·팩번호 금지)."""
    from lib.price_search import COMMEMORATIVE_YEAR_IN_TITLE  # noqa: PLC0415

    r = (rarity or "").upper()
    names = bunjang_search_names(name_kr, name_jp, name_en, rarity, card_number, set_code)
    code = (set_code or "").upper()
    fixed_name = fix_display_name_kr(name_kr)

    def finish_jp(found: list[str]) -> list[str]:
        from lib.art_split import extra_split_art_queries  # noqa: PLC0415

        merged = list(found)
        merged.extend(
            extra_split_art_queries(
                set_name_kr, fixed_name, r, card_number, set_code, jp=True
            )
        )
        return _dedupe_hangul_queries(merged)

    if r == "S" and fixed_name:
        from lib.price_search import shiny_s_search_queries  # noqa: PLC0415

        return finish_jp([f"{q} 일판" for q in shiny_s_search_queries(fixed_name)])

    if code == "SV4M" and "무쇠무인" in fixed_name and r == "SAR":
        return finish_jp([
            "미래의 일섬 무쇠무인 ex sar 일판",
            "미래의 일섬 무쇠무인ex sar 일판",
        ])

    if code == "SV8" and "무쇠무인" in fixed_name and r == "SAR":
        return finish_jp([
            "테라스탈 페스타 무쇠무인 ex sar 일판",
            "테라스탈페스타 무쇠무인 ex sar 일판",
            "테라스텔 페스타 무쇠무인 ex sar 일판",
        ])

    if code == "SV4" and "팬텀" in fixed_name and r == "RR":
        queries_phantom = [
            "와일드 포스 팬텀 ex rr 일판",
            "와일드포스 팬텀 ex rr 일판",
            "포켓몬카드 와일드 포스 팬텀 ex rr 일판",
        ]
    else:
        queries_phantom = []

    commemorative_prefix = COMMEMORATIVE_YEAR_IN_TITLE.get((set_code or "").upper())
    queries: list[str] = list(queries_phantom)
    limit = 12 if r == "MUR" else 8

    if commemorative_prefix:
        from lib.price_search import commemorative_card_search_queries, is_cel30_cc  # noqa: PLC0415

        for base in names[:limit]:
            for q in commemorative_card_search_queries(
                commemorative_prefix, base, r, set_name_kr, set_code
            ):
                queries.append(f"{q} 일판")
                if "일판" not in q:
                    queries.append(q)
            compact = re.sub(r"\s+", "", base)
            if is_cel30_cc(set_code, r):
                queries.append(f"{commemorative_prefix} 복각 {compact}일판")
            else:
                queries.append(f"{commemorative_prefix} {compact}{r}일판")
        seen: set[str] = set()
        out: list[str] = []
        for q in queries:
            q = re.sub(r"\s+", " ", q).strip()
            if q and q not in seen and _has_hangul(q):
                seen.add(q)
                out.append(q)
        return finish_jp(out)

    for base in names[:limit]:
        compact = re.sub(r"\s+", "", base)
        queries.append(f"{base} {r} 일판")
        queries.append(f"{compact}{r}일판")
        queries.append(f"{base} {r}")

    if not slim:
        for base in names[:4]:
            queries.append(f"포켓몬카드 {base} {r} 일판")
        if set_name_kr and name_kr and r:
            fixed = fix_display_name_kr(name_kr)
            queries.append(f"{set_name_kr} {fixed} {r} 일판")

    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen and _has_hangul(q):
            seen.add(q)
            out.append(q)
    return finish_jp(out)


def title_matches_bunjang_name(
    title: str,
    name_kr: str,
    name_jp: str = "",
    name_en: str = "",
    rarity: str = "",
    card_number: str = "",
    set_code: str = "",
) -> bool:
    """매물 제목이 카드와 일치하는지 (번개 한글 표기 기준)."""
    from lib.price_search import match_pikachu_pkr_name_in_title  # noqa: PLC0415

    if not title.strip():
        return False
    if match_pikachu_pkr_name_in_title(title, name_kr):
        return True
    for cand in bunjang_search_names(
        name_kr, name_jp, name_en, rarity, card_number, set_code
    ):
        if name_matches_spaced_title(title, cand):
            return True
        core = _strip_ex(cand)
        if core != cand and len(core) >= 2 and name_matches_spaced_title(title, core):
            return True
    return False
