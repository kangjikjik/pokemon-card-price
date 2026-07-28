#!/usr/bin/env python3
from __future__ import annotations
import os, sys, time, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import get_supabase
from lib.collectory_jp import build_jp_card_id_map
from lib.collectory_public import preload_public_quotes_jp
from lib.jp_set_prices import prefetch_bunjang_jp, resolve_jp_card_price, try_yuyutei_fallback
import httpx

sb = get_supabase()

def find_card_by_name_fragment(fragment: str):
    q = sb.table("cards").select("id, card_number, name_kr, name_jp, set_id").ilike("name_kr", f"%{fragment}%").limit(10).execute()
    return q.data or []

def latest_db_prices(card_id: int):
    kr = sb.table("prices_kr").select("price_krw,fetched_at,source").eq("card_id", card_id).order("fetched_at", desc=True).limit(5).execute().data or []
    jp = sb.table("prices_jp").select("price_jpy,price_krw,fetched_at,source").eq("card_id", card_id).order("fetched_at", desc=True).limit(5).execute().data or []
    return kr, jp

def main():
    frag = "레시라무"
    if len(sys.argv) > 1:
        frag = sys.argv[1]
    print("Searching cards matching:", frag)
    cards = find_card_by_name_fragment(frag)
    if not cards:
        print("No cards found for fragment:", frag); return
    # pick best match: exact contains 레시라무&리자몽 or first result
    target = None
    for c in cards:
        if "레시라무&리자몽" in (c.get("name_kr") or "") or "레시라무 & 리자몽" in (c.get("name_kr") or ""):
            target = c; break
    if not target:
        target = cards[0]
    print("Target card:", target)

    card_obj = {"id": target["id"], "card_number": target.get("card_number"), "name_jp": target.get("name_jp"), "name_kr": target.get("name_kr"), "rarity": None}
    # fetch set code
    set_row = sb.table("card_sets").select("id,set_code,name_kr").eq("id", target.get("set_id")).limit(1).execute().data or []
    set_code = set_row[0].get("set_code") if set_row else ""
    set_name = set_row[0].get("name_kr") if set_row else ""
    print("Card set:", set_code, set_name)

    rate = 9.5
    col_client = httpx.Client(timeout=30)
    yuyu_client = httpx.Client(timeout=30)

    # collectory id map
    id_map = build_jp_card_id_map([card_obj], col_client)
    print("Collectory JP id:", id_map.get(card_obj["id"]))

    quote_cache = {}
    if id_map:
        quote_cache = preload_public_quotes_jp(list(id_map.values()), col_client, workers=8)
        print("Collectory quotes fetched:", len(quote_cache))

    bunjang_cache = prefetch_bunjang_jp([card_obj], target.get("name_kr") or "", "", fast=True)
    print("Bunjang cache entries:", {k: len(v) for k, v in bunjang_cache.items()})

    # resolve price
    median, low, n, source, price_jpy = resolve_jp_card_price(
        card_obj,
        collectory_id=id_map.get(card_obj["id"], ""),
        quote_cache=quote_cache,
        bunjang_cache=bunjang_cache,
        rate=rate,
        set_name_kr="",
        set_code="",
        fast=True,
    )
    print("Resolved JP price -> KRW:", median, "(JPY:", price_jpy or "N/A", "), n=", n, "source=", source)

    # try yuyutei fallback explicitly if no matches
    med2 = low2 = n2 = source2 = price_jpy2 = None
    if n == 0:
        med2, low2, n2, source2, price_jpy2 = try_yuyutei_fallback(card_obj, vers="", rate=rate, client=yuyu_client)
        print("Yuyutei fallback:", med2, n2, source2, price_jpy2)

    kr_prices, jp_prices = latest_db_prices(card_obj["id"])
    print("Latest DB KR prices:", kr_prices)
    print("Latest DB JP prices:", jp_prices)

    # Print raw bunjang items for visibility (if any)
    raw = bunjang_cache.get(card_obj["id"]) or []
    print("Sample bunjang unit prices (up to 10):", raw[:10])

    col_client.close(); yuyu_client.close()

    # Decide whether to trigger a per-set re-crawl:
    # Trigger if resolved source is listing:bunjang or n == 0 or large mismatch vs DB KR price (if exists).
    trigger = False
    if n == 0 or (isinstance(source, str) and source.startswith("listing")):
        trigger = True
    # check DB KR latest
    kr_latest = sb.table("prices_kr").select("price_krw").eq("card_id", card_obj["id"]).order("fetched_at", desc=True).limit(1).execute().data or []
    kr_val = int(kr_latest[0].get("price_krw") or 0) if kr_latest else 0
    if kr_val and median and median < kr_val * 0.6:
        trigger = True

    if trigger and set_code:
        print("Triggering per-set JP re-crawl for set:", set_code)
        script = os.path.join(os.path.dirname(__file__), "crawl_set_prices_jp.py")
        cmd = f"\"{sys.executable}\" \"{script}\" --set {set_code} --apply --fallback --thorough"
        print("Running:", cmd)
        os.system(cmd + " &")
    else:
        print("No per-set re-crawl triggered.")

if __name__ == "__main__":
    main()

