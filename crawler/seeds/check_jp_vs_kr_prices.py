#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import sys
from time import sleep

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import get_supabase

sb = get_supabase()

def latest_price(card_id: int, table: str):
    try:
        res = sb.table(table).select("price_krw,fetched_at").eq("card_id", card_id).order("fetched_at", {"ascending": False}).limit(1).execute()
        return (res.data or [None])[0]
    except Exception as e:
        print("DB error", e)
        return None

def run_check(limit_ratio: float = 0.95):
    cards = sb.table("cards").select("id, name_kr, card_sets ( set_code )").execute().data or []
    anomalies = []
    for c in cards:
        cid = c.get("id")
        if not cid:
            continue
        kr = latest_price(cid, "prices_kr")
        jp = latest_price(cid, "prices_jp")
        if not kr or not jp:
            continue
        krp = int(kr.get("price_krw") or 0)
        jpp = int(jp.get("price_krw") or 0)
        if krp > 0 and jpp < krp * limit_ratio:
            sets = [s.get("set_code") for s in (c.get("card_sets") or []) if s.get("set_code")]
            anomalies.append({"card_id": cid, "name_kr": c.get("name_kr"), "kr": krp, "jp": jpp, "sets": list(dict.fromkeys(sets))})
    return anomalies

def trigger_recrawl(sets: list[str]):
    script = os.path.join(os.path.dirname(__file__), "crawl_set_prices_jp.py")
    if not os.path.exists(script):
        print("crawl_set_prices_jp.py missing; cannot trigger re-crawl")
        return
    for sc in sets:
        cmd = f"\"{sys.executable}\" \"{script}\" --set {sc} --apply"
        print("Starting:", cmd)
        if os.name == "nt":
            os.system(f"start /B {cmd}")
        else:
            os.system(cmd + " &")
        sleep(0.2)

def main():
    fix = "--fix" in sys.argv
    ratio_arg = "--ratio" in sys.argv
    if ratio_arg:
        try:
            raw = get_arg("--ratio", "0.95")
            limit_ratio = float(raw)
        except Exception:
            limit_ratio = 0.95
    else:
        limit_ratio = 0.95
    print("Running JP vs KR price check...")
    anomalies = run_check(limit_ratio=limit_ratio)
    if not anomalies:
        print("No anomalies.")
        return
    out = os.path.join(os.path.dirname(__file__), "_reports", "jp_vs_kr_anomalies.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(anomalies, f, ensure_ascii=False, indent=2)
    print(f"Found {len(anomalies)} anomalies. Report saved to {out}")
    for a in anomalies[:50]:
        print(f"- {a['card_id']} {a['name_kr']!r} KR:₩{a['kr']:,} JP:₩{a['jp']:,} sets={a['sets']}")
    if fix:
        sets = []
        for a in anomalies:
            for s in a["sets"]:
                if s and s not in sets:
                    sets.append(s)
        if sets:
            trigger_recrawl(sets)

if __name__ == "__main__":
    main()

