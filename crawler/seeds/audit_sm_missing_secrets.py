"""SM시대 정규팩: SR 있는데 HR/UR 없는 세트 탐지 (collectory 완전성 ≠ 공식 완전성)."""
from __future__ import annotations

import os
import sys
from collections import Counter

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from kr_sets import KR_SETS

# SM 정규 부스터에서 보통 기대하는 시크릿 패턴
SM_ERA_START = "2018-01-01"
SM_ERA_END = "2019-12-31"  # 태그팀 이전·포함 대략

HIGH = {"UR", "HR", "SSR", "SAR", "MUR", "FUR", "MA", "BWR", "ACE"}

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

suspect = []
for s in sorted(KR_SETS, key=lambda x: x.released_at):
    rows = sb.table("card_sets").select("id").eq("set_code", s.code).execute().data or []
    if not rows:
        continue
    cards = (
        sb.table("cards")
        .select("rarity")
        .eq("set_id", rows[0]["id"])
        .execute()
        .data
        or []
    )
    dist = Counter(c["rarity"] for c in cards)
    has_sr = dist.get("SR", 0) > 0
    has_high = any(dist.get(r, 0) > 0 for r in HIGH)
    # SM 시대 + SR 있는데 UR/HR급 없음
    if SM_ERA_START <= s.released_at <= SM_ERA_END and has_sr and not has_high:
        suspect.append((s.code, s.name_kr, s.released_at, dict(dist)))

print(f"SM시대 SR만 있고 HR/UR급 없음: {len(suspect)}")
for row in suspect:
    print(f"  {row[0]:8} {row[1]} {row[2]} {row[3]}")
