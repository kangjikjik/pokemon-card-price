"""S8b 이전 BS* 확장팩 후보"""
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
kr.sort(key=lambda s: s.get("release_date_ko") or "", reverse=True)

cutoff = "2022-02-10"  # S8b
filtered = []
for s in kr:
    if s["id"] in featured_ids:
        continue
    if (s.get("release_date_ko") or "") > cutoff:
        continue
    name = s.get("name_ko") or ""
    if any(x in name for x in SKIP):
        continue
    filtered.append(s)

print(f"featured: {len(FEATURED_SET_CODES)}, candidates older than S8b: {len(filtered)}")
client = httpx.Client(timeout=90)
for i, s in enumerate(filtered[:20]):
    cnt = len(client.get(f"https://collectory.cc/api/sets/{s['id']}/cards").json().get("cards") or [])
    print(
        f"{i+1:2}. {s.get('set_code_ko',''):12} {s.get('release_date_ko',''):12} "
        f"cards={cnt:3} {(s.get('name_ko') or '')[:28]:28} {s['id']}"
    )
    print(f"    {(s.get('image_url') or '')[:90]}")
