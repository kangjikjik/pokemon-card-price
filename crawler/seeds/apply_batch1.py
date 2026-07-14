"""1배치 3팩 — kr_sets + web lib 반영"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from batch1_verified import BATCH1_VERIFIED, VerifiedSet
from kr_sets import KR_SETS, KrSet
from revert_featured_55 import (
    load_jp_msrp,
    short_name,
    ts_key,
    write_constants,
    write_set_images,
    write_set_names,
)

KR_SETS_PATH = Path(__file__).with_name("kr_sets.py")
WEB = Path(__file__).resolve().parents[2] / "web" / "lib"


def to_krset(v: VerifiedSet) -> KrSet:
    return KrSet(
        code=v.code,
        name_kr=v.name_kr,
        released_at=v.released_at,
        box_image_kr=v.box_image_kr,
        bs_code=v.bs_code,
        collectory_id=v.collectory_id,
        msrp_pack_kr=v.msrp_pack_kr,
        msrp_box_kr=v.msrp_box_kr,
        pokemoncard_page=v.pokemoncard_page,
    )


def fmt_set(s: KrSet) -> str:
    return (
        f'    KrSet("{s.code}", "{s.name_kr}", "{s.released_at}",\n'
        f'          "{s.box_image_kr}",\n'
        f'          "{s.bs_code}", "{s.collectory_id}", '
        f"{s.msrp_pack_kr}, {s.msrp_box_kr}, {s.pokemoncard_page}),"
    )


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
    if "KR_SETS_ALL" not in new_text:
        new_text += "\nKR_SETS_ALL: list[KrSet] = KR_SETS\n"
    if "KR_BY_CODE" not in new_text:
        new_text += (
            "\nKR_BY_CODE: dict[str, KrSet] = {s.code: s for s in KR_SETS_ALL}\n"
            "\nFEATURED_SET_CODES: list[str] = [s.code for s in KR_SETS]\n"
            "\nRELEASE_DATES: dict[str, str] = {s.code: s.released_at for s in KR_SETS_ALL}\n"
            "NAME_KR: dict[str, str] = {s.code: s.name_kr for s in KR_SETS_ALL}\n"
            "KR_BOX_IMAGES: dict[str, str] = {s.code: s.box_image_kr for s in KR_SETS_ALL if s.box_image_kr}\n"
            "\nCOLLECTORY_IDS: dict[str, str] = {\n"
            "    s.code: s.collectory_id for s in KR_SETS_ALL if s.collectory_id\n"
            "}\n"
            "\nMSRP_KR: dict[str, tuple[int, int]] = {\n"
            "    s.code: (s.msrp_pack_kr, s.msrp_box_kr) for s in KR_SETS_ALL if s.msrp_pack_kr\n"
            "}\n"
            "POKEMONCARD_PAGE: dict[str, int] = {\n"
            "    s.code: s.pokemoncard_page for s in KR_SETS_ALL if s.pokemoncard_page\n"
            "}\n"
        )
    KR_SETS_PATH.write_text(new_text, encoding="utf-8")
    print(f"kr_sets.py -> {n}")


def ensure_kr_sets_footer() -> None:
    """KR_BY_CODE 등 하단 export 누락 시 복구"""
    text = KR_SETS_PATH.read_text(encoding="utf-8")
    if "KR_BY_CODE" in text:
        return
    footer = '''

KR_BY_CODE: dict[str, KrSet] = {s.code: s for s in KR_SETS_ALL}

FEATURED_SET_CODES: list[str] = [s.code for s in KR_SETS]

RELEASE_DATES: dict[str, str] = {s.code: s.released_at for s in KR_SETS_ALL}
NAME_KR: dict[str, str] = {s.code: s.name_kr for s in KR_SETS_ALL}
KR_BOX_IMAGES: dict[str, str] = {s.code: s.box_image_kr for s in KR_SETS_ALL if s.box_image_kr}

COLLECTORY_IDS: dict[str, str] = {
    s.code: s.collectory_id for s in KR_SETS_ALL if s.collectory_id
}

MSRP_KR: dict[str, tuple[int, int]] = {
    s.code: (s.msrp_pack_kr, s.msrp_box_kr) for s in KR_SETS_ALL if s.msrp_pack_kr
}
POKEMONCARD_PAGE: dict[str, int] = {
    s.code: s.pokemoncard_page for s in KR_SETS_ALL if s.pokemoncard_page
}
'''
    if "KR_SETS_ALL" not in text:
        text += "\nKR_SETS_ALL: list[KrSet] = KR_SETS\n"
    text += footer
    KR_SETS_PATH.write_text(text, encoding="utf-8")


def write_set_msrp(sets: list[KrSet]) -> None:
    jp = load_jp_msrp()
    # 신규 MEGA 3팩 JP 기본 (일본 공식)
    jp_defaults = {
        "MG4a": (550, 6050, "https://www.pokemon-card.com/ex/m2a/"),
        "MG2a": (290, 5800, "https://www.pokemon-card.com/ex/sv11/"),
        "MG1b": (180, 5400, "https://www.pokemon-card.com/products/sv/sv10.html"),
    }
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
        pack_jp = j.get("packJP", 0)
        box_jp = j.get("boxJP", 0)
        src_jp = j.get("sourceJP", "")
        if s.code in jp_defaults and not pack_jp:
            pack_jp, box_jp, src_jp = jp_defaults[s.code]
        lines = [
            f"  {ts_key(s.code)}: {{",
            f"    packKR: {s.msrp_pack_kr},",
            f"    boxKR: {s.msrp_box_kr},",
            f"    packJP: {pack_jp},",
            f"    boxJP: {box_jp},",
        ]
        if s.code == "MG4a":
            lines.extend([
                "    packLabelKR: '1팩 (5장)',",
                "    boxLabelKR: '1상자 (10팩)',",
            ])
        if s.pokemoncard_page:
            lines.append(f"    sourceKR: 'https://pokemoncard.co.kr/card/{s.pokemoncard_page}',")
        if src_jp:
            lines.append(f"    sourceJP: '{src_jp}',")
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
    print(f"set-msrp.ts synced (JP cache: {sum(1 for s in sets if jp.get(s.code))})")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    by_code = {s.code: s for s in KR_SETS}
    for v in BATCH1_VERIFIED:
        by_code[v.code] = to_krset(v)
    merged = sorted(by_code.values(), key=lambda s: s.released_at, reverse=True)
    write_kr_sets(merged)
    ensure_kr_sets_footer()
    write_constants([s.code for s in merged])
    write_set_names(merged)
    write_set_images(merged)
    write_set_msrp(merged)
    print("batch1 applied — featured 58")


if __name__ == "__main__":
    main()
