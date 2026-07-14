"""collectory + kr_sets 기준 featured 확장 후보 조사"""
import httpx
from kr_sets import FEATURED_SET_CODES, KR_SETS_ALL

r = httpx.get("https://collectory.cc/api/sets", timeout=60)
sets = r.json().get("sets") or []
kr = [s for s in sets if s.get("set_code_ko")]
kr.sort(key=lambda s: s.get("release_date_ko") or "", reverse=True)

featured = set(FEATURED_SET_CODES)
all_codes = {s.code for s in KR_SETS_ALL}

print("=== collectory KR sets (newest first) ===")
for s in kr[:45]:
    code = s.get("set_code_ko")
    mark = "F" if code in featured else ("A" if code in all_codes else " ")
    name = (s.get("name_ko") or "")[:24]
    print(f"{mark} {code:6} {s.get('release_date_ko',''):12} {name:24} {s['id'][:8]}")

print("\n=== not featured, older than SV5K (2024-05-10) ===")
sv5k_date = "2024-05-10"
candidates = [
    s for s in kr
    if s.get("set_code_ko") not in featured
    and (s.get("release_date_ko") or "") < sv5k_date
]
candidates.sort(key=lambda s: s.get("release_date_ko") or "", reverse=True)
for s in candidates[:15]:
    print(s.get("set_code_ko"), s.get("release_date_ko"), s.get("name_ko"), s["id"])

print("\n=== not featured but newer than SV5K (gaps in timeline) ===")
gaps = [
    s for s in kr
    if s.get("set_code_ko") not in featured
    and (s.get("release_date_ko") or "") >= sv5k_date
]
gaps.sort(key=lambda s: s.get("release_date_ko") or "", reverse=True)
for s in gaps[:15]:
    print(s.get("set_code_ko"), s.get("release_date_ko"), s.get("name_ko"), s["id"])
