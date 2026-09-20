"""KR·JP prices 테이블 간 동일 번개 PID 중복 감사.

JP 필터는 일판 표기 필수 — KR 체결이 prices_jp에 섞이면 FAIL.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from utils.db import get_supabase

PID_RE = re.compile(r":bunjang:(\d+)")


def audit_set(set_code: str) -> int:
    sb = get_supabase()
    set_row = sb.table("card_sets").select("id,name_kr").eq("set_code", set_code).single().execute().data
    if not set_row:
        print(f"{set_code}: 세트 없음")
        return 0

    cards = sb.table("cards").select("id,name_kr,card_number,rarity").eq("set_id", set_row["id"]).execute().data or []
    fails = 0
    total_shared = 0

    print(f"=== {set_row['name_kr']}({set_code}) KR/JP PID 중복 ===")
    for c in cards:
        cid = c["id"]
        kr_rows = sb.table("prices_kr").select("source").eq("card_id", cid).execute().data or []
        jp_rows = sb.table("prices_jp").select("source").eq("card_id", cid).execute().data or []
        kr_pids = {m.group(1) for r in kr_rows if (m := PID_RE.search(r.get("source") or ""))}
        jp_pids = {m.group(1) for r in jp_rows if (m := PID_RE.search(r.get("source") or ""))}
        shared = kr_pids & jp_pids
        if shared:
            fails += 1
            total_shared += len(shared)
            print(
                f"  FAIL [{c.get('card_number')}] {c.get('name_kr')} "
                f"— {len(shared)}개 PID 중복 (kr {len(kr_pids)}, jp {len(jp_pids)})"
            )

    print(f"\n결과: {fails}/{len(cards)}장 중복, shared PID {total_shared}건")
    return fails


def main() -> None:
    set_code = "MG6"
    if "--set" in sys.argv:
        i = sys.argv.index("--set")
        if i + 1 < len(sys.argv):
            set_code = sys.argv[i + 1]
    n = audit_set(set_code)
    sys.exit(1 if n else 0)


if __name__ == "__main__":
    main()
