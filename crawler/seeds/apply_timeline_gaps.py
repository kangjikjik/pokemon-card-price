"""kr_sets featured + 갭 병합 → kr_sets.py / web lib 동기화"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

from gap_sets import CODE_BY_NAME, DEFAULT_MSRP, HIGH_CLASS_CODES, HIGH_CLASS_MSRP
from kr_sets import KR_SETS, KrSet

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "lib"
MSRP_JSON = Path(__file__).with_name("timeline_gaps_msrp.json")

SKIP = (
    "스타트", "배틀 강화", "배틀 아카데미", "프리미엄 트레이너",
    "스페셜 덱", "랜덤 스타트", "강화 BOX", "트레이너 박스",
    "배틀컬렉션", "스타트 덱", "&",
    "GOLDEN BOX", "GOLDEN", "패밀리",
    "스페셜 세트", "스페셜 케이스", "스페셜 점보",
    "카드 앨범", "카드 실드", "TAG TEAM GX 스타터",
    "프리미엄 챔피언팩", "포켓심쿵", "레전드 컬렉션",
    "환상 전설 드림", "마그마단vs아쿠아단", "샤이니 컬렉션",
)
MIN_CARDS = 70


def norm(s: str) -> str:
    return (s or "").replace(" ", "").lower()


def load_msrp() -> dict[str, dict]:
    if not MSRP_JSON.exists():
        return {}
    return {r["code"]: r for r in json.loads(MSRP_JSON.read_text(encoding="utf-8"))}


def fetch_gaps() -> list[KrSet]:
    from kr_sets import FEATURED_SET_CODES, KR_BY_CODE

    featured_ids = {
        KR_BY_CODE[c].collectory_id
        for c in FEATURED_SET_CODES
        if c in KR_BY_CODE and KR_BY_CODE[c].collectory_id
    }
    featured_names = {norm(KR_BY_CODE[c].name_kr) for c in FEATURED_SET_CODES if c in KR_BY_CODE}
    msrp_map = load_msrp()

    r = httpx.get("https://collectory.cc/api/sets", timeout=60)
    kr = [s for s in r.json().get("sets") or [] if (s.get("set_code_ko") or "").startswith("BS")]
    client = httpx.Client(timeout=90)
    out: list[KrSet] = []
    seen_codes: set[str] = set()

    for s in sorted(kr, key=lambda x: x.get("release_date_ko") or "", reverse=True):
        cid = s["id"]
        name = s.get("name_ko") or ""
        if cid in featured_ids or any(x in name for x in SKIP):
            continue
        if norm(name) in featured_names:
            continue
        cnt = len(client.get(f"https://collectory.cc/api/sets/{cid}/cards").json().get("cards") or [])
        if cnt < MIN_CARDS:
            continue
        if name not in CODE_BY_NAME:
            raise KeyError(f"unmapped gap set: {name}")
        code, display = CODE_BY_NAME[name]
        if code in seen_codes:
            raise ValueError(f"duplicate code {code} for {name}")
        seen_codes.add(code)

        scraped = msrp_map.get(code, {})
        pack, box = DEFAULT_MSRP
        page = scraped.get("page") or 0
        if scraped.get("pack"):
            pack, box = scraped["pack"], scraped["box"]
        elif code in HIGH_CLASS_CODES:
            pack, box = HIGH_CLASS_MSRP

        out.append(
            KrSet(
                code=code,
                name_kr=display,
                released_at=s.get("release_date_ko") or "",
                box_image_kr=s.get("image_url") or "",
                bs_code=s.get("set_code_ko") or "",
                collectory_id=cid,
                msrp_pack_kr=pack,
                msrp_box_kr=box,
                pokemoncard_page=page,
            )
        )
    return out


def merge_sets() -> list[KrSet]:
    existing = {s.code: s for s in KR_SETS}
    gaps = fetch_gaps()
    merged: dict[str, KrSet] = dict(existing)
    for g in gaps:
        merged[g.code] = g
    return sorted(merged.values(), key=lambda s: s.released_at, reverse=True)


def fmt_set(s: KrSet) -> str:
    return (
        f'    KrSet("{s.code}", "{s.name_kr}", "{s.released_at}",\n'
        f'          "{s.box_image_kr}",\n'
        f'          "{s.bs_code}", "{s.collectory_id}", '
        f"{s.msrp_pack_kr}, {s.msrp_box_kr}, {s.pokemoncard_page}),"
    )


def write_kr_sets(merged: list[KrSet]) -> None:
    path = Path(__file__).with_name("kr_sets.py")
    text = path.read_text(encoding="utf-8")
    n = len(merged)
    block = "\n".join(fmt_set(s) for s in merged)
    new_text = re.sub(
        r"# featured \d+.*?\nKR_SETS: list\[KrSet\] = \[.*?\n\]",
        f"# featured {n} — 한국 발매일 최신순 (pokemoncard.co.kr 검증)\nKR_SETS: list[KrSet] = [\n{block}\n]",
        text,
        count=1,
        flags=re.S,
    )
    new_text = re.sub(
        r"KR_SETS_ALL: list\[KrSet\] = KR_SETS \+ \[.*?\]",
        "KR_SETS_ALL: list[KrSet] = KR_SETS",
        new_text,
        count=1,
        flags=re.S,
    )
    path.write_text(new_text, encoding="utf-8")
    print(f"kr_sets.py -> {n} featured")


def ts_key(code: str) -> str:
    """TS 객체 키 — + 등 특수문자는 따옴표 필요"""
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", code):
        return code
    return f"'{code}'"


def short_name(name: str) -> str:
    return name.replace(" ", "").replace("「", "").replace("」", "")[:20]


def write_constants(codes: list[str]) -> None:
    lines = ",\n  ".join(f"'{c}'" for c in codes)
    path = WEB / "constants.ts"
    text = path.read_text(encoding="utf-8")
    n = len(codes)
    text = re.sub(
        r"/\*\* 노출 \d+개.*?\*/\nexport const FEATURED_SET_CODES = \[.*?\] as const;",
        f"/** 노출 {n}개 — crawler/seeds/kr_sets.py 와 동기화 (한국 발매일 최신순) */\n"
        f"export const FEATURED_SET_CODES = [\n  {lines},\n] as const;",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"export const FEATURED_SET_LIMIT = \d+;",
        f"export const FEATURED_SET_LIMIT = {n};",
        text,
    )
    path.write_text(text, encoding="utf-8")
    print(f"constants.ts -> {n}")


def write_set_names(merged: list[KrSet]) -> None:
    entries = "\n".join(f"  {ts_key(s.code)}: '{short_name(s.name_kr)}'," for s in merged)
    path = WEB / "set-names.ts"
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"export const SET_SHORT_NAMES: Record<string, string> = \{.*?\};",
        f"export const SET_SHORT_NAMES: Record<string, string> = {{\n{entries}\n}};",
        text,
        count=1,
        flags=re.S,
    )
    path.write_text(text, encoding="utf-8")
    print("set-names.ts synced")


def write_set_images(merged: list[KrSet]) -> None:
    entries = "\n".join(
        f"  {ts_key(s.code)}: '{s.box_image_kr}'," for s in merged if s.box_image_kr
    )
    path = WEB / "set-images.ts"
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"export const SET_BOX_IMAGES: Record<string, string> = \{.*?\};",
        f"export const SET_BOX_IMAGES: Record<string, string> = {{\n{entries}\n}};",
        text,
        count=1,
        flags=re.S,
    )
    path.write_text(text, encoding="utf-8")
    print("set-images.ts synced")


def write_set_msrp(merged: list[KrSet]) -> None:
    path = WEB / "set-msrp.ts"
    # 기존 JP 발매가 보존
    existing_jp: dict[str, dict] = {}
    if path.exists():
        old = path.read_text(encoding="utf-8")
        for m in re.finditer(
            r"(\w+): \{[^}]*?packJP: ([\d,]+),[^}]*?boxJP: ([\d,]+)"
            r"(?:,[^}]*?sourceJP: '([^']*)')?",
            old,
            re.S,
        ):
            existing_jp[m.group(1)] = {
                "packJP": int(m.group(2).replace(",", "")),
                "boxJP": int(m.group(3).replace(",", "")),
                "sourceJP": m.group(4) or "",
            }

    blocks = []
    for s in merged:
        if not s.msrp_pack_kr:
            continue
        j = existing_jp.get(s.code, {})
        pack_jp = j.get("packJP", 0)
        box_jp = j.get("boxJP", 0)
        if not pack_jp and s.code in HIGH_CLASS_CODES:
            pack_jp, box_jp = HIGH_CLASS_MSRP
        src = (
            f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}"
            if s.pokemoncard_page
            else ""
        )
        src_jp = j.get("sourceJP", "")
        lines = [
            f"  {ts_key(s.code)}: {{",
            f"    packKR: {s.msrp_pack_kr:,},",
            f"    boxKR: {s.msrp_box_kr:,},",
            f"    packJP: {pack_jp:,},",
            f"    boxJP: {box_jp:,},",
        ]
        if src:
            lines.append(f"    sourceKR: '{src}',")
        if src_jp:
            lines.append(f"    sourceJP: '{src_jp}',")
        lines.append("  },")
        blocks.append("\n".join(lines))

    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"/\*\* featured \d+.*?\*/\nexport const SET_MSRP: Record<string, SetMsrp> = \{.*?\n\};",
        f"/** featured {len(merged)} — pokemoncard.co.kr 검증 */\n"
        f"export const SET_MSRP: Record<string, SetMsrp> = {{\n"
        + "\n".join(blocks)
        + "\n};",
        text,
        count=1,
        flags=re.S,
    )
    path.write_text(text, encoding="utf-8")
    print("set-msrp.ts synced")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    merged = merge_sets()
    write_kr_sets(merged)
    # reload after write
    import importlib
    import kr_sets as ks_mod
    importlib.reload(ks_mod)
    codes = [s.code for s in ks_mod.KR_SETS]
    write_constants(codes)
    write_set_names(merged)
    write_set_images(merged)
    write_set_msrp(merged)
    print(f"done: {len(merged)} sets")


if __name__ == "__main__":
    main()
