"""세트별 URL 있는 거래내역(sold:bunjang:PID / sold:snkrdunk:PID:date) 커버리지."""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from utils.db import get_supabase

sb = get_supabase()

PID_KR = re.compile(r"^sold:bunjang:\d+")
PID_JP = re.compile(r"^sold:(bunjang:\d+|snkrdunk:\d+:\d{4}-\d{2}-\d{2})")


def audit_set(code: str) -> None:
    row = sb.table("card_sets").select("id,name_kr").eq("set_code", code).execute().data
    if not row:
        print(f"{code}: no set")
        return
    sid = row[0]["id"]
    name = row[0]["name_kr"]
    cards = sb.table("cards").select("id").eq("set_id", sid).execute().data or []
    ids = [c["id"] for c in cards]
    if not ids:
        print(f"{code}: no cards")
        return

    kr_all, jp_all = [], []
    for i in range(0, len(ids), 100):
        chunk = ids[i : i + 100]
        kr_all.extend(
            sb.table("prices_kr")
            .select("card_id,source")
            .in_("card_id", chunk)
            .like("source", "sold:%")
            .execute()
            .data
            or []
        )
        jp_all.extend(
            sb.table("prices_jp")
            .select("card_id,source")
            .in_("card_id", chunk)
            .like("source", "sold:%")
            .execute()
            .data
            or []
        )

    kr_url = [r for r in kr_all if PID_KR.match(r.get("source") or "")]
    jp_url = [r for r in jp_all if PID_JP.match(r.get("source") or "")]
    kr_cards = len({r["card_id"] for r in kr_url})
    jp_cards = len({r["card_id"] for r in jp_url})
    print(
        f"{code:6} {name[:12]:12} cards={len(ids):3}  "
        f"KR url: {kr_cards:3} cards / {len(kr_url):4} rows  "
        f"JP url: {jp_cards:3} cards / {len(jp_url):4} rows"
    )


if __name__ == "__main__":
    codes = sys.argv[1:] or [
        "MG6", "MG5a", "MG5", "MG4", "SV7", "SV6", "SV2a", "SV1a", "S12a", "SM12a", "XY11",
    ]
    for c in codes:
        audit_set(c)
