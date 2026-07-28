#!/usr/bin/env python3
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from utils.db import get_supabase


def fetch_table(name: str, select: str) -> list[dict]:
    sb = get_supabase()
    rows: list[dict] = []
    off = 0
    while True:
        chunk = (
            sb.table(name)
            .select(select)
            .order("id")
            .range(off, off + 999)
            .execute()
            .data
            or []
        )
        if not chunk:
            break
        rows.extend(chunk)
        off += 1000
        if len(chunk) < 1000:
            break
    return rows


def main() -> None:
    sb = get_supabase()
    cards = {
        int(c["id"]): c
        for c in (sb.table("cards").select("id,name_kr,rarity").execute().data or [])
    }
    jp_rows = fetch_table("prices_jp", "card_id,price_krw,source,fetched_at")
    kr_rows = fetch_table("prices_kr", "card_id,price_krw,fetched_at")

    jp_hist: dict[int, list[dict]] = defaultdict(list)
    for r in jp_rows:
        jp_hist[int(r["card_id"])].append(r)
    for cid in jp_hist:
        jp_hist[cid].sort(key=lambda x: x.get("fetched_at") or "", reverse=True)

    kr_latest: dict[int, int] = {}
    kr_group: dict[int, list[dict]] = defaultdict(list)
    for r in kr_rows:
        kr_group[int(r["card_id"])].append(r)
    for cid, items in kr_group.items():
        items.sort(key=lambda x: x.get("fetched_at") or "", reverse=True)
        kr_latest[cid] = int(items[0].get("price_krw") or 0)

    crash_vs_yuyu = []
    jp_lt_half_kr = []
    snk_low_high_rarity = []
    snk_latest = 0

    for cid, items in jp_hist.items():
        if not items:
            continue
        latest = items[0]
        j = int(latest.get("price_krw") or 0)
        src = str(latest.get("source") or "")
        if "snkrdunk" in src.lower():
            snk_latest += 1
        prev_yuyu = next(
            (
                int(h.get("price_krw") or 0)
                for h in items[1:]
                if "yuyutei" in str(h.get("source") or "").lower()
            ),
            0,
        )
        card = cards.get(cid, {})
        rarity = (card.get("rarity") or "").upper()
        k = kr_latest.get(cid, 0)

        if prev_yuyu >= 10000 and j > 0 and j < prev_yuyu * 0.4:
            crash_vs_yuyu.append(
                {
                    "card_id": cid,
                    "name_kr": card.get("name_kr"),
                    "rarity": rarity,
                    "jp": j,
                    "prev_yuyu": prev_yuyu,
                    "source": src,
                }
            )
        if k >= 20000 and j > 0 and j < k * 0.5:
            jp_lt_half_kr.append(
                {
                    "card_id": cid,
                    "name_kr": card.get("name_kr"),
                    "rarity": rarity,
                    "jp": j,
                    "kr": k,
                    "source": src,
                }
            )
        if (
            "snkrdunk" in src.lower()
            and j > 0
            and j <= 50000
            and rarity in {"UR", "SAR", "MUR", "MA", "HR", "ACE", "SSR"}
        ):
            snk_low_high_rarity.append(
                {
                    "card_id": cid,
                    "name_kr": card.get("name_kr"),
                    "rarity": rarity,
                    "jp": j,
                    "source": src,
                }
            )

    report = {
        "cards_with_jp_history": len(jp_hist),
        "latest_snkrdunk": snk_latest,
        "jp_crash_vs_yuyutei_60pct": len(crash_vs_yuyu),
        "jp_lt_half_kr_kr_ge_20k": len(jp_lt_half_kr),
        "snkrdunk_latest_high_rarity_jp_le_50k": len(snk_low_high_rarity),
        "crash_vs_yuyu_examples": sorted(
            crash_vs_yuyu, key=lambda x: x["prev_yuyu"] - x["jp"], reverse=True
        )[:40],
        "jp_lt_kr_examples": sorted(
            jp_lt_half_kr, key=lambda x: x["kr"] - x["jp"], reverse=True
        )[:40],
        "snk_low_high_rarity_examples": snk_low_high_rarity[:40],
    }
    out = os.path.join(os.path.dirname(__file__), "_reports", "jp_anomaly_counts.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in report if k.endswith("examples") is False}, ensure_ascii=False, indent=2))
    print("report", out)


if __name__ == "__main__":
    main()
