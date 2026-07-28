#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import get_supabase

sb = get_supabase()

def find_card_by_name(fragment: str):
    q = sb.table("cards").select("id, card_number, name_kr, name_jp, set_id").ilike("name_kr", f"%{fragment}%").limit(20).execute()
    return q.data or []

def latest_prices(card_id: int):
    kr = sb.table("prices_kr").select("price_krw,fetched_at,source").eq("card_id", card_id).order("fetched_at", desc=True).limit(5).execute().data or []
    jp = sb.table("prices_jp").select("price_jpy,price_krw,fetched_at,source").eq("card_id", card_id).order("fetched_at", desc=True).limit(5).execute().data or []
    return kr, jp

def site_api_card(card_id: int):
    url = f"https://pokemon-card-price.stockpick.workers.dev/api/cards/{card_id}"
    try:
        r = requests.get(url, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def report(fragment: str):
    print("=== lookup:", fragment, "===")
    cards = find_card_by_name(fragment)
    if not cards:
        print("No DB card matches for fragment:", fragment)
        return
    for c in cards:
        cid = int(c["id"])
        print(f"\n- CARD: id={cid} name_kr={c.get('name_kr')} card_number={c.get('card_number')} set_code={c.get('set_code')}")
        kr, jp = latest_prices(cid)
        print("  Latest DB KR prices (up to 5):", kr)
        print("  Latest DB JP prices (up to 5):", jp)
        api = site_api_card(cid)
        print("  Live API /api/cards/{id} ->", ("error:" + api["error"]) if api.get("error") else f"priceKR={api.get('data',{}).get('priceKR')} priceJP={api.get('data',{}).get('priceJP')}")

if __name__ == "__main__":
    fragments = sys.argv[1:] or ["리자몽", "뮤"]
    for f in fragments:
        report(f)

