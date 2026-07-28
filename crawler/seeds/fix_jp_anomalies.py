#!/usr/bin/env python3
"""JP<KR·유유테i 급락 카드가 속한 세트를 정밀 재크롤."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from utils.db import get_supabase

SEEDS = os.path.dirname(__file__)
CRAWLER = os.path.join(SEEDS, "crawl_set_prices_jp.py")


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
    sets = {
        int(s["id"]): s.get("set_code")
        for s in (sb.table("card_sets").select("id,set_code").execute().data or [])
    }
    cards = sb.table("cards").select("id,set_id,name_kr,rarity").execute().data or []
    card_set: dict[int, str] = {}
    for c in cards:
        cid = int(c["id"])
        sid = c.get("set_id")
        if sid and int(sid) in sets and sets[int(sid)]:
            card_set[cid] = str(sets[int(sid)])

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

    target_sets: set[str] = set()
    flagged: list[dict] = []

    for cid, items in jp_hist.items():
        if not items:
            continue
        latest = items[0]
        j = int(latest.get("price_krw") or 0)
        src = str(latest.get("source") or "")
        k = kr_latest.get(cid, 0)
        prev_yuyu = next(
            (
                int(h.get("price_krw") or 0)
                for h in items[1:]
                if "yuyutei" in str(h.get("source") or "").lower()
            ),
            0,
        )
        reasons: list[str] = []
        if k >= 20000 and j > 0 and j < k:
            reasons.append("jp_lt_kr")
        if prev_yuyu >= 10000 and j > 0 and j < prev_yuyu * 0.4:
            reasons.append("jp_crash_yuyutei")
        if "snkrdunk" in src.lower() and j > 0 and j <= 50000:
            r = (next((c.get("rarity") for c in cards if int(c["id"]) == cid), "") or "").upper()
            if r in {"UR", "SAR", "MUR", "MA", "HR", "ACE", "SSR"}:
                reasons.append("snk_low_high_rarity")
        if not reasons:
            continue
        sc = card_set.get(cid)
        if sc:
            target_sets.add(sc)
        flagged.append({"card_id": cid, "set_code": sc, "jp": j, "kr": k, "source": src, "reasons": reasons})

    ordered_sets = sorted(target_sets)
    report = {
        "flagged_cards": len(flagged),
        "target_sets": ordered_sets,
        "examples": flagged[:50],
    }
    out = os.path.join(SEEDS, "_reports", "jp_fix_targets.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"flagged {len(flagged)} cards across {len(ordered_sets)} sets")
    print(f"report: {out}")

    if not ordered_sets:
        print("nothing to fix")
        return

    ok_sets: list[str] = []
    fail_sets: list[str] = []
    for i, sc in enumerate(ordered_sets):
        if i > 0:
            time.sleep(2)
        cmd = [
            sys.executable,
            CRAWLER,
            "--set",
            sc,
            "--apply",
            "--fallback",
            "--thorough",
        ]
        print(f"\n>>> [{i + 1}/{len(ordered_sets)}] {sc}")
        rc = subprocess.call(cmd, cwd=SEEDS)
        if rc == 0:
            ok_sets.append(sc)
        else:
            fail_sets.append(sc)

    summary = {"ok_sets": ok_sets, "fail_sets": fail_sets, "total": len(ordered_sets)}
    sum_path = os.path.join(SEEDS, "_reports", "jp_fix_run_summary.json")
    with open(sum_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nDone: ok={len(ok_sets)} fail={len(fail_sets)} summary={sum_path}")


if __name__ == "__main__":
    main()
