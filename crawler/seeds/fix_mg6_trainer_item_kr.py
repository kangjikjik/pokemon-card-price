"""MG6 트레이너·아이템 — 포켓몬코리아 공식 name_ko + image 동기화."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from lib.mg6_collectory_sync import official_for_name_jp
from lib.trainer_item_cards import card_number_int, is_mg6_trainer_or_item
from utils.db import get_supabase

APPLY = "--apply" in sys.argv


def main() -> None:
    sb = get_supabase()
    row = sb.table("card_sets").select("id").eq("set_code", "MG6").single().execute().data
    if not row:
        print("MG6 없음")
        return

    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,name_jp,rarity,image_url")
        .eq("set_id", row["id"])
        .execute()
        .data
        or []
    )

    updates: list[dict] = []
    for c in cards:
        num = card_number_int(c.get("card_number") or "")
        if num is None or not is_mg6_trainer_or_item(c.get("card_number") or ""):
            continue

        new_name, new_img = official_for_name_jp(
            (c.get("name_jp") or "").strip(), c.get("rarity") or ""
        )
        if not new_name or not new_img:
            print(f"  SKIP {num}: collectory 데이터 없음")
            continue

        old_name = (c.get("name_kr") or "").strip()
        old_img = (c.get("image_url") or "").strip()
        if old_name == new_name and old_img == new_img:
            continue

        print(f"  [{c['id']}] {c.get('card_number')} {c.get('name_jp')}")
        if old_name != new_name:
            print(f"    name: {old_name!r} → {new_name!r}")
        if old_img != new_img:
            print(f"    img:  {old_img[-55:]}")
            print(f"       → {new_img[-55:]}")

        payload: dict = {"id": c["id"]}
        if old_name != new_name:
            payload["name_kr"] = new_name
        if old_img != new_img:
            payload["image_url"] = new_img
        updates.append(payload)

    if not updates:
        print("교정 대상 없음")
        return

    if APPLY:
        for u in updates:
            cid = u.pop("id")
            sb.table("cards").update(u).eq("id", cid).execute()
        print(f"\n적용: {len(updates)}장")
    else:
        print(f"\n드라이런 {len(updates)}장 — --apply 로 반영")


if __name__ == "__main__":
    main()
