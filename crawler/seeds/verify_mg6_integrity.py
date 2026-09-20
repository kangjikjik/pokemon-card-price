"""MG6 전체 정합성 검증 — 이름·이미지·등급·거래내역."""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from lib.mg6_collectory_sync import official_image_url, official_name_ko
from lib.trainer_item_cards import card_number_int, is_mg6_trainer_or_item
from utils.db import get_supabase

FAIL = 0


def fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"  OK: {msg}")


def main() -> None:
    sb = get_supabase()
    set_id = sb.table("card_sets").select("id").eq("set_code", "MG6").single().execute().data["id"]
    cards = (
        sb.table("cards")
        .select("id,card_number,name_kr,name_jp,rarity,image_url")
        .eq("set_id", set_id)
        .execute()
        .data
        or []
    )

    print("=== 트레이너·아이템 name_kr / image ===")
    for c in cards:
        num = card_number_int(c.get("card_number") or "")
        if num is None or not is_mg6_trainer_or_item(c.get("card_number") or ""):
            continue
        r = (c.get("rarity") or "SR").upper()
        exp_name = official_name_ko(num, r)
        exp_img = official_image_url(num, r)
        if c.get("name_kr") != exp_name:
            fail(f"{num} name_kr {c.get('name_kr')!r} != {exp_name!r}")
        if c.get("image_url") != exp_img:
            fail(f"{num} image mismatch (BS2026004 CDN 금지)")
        if "/kr/BS2026004/" in (c.get("image_url") or ""):
            fail(f"{num} still uses broken BS2026004 CDN")

    print("\n=== MG6 전체 JP prices — SNK 금지 ===")
    for c in cards:
        rows = (
            sb.table("prices_jp")
            .select("source")
            .eq("card_id", c["id"])
            .execute()
            .data
            or []
        )
        snk = [r for r in rows if "snkrdunk" in (r.get("source") or "")]
        if snk:
            fail(f"{c['card_number']} id={c['id']} has {len(snk)} SNK rows")

    print("\n=== 트레이너·아이템 image — pokemonkorea 필수, jp/cn CDN 금지 ===")
    for c in cards:
        if not is_mg6_trainer_or_item(c.get("card_number") or ""):
            continue
        img = c.get("image_url") or ""
        if "pokemonkorea.co.kr" not in img:
            fail(f"{c['card_number']} image not pokemonkorea: {img[-50:]}")
        for bad in ("/jp/M5/", "/cn/M5", "BS2026004"):
            if bad in img:
                fail(f"{c['card_number']} forbidden CDN pattern {bad}")

    print("\n=== 모르페코 RR(53) vs SAR(115) ===")
    by_num = {card_number_int(c["card_number"]): c for c in cards if c.get("card_number")}
    rr = by_num.get(53)
    sar = by_num.get(115)
    if rr and sar:
        rr_rows = (
            sb.table("prices_jp")
            .select("price_krw,source")
            .eq("card_id", rr["id"])
            .like("source", "sold:%")
            .execute()
            .data
            or []
        )
        sar_rows = (
            sb.table("prices_jp")
            .select("price_krw,source")
            .eq("card_id", sar["id"])
            .like("source", "sold:%")
            .execute()
            .data
            or []
        )
        rr_prices = [r["price_krw"] for r in rr_rows if r.get("price_krw")]
        sar_prices = [r["price_krw"] for r in sar_rows if r.get("price_krw")]
        if rr_prices and max(rr_prices) > 20000:
            fail(f"RR id={rr['id']} max JP price {max(rr_prices)} looks like SAR contamination")
        if sar_prices and min(sar_prices) < 5000 and len(sar_prices) > 3:
            fail(f"SAR id={sar['id']} min JP price {min(sar_prices)} suspiciously low")
        ok(f"RR median~{sorted(rr_prices)[len(rr_prices)//2] if rr_prices else 0} SAR median~{sorted(sar_prices)[len(sar_prices)//2] if sar_prices else 0}")

    print(f"\n=== 결과: {FAIL} failures ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
