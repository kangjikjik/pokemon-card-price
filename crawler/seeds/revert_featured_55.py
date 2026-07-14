"""featured 55팩 복원 + web lib 동기화"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from kr_sets import KR_SETS, KrSet

# 타임라인 갭 일괄 추가분(45) — 제거 대상
REMOVE_CODES = frozenset({
    "MG4a", "MG2a", "MG1b",
    "S2", "S1a", "S1W", "S1H", "SM12a", "SM12", "SM11b", "SM11a", "SM10",
    "SM9", "SM8b", "SM9a", "SM8", "SM7", "SM7a", "SM6b", "SM6a", "SM6",
    "SM5+", "SM5", "SM4+", "SM4", "SM4a", "SM2+", "SM1+", "SM1M", "SM1C",
    "CP6", "XY11", "XY8a", "XY9", "XY7", "XY6", "XY5a", "XY5b", "XY4",
    "XY3", "XY2", "EBB1", "XY5", "XY3a", "BW4",
})

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "lib"
KR_SETS_PATH = Path(__file__).with_name("kr_sets.py")
MSRP_CHUNK = WEB / ".open-next/assets/_next/static/chunks/922-aaa070482ab3db17.js"


def ts_key(code: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", code):
        return code
    return f"'{code}'"


def short_name(name: str) -> str:
    return name.replace(" ", "").replace("「", "").replace("」", "")[:20]


def fmt_set(s: KrSet) -> str:
    return (
        f'    KrSet("{s.code}", "{s.name_kr}", "{s.released_at}",\n'
        f'          "{s.box_image_kr}",\n'
        f'          "{s.bs_code}", "{s.collectory_id}", '
        f"{s.msrp_pack_kr}, {s.msrp_box_kr}, {s.pokemoncard_page}),"
    )


def load_jp_msrp() -> dict[str, dict]:
    chunk = MSRP_CHUNK
    if not chunk.exists():
        for p in (WEB / ".open-next").rglob("922-*.js"):
            chunk = p
            break
    if not chunk.exists():
        return {}
    text = chunk.read_text(encoding="utf-8")
    entry_re = re.compile(
        r"([A-Z0-9+]+):\{packKR:([\de]+),boxKR:([\de]+),packJP:([\de]+),boxJP:([\de]+)"
        r'(?:,packLabelKR:"[^"]*")?(?:,boxLabelKR:"[^"]*")?'
        r'(?:,sourceKR:"([^"]*)")?(?:,sourceJP:"([^"]*)")?\}'
    )

    def n(s: str) -> int:
        return int(float(s)) if "e" in s else int(s)

    return {
        m.group(1): {
            "packJP": n(m.group(4)),
            "boxJP": n(m.group(5)),
            "sourceJP": m.group(7) or "",
        }
        for m in entry_re.finditer(text)
    }


def write_kr_sets(sets: list[KrSet]) -> None:
    text = KR_SETS_PATH.read_text(encoding="utf-8")
    n = len(sets)
    block = "\n".join(fmt_set(s) for s in sets)
    new_text = re.sub(
        r"# featured \d+.*?\nKR_SETS: list\[KrSet\] = \[.*?\n\]",
        f"# featured {n} — 한국 발매일 최신순 (pokemoncard.co.kr 검증)\nKR_SETS: list[KrSet] = [\n{block}\n]",
        text,
        count=1,
        flags=re.S,
    )
    new_text = re.sub(
        r"KR_SETS_ALL: list\[KrSet\] = KR_SETS.*",
        "KR_SETS_ALL: list[KrSet] = KR_SETS\n\n"
        "KR_BY_CODE: dict[str, KrSet] = {s.code: s for s in KR_SETS_ALL}\n\n"
        "FEATURED_SET_CODES: list[str] = [s.code for s in KR_SETS]\n\n"
        "RELEASE_DATES: dict[str, str] = {s.code: s.released_at for s in KR_SETS_ALL}\n"
        "NAME_KR: dict[str, str] = {s.code: s.name_kr for s in KR_SETS_ALL}\n"
        "KR_BOX_IMAGES: dict[str, str] = {s.code: s.box_image_kr for s in KR_SETS_ALL if s.box_image_kr}\n\n"
        "COLLECTORY_IDS: dict[str, str] = {\n"
        "    s.code: s.collectory_id for s in KR_SETS_ALL if s.collectory_id\n"
        "}\n\n"
        "MSRP_KR: dict[str, tuple[int, int]] = {\n"
        "    s.code: (s.msrp_pack_kr, s.msrp_box_kr) for s in KR_SETS_ALL if s.msrp_pack_kr\n"
        "}\n"
        "POKEMONCARD_PAGE: dict[str, int] = {\n"
        "    s.code: s.pokemoncard_page for s in KR_SETS_ALL if s.pokemoncard_page\n"
        "}",
        new_text,
        count=1,
        flags=re.S,
    )
    KR_SETS_PATH.write_text(new_text, encoding="utf-8")
    print(f"kr_sets.py -> {n}")


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
    text = re.sub(r"export const FEATURED_SET_LIMIT = \d+;", f"export const FEATURED_SET_LIMIT = {n};", text)
    path.write_text(text, encoding="utf-8")


def write_set_names(sets: list[KrSet]) -> None:
    entries = "\n".join(f"  {ts_key(s.code)}: '{short_name(s.name_kr)}'," for s in sets)
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


def write_set_images(sets: list[KrSet]) -> None:
    entries = "\n".join(f"  {ts_key(s.code)}: '{s.box_image_kr}'," for s in sets if s.box_image_kr)
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


def write_set_msrp(sets: list[KrSet]) -> None:
    jp = load_jp_msrp()
    blocks = [
        "/** 확장팩 공식 발매가 — pokemoncard.co.kr / pokemon-card.com 제품 페이지 검증값 */",
        "",
        "export type SetMsrp = {",
        "  packKR: number;",
        "  boxKR: number;",
        "  packJP: number;",
        "  boxJP: number;",
        "  packLabelKR?: string;",
        "  boxLabelKR?: string;",
        "  sourceKR?: string;",
        "  sourceJP?: string;",
        "};",
        "",
        f"/** featured {len(sets)} — pokemoncard.co.kr 검증 */",
        "export const SET_MSRP: Record<string, SetMsrp> = {",
    ]
    for s in sets:
        if not s.msrp_pack_kr:
            continue
        j = jp.get(s.code, {})
        lines = [
            f"  {ts_key(s.code)}: {{",
            f"    packKR: {s.msrp_pack_kr},",
            f"    boxKR: {s.msrp_box_kr},",
            f"    packJP: {j.get('packJP', 0)},",
            f"    boxJP: {j.get('boxJP', 0)},",
        ]
        if s.pokemoncard_page:
            lines.append(f"    sourceKR: 'https://pokemoncard.co.kr/card/{s.pokemoncard_page}',")
        if j.get("sourceJP"):
            lines.append(f"    sourceJP: '{j['sourceJP']}',")
        lines.append("  },")
        blocks.extend(lines)
    blocks.extend([
        "};",
        "",
        "const DEFAULT_MSRP: SetMsrp = { packKR: 1000, boxKR: 30000, packJP: 180, boxJP: 5400 };",
        "",
        "export function getSetMsrp(code: string): SetMsrp {",
        "  return SET_MSRP[code] ?? DEFAULT_MSRP;",
        "}",
        "",
        "export function formatYen(amount: number): string {",
        "  return new Intl.NumberFormat('ja-JP').format(amount) + '円';",
        "}",
        "",
    ])
    (WEB / "set-msrp.ts").write_text("\n".join(blocks), encoding="utf-8")
    print(f"set-msrp.ts — JP from cache: {sum(1 for s in sets if jp.get(s.code))}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    kept = [s for s in KR_SETS if s.code not in REMOVE_CODES]
    kept.sort(key=lambda s: s.released_at, reverse=True)
    if len(kept) != 55:
        print(f"WARN: expected 55, got {len(kept)}")
    write_kr_sets(kept)
    codes = [s.code for s in kept]
    write_constants(codes)
    write_set_names(kept)
    write_set_images(kept)
    write_set_msrp(kept)
    print("done — featured 55 restored")


if __name__ == "__main__":
    main()
