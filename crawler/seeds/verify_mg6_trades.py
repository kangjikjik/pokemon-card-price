"""MG6 카드별 거래내역 DB·로컬 API 검증."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from utils.db import get_supabase

SET_CODE = "MG6"
API_BASE = os.environ.get("TRADES_API_BASE", "https://pokemon-card-price.stockpick.workers.dev")

PID_KR = re.compile(r"^sold:bunjang:\d+")
PID_JP = re.compile(r"^sold:(bunjang:\d+|snkrdunk:\d+)")


def count_db_trades(card_id: int, table: str) -> tuple[int, int]:
    rows = (
        sb.table(table)
        .select("source")
        .eq("card_id", card_id)
        .like("source", "sold:%")
        .execute()
        .data
        or []
    )
    url_rows = sum(1 for r in rows if PID_KR.match(r["source"]) or PID_JP.match(r["source"]))
    return len(rows), url_rows


def fetch_api_trades(card_id: int) -> dict:
    url = f"{API_BASE}/api/cards/{card_id}/trades"
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.loads(res.read().decode())


sb = get_supabase()
set_row = sb.table("card_sets").select("id").eq("set_code", SET_CODE).execute().data[0]
cards = (
    sb.table("cards")
    .select("id,name_kr,rarity,card_number")
    .eq("set_id", set_row["id"])
    .order("card_number")
    .execute()
    .data
    or []
)

print(f"=== {SET_CODE} 거래내역 검증 ({len(cards)}장) API={API_BASE} ===\n")
print(f"{'#':>4} {'id':>5} {'rarity':>4} {'KRdb':>5} {'KRurl':>6} {'KRapi':>6} {'JPdb':>5} {'JPurl':>6} {'JPapi':>6}  name")
print("-" * 90)

kr_empty = jp_empty = 0
for c in cards:
    cid = c["id"]
    kr_db, kr_url = count_db_trades(cid, "prices_kr")
    jp_db, jp_url = count_db_trades(cid, "prices_jp")
    try:
        api = fetch_api_trades(cid)
        kr_api = len(api.get("kr") or [])
        jp_api = len(api.get("jp") or [])
    except Exception as e:
        kr_api = jp_api = -1
        print(f"  API error card {cid}: {e}")
    if kr_api == 0:
        kr_empty += 1
    if jp_api == 0:
        jp_empty += 1
    print(
        f"{c['card_number']:>4} {cid:5} {c['rarity']:>4} "
        f"{kr_db:5} {kr_url:6} {kr_api:6} {jp_db:5} {jp_url:6} {jp_api:6}  "
        f"{(c['name_kr'] or '')[:20]}"
    )

print("-" * 90)
print(f"KR 거래없음(API): {kr_empty}/{len(cards)}  JP 거래없음(API): {jp_empty}/{len(cards)}")
