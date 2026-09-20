"""MEGA 6팩 트레이너·아이템 — 등급별 한국판 이미지·공식명 검증."""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from kr_sets import KR_BY_CODE
from lib.collectory_kr_sync import official_kr_for_card
from lib.trainer_item_cards import is_mg6_trainer_or_item, is_trainer_or_item_card
from utils.db import get_supabase

SETS = [
    ("MG4", KR_BY_CODE["MG4"].name_kr),
    ("MG4a", KR_BY_CODE["MG4a"].name_kr),
    ("MG5", KR_BY_CODE["MG5"].name_kr),
    ("MG5a", KR_BY_CODE["MG5a"].name_kr),
    ("MG6", KR_BY_CODE["MG6"].name_kr),
    ("MG7", KR_BY_CODE["MG7"].name_kr),
]


def _is_kr_img(url: str) -> bool:
    return "pokemonkorea" in (url or "")


def _wrong_u_on_sr(rarity: str, url: str) -> bool:
    r = (rarity or "").upper()
    if r not in ("SR", "SAR", "HR", "UR") or not _is_kr_img(url):
        return False
    m = re.search(r"M[45a6]?_(\d{3})\.png", url)
    if not m:
        return False
    n = int(m.group(1))
    return n < 90  # U/C 구간 한국판이 SR에 붙은 경우


def main() -> None:
    sb = get_supabase()
    total = 0
    ok = 0
    issues: list[str] = []

    for code, label in SETS:
        row = sb.table("card_sets").select("id").eq("set_code", code).execute().data
        if not row:
            issues.append(f"{label}: 세트 없음")
            continue
        sid = row[0]["id"]
        cards = (
            sb.table("cards")
            .select("card_number,name_kr,name_jp,rarity,image_url")
            .eq("set_id", sid)
            .execute()
            .data
            or []
        )

        for c in cards:
            name_jp = (c.get("name_jp") or "").strip()
            cn = c.get("card_number") or ""
            if code == "MG6":
                if not is_mg6_trainer_or_item(cn):
                    continue
            elif not is_trainer_or_item_card(code, cn, name_jp):
                continue

            total += 1
            rarity = (c.get("rarity") or "").strip()
            img = (c.get("image_url") or "").split("?")[0]
            exp_name, exp_img = official_kr_for_card(code, name_jp, cn, rarity)

            problems: list[str] = []
            if exp_name and (c.get("name_kr") or "").strip() != exp_name.strip():
                problems.append(f"이름 {(c.get('name_kr') or '')!r} ≠ 공식 {exp_name!r}")
            if _wrong_u_on_sr(rarity, img):
                problems.append("SR/SAR에 U 한국판 이미지 오적용")
            elif (
                (rarity or "").upper() in ("U", "C")
                and exp_img
                and _is_kr_img(exp_img)
                and not _is_kr_img(img)
            ):
                problems.append("U/C 한국판 이미지 미적용")
            elif (rarity or "").upper() in ("U", "C") and exp_img and img != exp_img.split("?")[0]:
                problems.append("U/C 등급 한국판 이미지 불일치")

            if problems:
                issues.append(f"{label} {cn} {rarity} {c.get('name_kr')}: " + "; ".join(problems))
            else:
                ok += 1

    print(f"검증: {ok}/{total}장 OK")
    if issues:
        print(f"\n문제 {len(issues)}건:")
        for line in issues[:40]:
            print(" ", line)
        if len(issues) > 40:
            print(f"  … 외 {len(issues) - 40}건")
        sys.exit(1)
    print("전체 통과")


if __name__ == "__main__":
    main()
