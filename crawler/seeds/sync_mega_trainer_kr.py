"""MEGA 6팩 트레이너·아이템 — Collectory KR 공식 name_ko + 등급별 pokemonkorea 이미지."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from lib.collectory_kr_sync import official_kr_for_card
from lib.trainer_item_cards import is_mg6_trainer_or_item, is_trainer_or_item_card
from utils.db import get_supabase

# MG7 — fix_mg7_trainer_kr.py (경기장 L/R 별도)
SETS = ["MG4", "MG4a", "MG5", "MG5a", "MG6"]
APPLY = "--apply" in sys.argv


def main() -> None:
    sb = get_supabase()
    total = 0
    for code in SETS:
        row = sb.table("card_sets").select("id").eq("set_code", code).execute().data
        if not row:
            print(f"[{code}] 세트 없음")
            continue
        set_id = row[0]["id"]
        cards = (
            sb.table("cards")
            .select("id,card_number,name_kr,name_jp,rarity,image_url")
            .eq("set_id", set_id)
            .execute()
            .data
            or []
        )
        print(f"\n[{code}] DB {len(cards)}장")
        n = 0
        for c in cards:
            name_jp = (c.get("name_jp") or "").strip()
            cn = c.get("card_number") or ""
            if code == "MG6":
                if not is_mg6_trainer_or_item(cn):
                    continue
            elif not is_trainer_or_item_card(code, cn, name_jp):
                continue

            new_name, new_img = official_kr_for_card(
                code, name_jp, cn, c.get("rarity") or ""
            )
            if not new_name:
                print(f"  SKIP {cn} {name_jp} — collectory 매칭 없음")
                continue

            old_name = (c.get("name_kr") or "").strip()
            old_img = (c.get("image_url") or "").split("?")[0]
            new_img_key = (new_img or "").split("?")[0]

            payload: dict = {}
            if old_name != new_name:
                payload["name_kr"] = new_name
            if new_img_key and old_img != new_img_key:
                payload["image_url"] = new_img_key

            if not payload:
                continue

            print(f"  [{cn}] {c.get('rarity')} {name_jp}")
            if "name_kr" in payload:
                print(f"    name: {old_name!r} → {new_name!r}")
            if "image_url" in payload:
                print(f"    img → pokemonkorea")
            if APPLY:
                sb.table("cards").update(payload).eq("id", c["id"]).execute()
            n += 1
        print(f"  교정: {n}장")
        total += n
    print(f"\n{'적용' if APPLY else '드라이런'} 합계: {total}장")


if __name__ == "__main__":
    main()
