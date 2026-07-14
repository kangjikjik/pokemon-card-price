"""featured 100 타임라인 — collectory BS* 갭 잔여 검증"""
from __future__ import annotations

import httpx
from kr_sets import FEATURED_SET_CODES, KR_BY_CODE

SKIP = (
    "스타트", "배틀 강화", "배틀 아카데미", "프리미엄 트레이너",
    "스페셜 덱", "랜덤 스타트", "강화 BOX", "트레이너 박스",
    "배틀컬렉션", "스타트 덱", "&",
    "GOLDEN", "패밀리", "스페셜 세트", "스페셜 케이스",
    "카드 앨범", "TAG TEAM GX 스타터", "프리미엄 챔피언팩",
    "포켓심쿵", "레전드 컬렉션", "마그마단vs아쿠아단", "샤이니 컬렉션",
)
MIN_CARDS = 70


def norm(s: str) -> str:
    return (s or "").replace(" ", "").lower()


featured_ids = {
    KR_BY_CODE[c].collectory_id
    for c in FEATURED_SET_CODES
    if c in KR_BY_CODE and KR_BY_CODE[c].collectory_id
}
featured_names = {norm(KR_BY_CODE[c].name_kr) for c in FEATURED_SET_CODES if c in KR_BY_CODE}

r = httpx.get("https://collectory.cc/api/sets", timeout=60)
kr = [s for s in r.json().get("sets") or [] if (s.get("set_code_ko") or "").startswith("BS")]
client = httpx.Client(timeout=90)
remaining = []
for s in kr:
    name = s.get("name_ko") or ""
    if any(x in name for x in SKIP):
        continue
    if s["id"] in featured_ids or norm(name) in featured_names:
        continue
    cnt = len(client.get(f"https://collectory.cc/api/sets/{s['id']}/cards").json().get("cards") or [])
    if cnt < MIN_CARDS:
        continue
    remaining.append((s.get("release_date_ko"), name, cnt, s.get("set_code_ko")))

remaining.sort(reverse=True)
print(f"featured: {len(FEATURED_SET_CODES)}")
print(f"remaining gaps (cards>={MIN_CARDS}): {len(remaining)}")
for row in remaining[:15]:
    print(f"  {row[0]} {row[1][:30]:30} cards={row[2]:3} {row[3]}")

# 중복 collectory_id / code 검사
ids = [KR_BY_CODE[c].collectory_id for c in FEATURED_SET_CODES if c in KR_BY_CODE]
print(f"\ndup collectory_id: {len(ids) - len(set(ids))}")
print(f"dup codes: {len(FEATURED_SET_CODES) - len(set(FEATURED_SET_CODES))}")
