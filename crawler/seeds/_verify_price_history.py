"""일별 스냅샷 저장 검증 (CEL 카드 1장, 끝나면 원복).

  python _verify_price_history.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.price_history import kst_day_bounds_utc, save_daily_snapshots  # noqa: E402
from lib.rarity_rank import is_displayable_rarity  # noqa: E402

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
KST = timezone(timedelta(hours=9))


def main() -> None:
    start, end = kst_day_bounds_utc()
    print(f"[1] KST today UTC bounds: {start} .. {end}")
    assert start < end

    set_row = sb.table("card_sets").select("id").eq("set_code", "CEL").execute().data
    assert set_row, "CEL set missing"
    cards = (
        sb.table("cards")
        .select("id,rarity")
        .eq("set_id", set_row[0]["id"])
        .execute()
        .data
        or []
    )
    cards = [c for c in cards if is_displayable_rarity(c.get("rarity"))]
    assert cards, "CEL no displayable cards"
    card_id = cards[0]["id"]
    print(f"[2] test card_id={card_id} (CEL)")

    # 원복용 백업
    backup = (
        sb.table("prices_jp")
        .select("card_id,price_jpy,price_krw,source,fetched_at")
        .eq("card_id", card_id)
        .execute()
        .data
        or []
    )
    print(f"[3] backup rows={len(backup)}")

    try:
        yesterday = (datetime.now(KST) - timedelta(days=1)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        y_iso = yesterday.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        sb.table("prices_jp").insert({
            "card_id": card_id,
            "price_jpy": 999,
            "price_krw": 9990,
            "source": "verify_yesterday",
            "fetched_at": y_iso,
        }).execute()
        print(f"[4] inserted yesterday stub @ {y_iso}")

        deleted, inserted = save_daily_snapshots(
            sb,
            "prices_jp",
            [card_id],
            [{
                "card_id": card_id,
                "price_jpy": 1234,
                "price_krw": 12340,
                "source": "verify_today",
            }],
        )
        print(f"[5] save #1 deleted={deleted} inserted={inserted}")

        mid = (
            sb.table("prices_jp")
            .select("id,price_jpy,source,fetched_at")
            .eq("card_id", card_id)
            .execute()
            .data
            or []
        )
        y_after = [r for r in mid if r.get("source") == "verify_yesterday"]
        t_after = [r for r in mid if r.get("source") == "verify_today"]
        print(f"[6] after1 total={len(mid)} yesterday={len(y_after)} today={len(t_after)}")
        assert len(y_after) == 1, "yesterday stub must survive"
        assert len(t_after) == 1, "exactly one today snapshot"

        deleted2, inserted2 = save_daily_snapshots(
            sb,
            "prices_jp",
            [card_id],
            [{
                "card_id": card_id,
                "price_jpy": 2222,
                "price_krw": 22220,
                "source": "verify_today",
            }],
        )
        print(f"[7] save #2 deleted={deleted2} inserted={inserted2}")

        end_rows = (
            sb.table("prices_jp")
            .select("id,price_jpy,source")
            .eq("card_id", card_id)
            .execute()
            .data
            or []
        )
        y_end = [r for r in end_rows if r.get("source") == "verify_yesterday"]
        t_end = [r for r in end_rows if r.get("source") == "verify_today"]
        print(
            f"[8] after2 total={len(end_rows)} yesterday={len(y_end)} "
            f"today={len(t_end)} price={t_end[0]['price_jpy'] if t_end else None}"
        )
        assert len(y_end) == 1
        assert len(t_end) == 1
        assert t_end[0]["price_jpy"] == 2222
        print("\nOK — price history helper verified")
    finally:
        # 전체 삭제 후 백업 복원
        sb.table("prices_jp").delete().eq("card_id", card_id).execute()
        if backup:
            sb.table("prices_jp").insert(backup).execute()
        print(f"[9] restored {len(backup)} original rows")


if __name__ == "__main__":
    main()
