#!/usr/bin/env python3
import os
import sys
import json
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import get_supabase

def latest_prices(sb, table, card_id, limit=5):
    res = sb.table(table).select("*").eq("card_id", card_id).order("fetched_at", desc=True).limit(limit).execute()
    return res.data or []

def main():
    frag = "루카리오"
    if len(sys.argv) > 1:
        frag = sys.argv[1]
    sb = get_supabase()
    rows = sb.table("cards").select("id, name_kr, name_jp, card_number, set_id").ilike("name_kr", f"%{frag}%").limit(20).execute().data or []
    out = []
    client = httpx.Client(timeout=10)
    for r in rows:
        cid = int(r["id"])
        kr = latest_prices(sb, "prices_kr", cid)
        jp = latest_prices(sb, "prices_jp", cid)
        api = {}
        try:
            resp = client.get(f"https://pokemon-card-price.stockpick.workers.dev/api/cards/{cid}", timeout=10)
            api = resp.json()
        except Exception as e:
            api = {"error": str(e)}
        out.append({"card": r, "latest_kr": kr, "latest_jp": jp, "live_api": api})
    client.close()
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__":
    main()
