"""ACE 전수 덤프 + collectory ACE 라벨 대조"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
OUT = Path(__file__).parent / "_audit_out"
OUT.mkdir(exist_ok=True)

ace = (
    sb.table("cards")
    .select("id,name_kr,name_jp,card_number,rarity,image_url,set_id")
    .eq("rarity", "ACE")
    .execute()
    .data
    or []
)
set_ids = list({r["set_id"] for r in ace})
sets = (
    sb.table("card_sets").select("id,set_code,name_kr").in_("id", set_ids).execute().data
    or []
)
by_id = {s["id"]: s for s in sets}
print(f"ACE total: {len(ace)}")
print("by set:", dict(Counter(by_id.get(r["set_id"], {}).get("set_code", "?") for r in ace)))

lines = []
for r in sorted(ace, key=lambda x: (by_id.get(x["set_id"], {}).get("set_code", ""), x.get("card_number") or "")):
    s = by_id.get(r["set_id"], {})
    line = f"{s.get('set_code','?'):6}|{(r.get('card_number') or ''):12}|{r.get('name_kr') or ''}|{r.get('name_jp') or ''}|{r['id']}"
    print(f"  {line}")
    lines.append({
        "id": r["id"],
        "set_code": s.get("set_code"),
        "card_number": r.get("card_number") or "",
        "name_kr": r.get("name_kr") or "",
        "name_jp": r.get("name_jp") or "",
        "image_url": r.get("image_url") or "",
    })

(OUT / "ace_db.json").write_text(json.dumps(lines, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nwrote {OUT / 'ace_db.json'}")

# collectory: what rarity labels exist as ACE
print("\n=== collectory ACE labels ===")
from collectory_map import COLLECTORY_API, COLLECTORY_SETS
from seed_from_collectory import parse_rarity

client = httpx.Client(timeout=60, headers={"User-Agent": "Mozilla/5.0"})
# fetch all sets meta
sets_api = client.get(f"{COLLECTORY_API}/sets").json().get("sets") or []
by_col = {s["id"]: s for s in sets_api}

# map our featured codes that have ACE in DB
ace_codes = sorted({x["set_code"] for x in lines if x["set_code"]})
col_ace = []
for code in ace_codes:
    cfg = COLLECTORY_SETS.get(code)
    if not cfg:
        # try kr_sets collectory_id
        from kr_sets import KR_BY_CODE
        ks = KR_BY_CODE.get(code)
        cid = ks.collectory_id if ks else ""
    else:
        cid = cfg["id"]
    if not cid:
        print(f"  {code}: no collectory id")
        continue
    cards = client.get(f"{COLLECTORY_API}/sets/{cid}/cards").json().get("cards") or []
    ace_cards = []
    for c in cards:
        r = (c.get("rarity") or "").strip()
        num = c.get("card_number") or ""
        parsed = parse_rarity(c)
        if r.upper() == "ACE" or (parsed == "ACE") or "ACE" in num.upper():
            ace_cards.append({
                "num": num,
                "rarity": r,
                "parsed": parsed,
                "name": c.get("name_ko") or c.get("name_kr") or c.get("name_ja") or "",
            })
    print(f"  {code}: collectory ACE-ish={len(ace_cards)} / cards={len(cards)}")
    for a in ace_cards:
        print(f"    {a['num']:16} rar={a['rarity']:6} parsed={a['parsed']} {a['name']}")
        col_ace.append({"set_code": code, **a})

(OUT / "ace_collectory.json").write_text(json.dumps(col_ace, ensure_ascii=False, indent=2), encoding="utf-8")
