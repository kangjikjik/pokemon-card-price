"""XY3 / EBB1 — collectory 원본 전부 + DB + 공식 기대치 조사."""
from __future__ import annotations

import os
import sys
from collections import Counter

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

from collectory_map import COLLECTORY_API
from kr_sets import KR_BY_CODE
from seed_from_collectory import parse_rarity, resolve_rarity, normalize_card_number

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
client = httpx.Client(timeout=90, follow_redirects=True)


def inspect(code: str) -> None:
    meta = KR_BY_CODE[code]
    raw = client.get(f"{COLLECTORY_API}/sets/{meta.collectory_id}/cards").json().get("cards") or []
    print(f"\n{'='*60}\n{code} {meta.name_kr} collectory={meta.collectory_id}")
    print(f"collectory total={len(raw)}")
    print("raw rarity:", dict(Counter((c.get("rarity") or "?") for c in raw)))

    has_rr = any((c.get("rarity") or "").upper() == "RR" for c in raw)
    kept = []
    skipped = []
    for c in raw:
        pr = resolve_rarity(c, has_rr)
        num = c.get("card_number")
        name = c.get("name_ko") or c.get("name") or ""
        if pr:
            kept.append((num, pr, name, c.get("rarity")))
        else:
            skipped.append((num, c.get("rarity"), name))

    print(f"kept(display RR+ logic)={len(kept)} skipped={len(skipped)}")
    print("kept by rarity:", dict(Counter(k[1] for k in kept)))
    print("--- KEPT ---")
    for row in sorted(kept, key=lambda x: (x[1], x[0] or "")):
        print(f"  {row[1]:4} {row[0]} | raw={row[3]} | {row[2]}")
    print("--- SKIP sample (first 30) ---")
    for row in skipped[:30]:
        print(f"  SKIP raw={row[1]:4} {row[0]} | {row[2]}")
    if len(skipped) > 30:
        print(f"  ... +{len(skipped)-30}")

    # secrets
    secrets = []
    for c in raw:
        num = c.get("card_number") or ""
        if "/" not in num:
            continue
        left, right = num.split("/", 1)
        try:
            a = int("".join(ch for ch in left if ch.isdigit()) or 0)
            b = int("".join(ch for ch in right if ch.isdigit()) or 0)
        except ValueError:
            continue
        if a > b:
            secrets.append((num, c.get("rarity"), c.get("name_ko") or c.get("name")))
    print(f"secret numbers (a>b): {len(secrets)}")
    for s in secrets:
        print(f"  {s[0]} {s[1]} {s[2]}")

    set_id = sb.table("card_sets").select("id").eq("set_code", code).single().execute().data["id"]
    db = (
        sb.table("cards")
        .select("card_number,rarity,name_kr,image_url")
        .eq("set_id", set_id)
        .order("card_number")
        .execute()
        .data
        or []
    )
    print(f"DB cards={len(db)} dist={dict(Counter(c['rarity'] for c in db))}")
    for c in db:
        print(f"  DB {c['rarity']:4} {c['card_number']} {c['name_kr']}")


inspect("XY3")
inspect("EBB1")
