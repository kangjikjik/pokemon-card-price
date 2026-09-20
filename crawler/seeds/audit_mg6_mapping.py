"""MG6 카드번호·이름·이미지·거래내역 정합성 감사."""
from __future__ import annotations

import os
import re
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from utils.db import get_supabase

COLLECTORY_ID = "611cf371-dafe-42fc-b86d-895aa433e10d"
BS = "BS2026004"


def num_int(card_number: str) -> int:
    return int(card_number.split("/")[0])


def main() -> None:
    sb = get_supabase()
    set_row = sb.table("card_sets").select("id").eq("set_code", "MG6").single().execute().data
    db_cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,name_jp,rarity,image_url")
        .eq("set_id", set_row["id"])
        .execute()
        .data
        or []
    )
    db_by_num = {num_int(c["card_number"]): c for c in db_cards if c.get("card_number")}

    col_cards = httpx.get(
        f"https://collectory.cc/api/sets/{COLLECTORY_ID}/cards", timeout=60
    ).json().get("cards", [])
    col_by_num = {num_int(c["card_number"]): c for c in col_cards if c.get("card_number")}

    print("=== Collectory name vs DB name_kr (102-117) ===")
    for n in range(102, 118):
        col = col_by_num.get(n, {})
        db = db_by_num.get(n, {})
        col_name = (col.get("name") or "").strip()
        db_name = (db.get("name_kr") or "").strip()
        ok = "OK" if col_name == db_name else "MISMATCH"
        print(f"  {n:03d} col={col_name!r} db={db_name!r} [{ok}]")

    print("\n=== DB image URL suffix (102-117) ===")
    for n in range(102, 118):
        db = db_by_num.get(n, {})
        img = db.get("image_url") or ""
        expected = f"{n}_081{db.get('rarity','SR').upper()}"
        match = expected in img
        print(f"  {n:03d} {db.get('name_kr',''):16} img_has_{expected}={match} | {img[-60:]}")

    print("\n=== Morpeko RR(53) vs SAR(115) prices_jp sources ===")
    for label, num in [("RR", 53), ("SAR", 115)]:
        c = db_by_num.get(num)
        if not c:
            continue
        rows = (
            sb.table("prices_jp")
            .select("source,price_krw")
            .eq("card_id", c["id"])
            .execute()
            .data
            or []
        )
        sold = [r for r in rows if (r.get("source") or "").startswith("sold:")]
        print(f"  {num}/081 {c['rarity']} id={c['id']} name={c['name_kr']} sold_rows={len(sold)}")
        for r in sold[:3]:
            print(f"    {r['price_krw']} {r['source'][:60]}")

    # duplicate card_number check
    print("\n=== Duplicate card_numbers in DB ===")
    from collections import Counter
    nums = [c["card_number"] for c in db_cards]
    for num, cnt in Counter(nums).items():
        if cnt > 1:
            ids = [c["id"] for c in db_cards if c["card_number"] == num]
            print(f"  DUP {num} x{cnt} ids={ids}")


if __name__ == "__main__":
    main()
