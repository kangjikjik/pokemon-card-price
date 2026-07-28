#!/usr/bin/env python3
"""D급·하자 등급 SNKRDUNK 체결이 유일 raw로 잡히는 카드 샘플링."""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from lib.collectory_jp import build_jp_card_id_map
from lib.collectory_public import TR_ROW_RE, _parse_transaction_row_jp, _row_text
from lib.price_resolve import is_graded_grade
from utils.db import get_supabase

DAMAGE_GRADES = ("D급", "D", "E급", "E", "F급", "F", "하자", "키즈", "KIDS")


def grade_from_row(row_html: str) -> str:
    parts = _row_text(row_html)
    return parts[2] if len(parts) > 2 else ""


def analyze_collectory_html(html: str) -> dict:
    rows = TR_ROW_RE.findall(html)
    parsed = [_parse_transaction_row_jp(r) for r in rows]
    parsed = [q for q in parsed if q]
    sold = [q for q in parsed if q.tier == "sold"]
    damage_sold = []
    psa_filtered = 0
    for row_html in rows:
        if "SNKRDUNK" not in row_html:
            continue
        g = grade_from_row(row_html)
        if is_graded_grade(g):
            psa_filtered += 1
            continue
        if any(d in (g or "") for d in DAMAGE_GRADES):
            q = _parse_transaction_row_jp(row_html)
            if q and q.tier == "sold":
                damage_sold.append({"grade": g, "price_krw": q.price_krw, "title": q.title[:80]})
    return {
        "parsed_sold_count": len(sold),
        "parsed_sold_prices": [q.price_krw for q in sold],
        "damage_sold": damage_sold,
        "psa_snkrdunk_rows_filtered": psa_filtered,
        "only_damage_sold": len(sold) == len(damage_sold) and len(damage_sold) > 0,
    }


def main() -> None:
    sb = get_supabase()
    # latest JP from snkrdunk, ordered by recent fetch
    jp_rows = (
        sb.table("prices_jp")
        .select("card_id,price_krw,source,fetched_at")
        .ilike("source", "%snkrdunk%")
        .order("fetched_at", desc=True)
        .limit(5000)
        .execute()
        .data
        or []
    )
    latest: dict[int, dict] = {}
    for r in jp_rows:
        cid = int(r["card_id"])
        if cid not in latest:
            latest[cid] = r

    cards = (
        sb.table("cards")
        .select("id,name_kr,rarity,card_number")
        .in_("id", list(latest.keys())[:300])
        .execute()
        .data
        or []
    )
    card_map = {int(c["id"]): c for c in cards}
    sample_ids = list(latest.keys())[:120]

    client = httpx.Client(timeout=45, headers={"User-Agent": "Mozilla/5.0"})
    id_map = build_jp_card_id_map(
        [
            {
                "id": cid,
                "card_number": card_map.get(cid, {}).get("card_number"),
                "name_jp": card_map.get(cid, {}).get("name_kr"),
                "name_kr": card_map.get(cid, {}).get("name_kr"),
            }
            for cid in sample_ids
            if cid in card_map
        ],
        client,
    )

    only_damage = []
    no_sold = []
    ok = []
    for cid, col_id in id_map.items():
        if not col_id:
            continue
        res = client.get(f"https://collectory.cc/cards/{col_id}")
        if res.status_code != 200:
            continue
        info = analyze_collectory_html(res.text)
        row = {
            "card_id": cid,
            "name_kr": card_map.get(cid, {}).get("name_kr"),
            "rarity": card_map.get(cid, {}).get("rarity"),
            "db_jp": int(latest[cid].get("price_krw") or 0),
            **info,
        }
        if info["only_damage_sold"]:
            only_damage.append(row)
        elif info["parsed_sold_count"] == 0:
            no_sold.append(row)
        else:
            ok.append(row)

    client.close()
    out = {
        "sample_size": len(id_map),
        "only_damage_sold_count": len(only_damage),
        "no_parsed_sold_count": len(no_sold),
        "ok_count": len(ok),
        "only_damage_examples": only_damage[:30],
        "no_sold_examples": no_sold[:15],
    }
    path = os.path.join(os.path.dirname(__file__), "_reports", "snkrdunk_dgrade_sample.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)

    print("sample_size", out["sample_size"])
    print("only_damage_sold (D급 등만 raw로 잡힘)", out["only_damage_sold_count"])
    print("no_parsed_sold at all", out["no_parsed_sold_count"])
    print("has normal sold", out["ok_count"])
    print("report", path)
    for r in only_damage[:10]:
        print(f"- id={r['card_id']} {r.get('name_kr')} db_jp={r['db_jp']:,} damage={r['damage_sold']}")


if __name__ == "__main__":
    main()
