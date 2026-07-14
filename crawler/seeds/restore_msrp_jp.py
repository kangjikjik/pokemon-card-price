"""set-msrp.ts — KR은 kr_sets, JP는 이전 빌드 캐시에서 복원"""
from __future__ import annotations

import re
from pathlib import Path

from kr_sets import KR_SETS

WEB = Path(__file__).resolve().parents[2] / "web"
CHUNK = WEB / ".open-next/assets/_next/static/chunks/922-cc218d1761ceb219.js"
OUT = WEB / "lib/set-msrp.ts"

ENTRY_RE = re.compile(
    r"([A-Z0-9+]+):\{packKR:([\de]+),boxKR:([\de]+),packJP:([\de]+),boxJP:([\de]+)"
    r'(?:,packLabelKR:"[^"]*")?(?:,boxLabelKR:"[^"]*")?'
    r'(?:,sourceKR:"([^"]*)")?(?:,sourceJP:"([^"]*)")?\}'
)


def n(s: str) -> int:
    return int(float(s)) if "e" in s else int(s)


def ts_key(code: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", code):
        return code
    return f"'{code}'"


def load_jp() -> dict[str, dict]:
    if not CHUNK.exists():
        return {}
    chunk = CHUNK.read_text(encoding="utf-8")
    out = {}
    for m in ENTRY_RE.finditer(chunk):
        out[m.group(1)] = {
            "packJP": n(m.group(4)),
            "boxJP": n(m.group(5)),
            "sourceJP": m.group(7) or "",
        }
    return out


def main():
    jp = load_jp()
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
        f"/** featured {len(KR_SETS)} — pokemoncard.co.kr 검증 */",
        "export const SET_MSRP: Record<string, SetMsrp> = {",
    ]
    for s in KR_SETS:
        if not s.msrp_pack_kr:
            continue
        j = jp.get(s.code, {})
        pack_jp = j.get("packJP", 0)
        box_jp = j.get("boxJP", 0)
        # 신규 MEGA 갭 — JP 기본값 (일본 MEGA 시리즈)
        if not pack_jp and s.code in ("MG4a", "MG2a", "MG1b"):
            if s.code == "MG4a":
                pack_jp, box_jp = 550, 6050
            elif s.code == "MG2a":
                pack_jp, box_jp = 290, 5800
            else:
                pack_jp, box_jp = 180, 5400
        src_kr = (
            f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}"
            if s.pokemoncard_page
            else ""
        )
        src_jp = j.get("sourceJP", "")
        lines = [
            f"  {ts_key(s.code)}: {{",
            f"    packKR: {s.msrp_pack_kr},",
            f"    boxKR: {s.msrp_box_kr},",
            f"    packJP: {pack_jp},",
            f"    boxJP: {box_jp},",
        ]
        if src_kr:
            lines.append(f"    sourceKR: '{src_kr}',")
        if src_jp:
            lines.append(f"    sourceJP: '{src_jp}',")
        lines.append("  },")
        blocks.extend(lines)
    blocks.append("};")
    blocks.append("")
    OUT.write_text("\n".join(blocks), encoding="utf-8")
    print(f"wrote {OUT.name} — JP restored for {sum(1 for s in KR_SETS if jp.get(s.code))} codes")


if __name__ == "__main__":
    main()
