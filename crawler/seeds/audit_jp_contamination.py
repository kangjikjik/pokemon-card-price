#!/usr/bin/env python3
"""JP 시세 오염 규모 추정 — SNKRDUNK/D급·급락·KR 대비 이상."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import get_supabase


def fetch_all(table: str, select: str) -> list[dict]:
    sb = get_supabase()
    rows: list[dict] = []
    offset = 0
    batch = 1000
    while True:
        res = (
            sb.table(table)
            .select(select)
            .order("id", desc=False)
            .range(offset, offset + batch - 1)
            .execute()
        )
        chunk = res.data or []
        if not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < batch:
            break
        offset += batch
    return rows


def latest_by_card(rows: list[dict], card_key: str = "card_id") -> dict[int, dict]:
    by: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        cid = r.get(card_key)
        if cid:
            by[int(cid)].append(r)
    out: dict[int, dict] = {}
    for cid, items in by.items():
        items.sort(key=lambda x: x.get("fetched_at") or "", reverse=True)
        out[cid] = items[0]
    return out


def main() -> None:
    sb = get_supabase()
    cards = sb.table("cards").select("id, name_kr, rarity, card_number").execute().data or []
    card_map = {int(c["id"]): c for c in cards if c.get("id")}

    jp_rows = fetch_all("prices_jp", "id,card_id,price_jpy,price_krw,source,fetched_at")
    kr_rows = fetch_all("prices_kr", "id,card_id,price_krw,source,fetched_at")

    latest_jp = latest_by_card(jp_rows)
    latest_kr = latest_by_card(kr_rows)
    history_jp: dict[int, list[dict]] = defaultdict(list)
    for r in jp_rows:
        history_jp[int(r["card_id"])].append(r)
    for cid in history_jp:
        history_jp[cid].sort(key=lambda x: x.get("fetched_at") or "", reverse=True)

    total_cards = len(card_map)
    with_jp = len(latest_jp)
    with_kr = len(latest_kr)

    src_counter = Counter()
    snkrdunk_latest: list[dict] = []
    listing_bunjang_latest: list[dict] = []
    suspicious: list[dict] = []

    for cid, jp in latest_jp.items():
        src = str(jp.get("source") or "")
        src_counter[src] += 1
        card = card_map.get(cid, {})
        jpp = int(jp.get("price_krw") or 0)
        krp = int((latest_kr.get(cid) or {}).get("price_krw") or 0)

        hist = history_jp.get(cid, [])
        prev_yuyu = next(
            (
                int(h.get("price_krw") or 0)
                for h in hist[1:]
                if "yuyutei" in str(h.get("source") or "").lower()
            ),
            0,
        )
        prev_any = int(hist[1].get("price_krw") or 0) if len(hist) > 1 else 0

        row = {
            "card_id": cid,
            "name_kr": card.get("name_kr"),
            "rarity": card.get("rarity"),
            "card_number": card.get("card_number"),
            "jp": jpp,
            "kr": krp,
            "source": src,
            "fetched_at": jp.get("fetched_at"),
            "prev_yuyu": prev_yuyu,
            "prev_any": prev_any,
        }

        if "snkrdunk" in src.lower():
            snkrdunk_latest.append(row)
        if src.startswith("listing:bunjang"):
            listing_bunjang_latest.append(row)

        reasons: list[str] = []
        if "snkrdunk" in src.lower():
            reasons.append("snkrdunk_latest")
        if src.startswith("listing:bunjang"):
            reasons.append("bunjang_listing_latest")
        if krp >= 30000 and jpp > 0 and jpp < krp * 0.5:
            reasons.append("jp_lt_half_kr")
        if prev_yuyu >= 10000 and jpp > 0 and jpp < prev_yuyu * 0.4:
            reasons.append("jp_crash_vs_yuyutei")
        if prev_any >= 10000 and jpp > 0 and jpp < prev_any * 0.35:
            reasons.append("jp_crash_vs_prev")

        if reasons:
            row["reasons"] = reasons
            suspicious.append(row)

    # KR 대비 JP 낮음 (ratio 1.0 = JP < KR)
    jp_lt_kr = [
        r
        for r in suspicious
        if r.get("kr", 0) > 0 and r.get("jp", 0) > 0 and r["jp"] < r["kr"]
    ]

    snkrdunk_suspicious = [r for r in suspicious if "snkrdunk_latest" in r.get("reasons", [])]
    bunjang_suspicious = [r for r in suspicious if "bunjang_listing_latest" in r.get("reasons", [])]

    report = {
        "summary": {
            "total_cards": total_cards,
            "cards_with_latest_jp": with_jp,
            "cards_with_latest_kr": with_kr,
            "latest_jp_source_breakdown": dict(src_counter.most_common(20)),
            "latest_snkrdunk_count": len(snkrdunk_latest),
            "latest_listing_bunjang_count": len(listing_bunjang_latest),
            "suspicious_total": len(suspicious),
            "suspicious_snkrdunk_latest": len(snkrdunk_suspicious),
            "suspicious_bunjang_listing_latest": len(bunjang_suspicious),
            "jp_lower_than_kr_count": len(jp_lt_kr),
        },
        "top_suspicious": sorted(
            suspicious,
            key=lambda x: (
                -len(x.get("reasons", [])),
                (x.get("prev_yuyu") or x.get("prev_any") or 0) - (x.get("jp") or 0),
            ),
            reverse=True,
        )[:80],
    }

    out_dir = os.path.join(os.path.dirname(__file__), "_reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "jp_price_contamination_audit.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    s = report["summary"]
    print("=== JP price contamination audit ===")
    print(f"total cards: {s['total_cards']}")
    print(f"cards with latest JP: {s['cards_with_latest_jp']}")
    print(f"latest JP source top: {s['latest_jp_source_breakdown']}")
    print(f"latest sold:snkrdunk: {s['latest_snkrdunk_count']}")
    print(f"latest listing:bunjang: {s['latest_listing_bunjang_count']}")
    print(f"suspicious total: {s['suspicious_total']}")
    print(f"  - snkrdunk latest flagged: {s['suspicious_snkrdunk_latest']}")
    print(f"  - bunjang listing latest flagged: {s['suspicious_bunjang_listing_latest']}")
    print(f"JP < KR (both exist): {s['jp_lower_than_kr_count']}")
    print(f"report: {out_path}")
    print("\nTop 15 suspicious:")
    for r in report["top_suspicious"][:15]:
        print(
            f"- id={r['card_id']} {r.get('name_kr')} "
            f"JP={r['jp']:,} KR={r.get('kr',0):,} src={r['source']} "
            f"prev_yuyu={r.get('prev_yuyu',0):,} reasons={r.get('reasons')}"
        )


if __name__ == "__main__":
    main()
