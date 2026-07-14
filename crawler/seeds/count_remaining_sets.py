"""featured 이후 남은 BS* 확장팩 수"""
import httpx
from kr_sets import FEATURED_SET_CODES, KR_BY_CODE

SKIP = (
    "스타트", "배틀 강화", "배틀 아카데미", "프리미엄 트레이너",
    "스페셜 덱", "랜덤 스타트", "강화 BOX", "트레이너 박스",
    "배틀컬렉션", "스타트 덱", "&",
)

featured_ids = {
    KR_BY_CODE[c].collectory_id
    for c in FEATURED_SET_CODES
    if c in KR_BY_CODE and KR_BY_CODE[c].collectory_id
}

r = httpx.get("https://collectory.cc/api/sets", timeout=60)
kr = [s for s in r.json().get("sets") or [] if (s.get("set_code_ko") or "").startswith("BS")]

remaining = []
for s in kr:
    if s["id"] in featured_ids:
        continue
    name = s.get("name_ko") or ""
    if any(x in name for x in SKIP):
        continue
    remaining.append(s)

remaining.sort(key=lambda s: s.get("release_date_ko") or "", reverse=True)
print(f"featured: {len(FEATURED_SET_CODES)}")
print(f"remaining expansions: {len(remaining)}")
print("\nnext 10:")
for i, s in enumerate(remaining[:10]):
    print(f"  {i+1}. {s.get('release_date_ko','')} {(s.get('name_ko') or '')[:30]}")
