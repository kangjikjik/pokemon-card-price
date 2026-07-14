"""featured 타임라인 vs collectory BS* — 빈 구간·중복 분석"""
from __future__ import annotations

import httpx
from kr_sets import FEATURED_SET_CODES, KR_BY_CODE, KR_SETS

SKIP = (
    "스타트", "배틀 강화", "배틀 아카데미", "프리미엄 트레이너",
    "스페셜 덱", "랜덤 스타트", "강화 BOX", "트레이너 박스",
    "배틀컬렉션", "스타트 덱", "&",
    "GOLDEN BOX", "GOLDEN", "패밀리",
    "스페셜 세트", "스페셜 케이스", "스페셜 점보",
    "카드 앨범", "카드 실드",
    "TAG TEAM GX 스타터",
    "프리미엄 챔피언팩", "포켓심쿵", "레전드 컬렉션",
    "환상 전legend", "환상 전설 드림",
    "마그마단vs아쿠아단",
    "샤이니 컬렉션",
)

MIN_CARDS = 70  # 덱/소형 제외


def norm(s: str) -> str:
    return (s or "").replace(" ", "").lower()


featured_by_cid = {}
featured_by_name = {}
for c in FEATURED_SET_CODES:
    if c not in KR_BY_CODE:
        continue
    s = KR_BY_CODE[c]
    if s.collectory_id:
        featured_by_cid[s.collectory_id] = c
    featured_by_name[norm(s.name_kr)] = c

r = httpx.get("https://collectory.cc/api/sets", timeout=60)
kr = [
    s for s in r.json().get("sets") or []
    if (s.get("set_code_ko") or "").startswith("BS")
]
kr.sort(key=lambda s: s.get("release_date_ko") or "", reverse=True)

client = httpx.Client(timeout=90)
eligible = []
for s in kr:
    cid = s["id"]
    name = s.get("name_ko") or ""
    if any(x in name for x in SKIP):
        continue
    if cid in featured_by_cid:
        continue
    # 이름 중복 (SV5a 나이트원더러 = BS2024011)
    if norm(name) in featured_by_name:
        continue
    cnt = len(client.get(f"https://collectory.cc/api/sets/{cid}/cards").json().get("cards") or [])
    if cnt < MIN_CARDS:
        continue
    eligible.append({**s, "card_count": cnt})

print(f"featured: {len(FEATURED_SET_CODES)}")
print(f"missing eligible (cards>={MIN_CARDS}): {len(eligible)}")
print()

# featured 발매일 목록
feat_dates = sorted(
    [(KR_BY_CODE[c].released_at, c, KR_BY_CODE[c].name_kr) for c in FEATURED_SET_CODES if c in KR_BY_CODE],
    reverse=True,
)
print("=== 최근 featured 구간 빈틈 (2024~) ===")
recent_feat = [f for f in feat_dates if f[0] >= "2024-01-01"]
recent_missing = [e for e in eligible if (e.get("release_date_ko") or "") >= "2024-01-01"]
for m in recent_missing:
    print(
        f"  GAP {m.get('release_date_ko',''):12} {(m.get('name_ko') or '')[:28]:28} "
        f"cards={m['card_count']:3} {m.get('set_code_ko',''):14} {m['id']}"
    )

print()
print("=== 과거 featured 구간 (S2R~2023) 빈틈 ===")
old_missing = [
    e for e in eligible
    if "2020-06-16" <= (e.get("release_date_ko") or "") < "2024-01-01"
]
for m in old_missing:
    print(
        f"  GAP {m.get('release_date_ko',''):12} {(m.get('name_ko') or '')[:28]:28} "
        f"cards={m['card_count']:3} {m.get('set_code_ko',''):14} {m['id']}"
    )

print()
print("=== S2R 이전 확장팩 ===")
pre_s2r = [e for e in eligible if (e.get("release_date_ko") or "") < "2020-06-16"]
print(f"count: {len(pre_s2r)}")
for m in pre_s2r[:20]:
    print(
        f"  {m.get('release_date_ko',''):12} {(m.get('name_ko') or '')[:28]:28} "
        f"cards={m['card_count']:3} {m.get('set_code_ko',''):14}"
    )
if len(pre_s2r) > 20:
    print(f"  ... +{len(pre_s2r)-20} more")
