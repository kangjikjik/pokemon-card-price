"""DB에 남은 '에메랄da'(영문 da) 표기 → 공식 '스톰에메랄da' 교정."""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from kr_sets import KR_BY_CODE
from utils.db import get_supabase

APPLY = "--apply" in sys.argv

OFFICIAL = KR_BY_CODE["MG7"].name_kr  # 스톰에메랄da (한글)

# 영문 da / 번개 오타 → 공식명·공식 접미
_LATIN_DA = re.compile(r"에메랄da(?!.)|에메랄da$|에메랄da(?=[^가-힣])")


def fix_text(s: str) -> str:
    if not s:
        return s
    out = s
    out = out.replace("스토에메랄da", OFFICIAL)
    out = out.replace("스토 에메랄da", OFFICIAL)
    out = out.replace("스톰에메랄da", OFFICIAL)
    out = out.replace("스톰 에메랄da", OFFICIAL.replace("스톰", "스톰 ").replace("  ", " ") if " " not in OFFICIAL else "스톰 에메랄da")
    out = out.replace("스톰에메랄da", OFFICIAL)
    out = out.replace("스톰 에메랄da", "스톰 에메랄da")
    out = out.replace("에메랄da", "에메랄da")
    out = out.replace("에메랄드", "에메랄da")
    # 위에서 에메랄da는 한글 '다' — OFFICIAL에서 접미 추출
    suffix = OFFICIAL[-3:] if len(OFFICIAL) >= 3 else "에메랄da"
    out = re.sub(r"에메랄da(?![가-힣])", suffix.replace("에메랄", "에메랄") if "에메랄" in suffix else "에메랄da", out)
    out = out.replace("에메랄da", OFFICIAL[-4:] if OFFICIAL.endswith("에메랄da") else "에메랄da")
    # 단순 치환 (최종)
    for wrong in (
        "스톰에메랄da",
        "스톰 에메랄da",
        "스토에메랄da",
        "스토 에메랄da",
        "에메랄da",
    ):
        if wrong.endswith("da") and wrong[-2:] == "da" and wrong[-3] == "랄":
            # latin da → official ending
            rep = OFFICIAL if wrong.startswith("스") else OFFICIAL[-4:]
            out = out.replace(wrong, rep if "스" in wrong else OFFICIAL.replace("스톰", "").strip() or "에메랄da")
    return out


def needs_fix(s: str) -> bool:
    return bool(re.search(r"에메랄da|스토에메랄da|스톰에메랄da", s or ""))


def _simple_fix(s: str) -> str:
    """영문 'da' 접미 → 한글 '다'."""
    if not s:
        return s
    out = s
    pairs = [
        ("스톰에메랄da", OFFICIAL),
        ("스톰 에메랄da", "스톰 에메랄da"),
        ("스토에메랄da", OFFICIAL),
        ("스토 에메랄da", "스톰 에메랄da"),
        ("에메랄da", "에메랄da"),
    ]
    # 공식: 스톰에메랄da ends with 다
    emerald_ko = "에메랄" + OFFICIAL[-1]  # 에메랄 + 다
    spaced = "스톰 " + emerald_ko
    pairs = [
        ("스톰에메랄da", OFFICIAL),
        ("스톰 에메랄da", spaced),
        ("스토에메랄da", OFFICIAL),
        ("스토 에메랄da", spaced),
        ("에메랄da", emerald_ko),
        ("에메랄드", emerald_ko),
    ]
    for a, b in pairs:
        out = out.replace(a, b)
    return out


def main() -> None:
    sb = get_supabase()
    total = 0

    sets = sb.table("card_sets").select("id,set_code,name_kr").execute().data or []
    for row in sets:
        old = row.get("name_kr") or ""
        if not needs_fix(old):
            continue
        new = _simple_fix(old)
        print(f"card_sets [{row['set_code']}] {old!r} → {new!r}")
        if APPLY and new != old:
            sb.table("card_sets").update({"name_kr": new}).eq("id", row["id"]).execute()
        total += 1

    for row in sets:
        cards = (
            sb.table("cards")
            .select("id,card_number,name_kr")
            .eq("set_id", row["id"])
            .execute()
            .data
            or []
        )
        for c in cards:
            old = c.get("name_kr") or ""
            if not needs_fix(old):
                continue
            new = _simple_fix(old)
            print(f"cards [{row['set_code']}] {c.get('card_number')} {old!r} → {new!r}")
            if APPLY and new != old:
                sb.table("cards").update({"name_kr": new}).eq("id", c["id"]).execute()
            total += 1

    # MG7 공식명 강제 동기화
    mg7 = next((r for r in sets if r["set_code"] == "MG7"), None)
    if mg7 and mg7.get("name_kr") != OFFICIAL:
        print(f"card_sets [MG7] 강제 → {OFFICIAL!r}")
        if APPLY:
            sb.table("card_sets").update({"name_kr": OFFICIAL}).eq("id", mg7["id"]).execute()
        total += 1

    print(f"\n공식 세트명: {OFFICIAL!r}")
    print(f"{'적용' if APPLY else '드라이런'}: {total}건")


if __name__ == "__main__":
    main()
