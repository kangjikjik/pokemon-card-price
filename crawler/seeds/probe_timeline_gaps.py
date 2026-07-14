"""featured 타임라인 빈 구간 분석"""
import httpx
from kr_sets import FEATURED_SET_CODES, KR_BY_CODE

SKIP = (
    "스타트", "배틀 강화", "배틀 아카데미", "프리미엄 트레이너",
    "스페셜 덱", "랜덤 스타트", "강화 BOX", "트레이너 박스",
    "배틀컬렉션", "스타트 덱", "&",
    "GOLDEN BOX", "GOLDEN",
    "패밀리",
    "스페셜 세트", "스페셜 케이스", "스페셜 점보",
    "카드 앨범", "카드 실드",
    "프리미엄 트레이너",
)

featured_ids = {
    KR_BY_CODE[c].collectory_id
    for c in FEATURED_SET_CODES
    if c in KR_BY_CODE and KR_BY_CODE[c].collectory_id
}
featured_names = {
    (KR_BY_CODE[c].name_kr or "").replace(" ", "")
    for c in FEATURED_SET_CODES
    if c in KR_BY_CODE
}

r = httpx.get("https://collectory.cc/api/sets", timeout=60)
kr = [
    s for s in r.json().get("sets") or []
    if (s.get("set_code_ko") or "").startswith("BS")
]
kr.sort(key=lambda s: s.get("release_date_ko") or "", reverse=True)

gaps = []
for s in kr:
    if s["id"] in featured_ids:
        continue
    name = s.get("name_ko") or ""
    if any(x in name for x in SKIP):
        continue
    norm = name.replace(" ", "")
    # 이름 중복 (SV5a 나이트원더러 vs BS2024011 등)
    if any(norm in fn or fn in norm for fn in featured_names if len(fn) > 4):
        continue
    gaps.append(s)

print(f"featured: {len(FEATURED_SET_CODES)}")
print(f"gap candidates (no dup name): {len(gaps)}")
print()
client = httpx.Client(timeout=90)
for i, s in enumerate(gaps):
    cnt = len(client.get(f"https://collectory.cc/api/sets/{s['id']}/cards").json().get("cards") or [])
    if cnt < 25:  # 덱/스페셜 소량 제외
        continue
    print(
        f"{i+1:2}. {s.get('set_code_ko',''):14} {s.get('release_date_ko',''):12} "
        f"cards={cnt:3} {(s.get('name_ko') or '')[:32]:32} | {s['id']}"
    )
    img = s.get("image_url") or ""
    if img:
        print(f"    {img[:95]}")
