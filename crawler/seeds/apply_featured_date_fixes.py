"""featured_dates_audit.json 기반 — 발매일·가격 pokemoncard 공식값 반영 + 타임라인 재정렬"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import replace
from pathlib import Path

from kr_sets import KR_SETS, KrSet
from revert_featured_55 import (
    load_jp_msrp,
    short_name,
    ts_key,
    write_constants,
    write_kr_sets,
    write_set_images,
    write_set_names,
)

AUDIT = Path(__file__).with_name("featured_dates_audit.json")
WEB = Path(__file__).resolve().parents[2] / "web" / "lib"


def title_ok(name_kr: str, title: str) -> bool:
    if name_kr.startswith("25주년"):
        return "25" in title and "ANNIVERSARY" in title.upper()
    key = name_kr.replace(" ", "")[:4]
    t = title.replace(" ", "")
    return key in t or name_kr.replace(" ", "") in t


def write_set_msrp(sets: list[KrSet]) -> None:
    jp = load_jp_msrp()
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
        if not pack_jp and s.code in jp_defaults:
            pack_jp, box_jp, src_jp = jp_defaults[s.code]
        lines = [
            f"  {ts_key(s.code)}: {{",
            f"    packKR: {s.msrp_pack_kr},",
            f"    boxKR: {s.msrp_box_kr},",
            f"    packJP: {pack_jp},",
            f"    boxJP: {box_jp},",
        ]
        if s.pokemoncard_page:
            lines.append(f"    sourceKR: 'https://pokemoncard.co.kr/card/{s.pokemoncard_page}',")
        if src_jp:
            lines.append(f"    sourceJP: '{src_jp}',")
        lines.append("  },")
        blocks.extend(lines)
    blocks.extend([
        "};",
        "",
        "export function getSetMsrp(code: string): SetMsrp {",
        "  return SET_MSRP[code] ?? { packKR: 0, boxKR: 0, packJP: 0, boxJP: 0 };",
        "}",
        "",
        "export function formatYen(amount: number): string {",
        "  if (!amount) return '';",
        "  return `¥${amount.toLocaleString('ja-JP')}`;",
        "}",
        "",
    ])
    (WEB / "set-msrp.ts").write_text("\n".join(blocks), encoding="utf-8")
    print(f"set-msrp.ts -> {len(sets)}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    audit = {r["code"]: r for r in json.loads(AUDIT.read_text(encoding="utf-8"))}
    updated = []
    fixes = []

    for s in KR_SETS:
        r = audit.get(s.code)
        if not r or not r.get("official_date"):
            updated.append(s)
            continue
        if not title_ok(s.name_kr, r.get("title", "")):
            print(f"SKIP title mismatch {s.code}: {r.get('title')}")
            updated.append(s)
            continue
        ns = s
        if r["official_date"] != s.released_at:
            fixes.append(f"{s.code} date {s.released_at} -> {r['official_date']}")
            ns = replace(ns, released_at=r["official_date"])
        if r.get("official_pack") and r["official_pack"] != s.msrp_pack_kr:
            fixes.append(f"{s.code} pack {s.msrp_pack_kr} -> {r['official_pack']}")
            ns = replace(ns, msrp_pack_kr=r["official_pack"])
        if r.get("official_box") and r["official_box"] != s.msrp_box_kr:
            fixes.append(f"{s.code} box {s.msrp_box_kr} -> {r['official_box']}")
            ns = replace(ns, msrp_box_kr=r["official_box"])
        updated.append(ns)

    updated.sort(key=lambda x: x.released_at, reverse=True)
    codes = [s.code for s in updated]

    print(f"fixes: {len(fixes)}")
    for f in fixes:
        print(f"  {f}")

    write_kr_sets(updated)
    write_constants(codes)
    write_set_names(updated)
    write_set_images(updated)
    write_set_msrp(updated)
    print(f"done — featured {len(updated)} (timeline re-sorted)")


if __name__ == "__main__":
    main()
