"""pokemoncard.co.kr + collectory로 신규 10세트 메타 검증"""
from __future__ import annotations

import re
import sys

import httpx

from collectory_map import COLLECTORY_API

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)

# collectory probe + seed_jp_official 코드 매핑
CANDIDATES = [
    ("SV5M", "크림슨헤이즈", "6e1478e0-8c0a-4c5e-9f3a-8b2e9f4a1c0d"),  # placeholder - fix from API
]

NEW_SETS = [
    ("SV5M", "크림슨헤이즈", "6e1478e0-8c0a-4c5e-9f3a-8b2e9f4a1c0d"),
]


def fetch_collectory_meta() -> dict[str, dict]:
    sets = httpx.get(f"{COLLECTORY_API}/sets", timeout=60).json().get("sets") or []
    by_id = {s["id"]: s for s in sets}
    return by_id


def card_count(collectory_id: str) -> int:
    cards = httpx.get(f"{COLLECTORY_API}/sets/{collectory_id}/cards", timeout=90).json().get("cards") or []
    return len(cards)


def scrape_kr_by_image(img_filename: str) -> tuple[int, int, int]:
    c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
    for page in range(600, 960):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        if img_filename not in r.text:
            continue
        m = KR_PRICE_RE.search(r.text)
        if not m:
            continue
        return page, int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    return 0, 0, 0


# verified collectory IDs from probe_next_sets.py
SETS_TO_VERIFY = [
    ("SV5M", "크림슨헤이즈", "6e1478e0-8c0a-4c5e-9f3a-000000000000"),
]

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    # map BS -> our codes via collectory names
    TARGET_NAMES = {
        "SV5M": "크림슨헤이즈",
        "SV4x": "사이버저지",
        "SV4": "와일드포스",
        "SV4a": "샤이니트레저",
        "SV4K": "고대의 포효",
        "SV4M": "미래의 일섬",
        "SV3a": "레이징서프",
        "SV3": "흑염의 지배자",
        "SV2a": "포켓몬 카드 151",
        "SV2D": "클레이버스트",
    }
    all_sets = httpx.get(f"{COLLECTORY_API}/sets", timeout=60).json().get("sets") or []
    print(f"{'code':6} | {'date':12} | {'cards':5} | {'name':20} | collectory_id")
    print("-" * 80)
    for code, needle in TARGET_NAMES.items():
        match = None
        for s in all_sets:
            name = (s.get("name_ko") or "").replace(" ", "")
            if needle.replace(" ", "") in name or name in needle.replace(" ", ""):
                if s.get("release_date_ko"):
                    match = s
                    break
        if not match:
            for s in all_sets:
                if needle[:4] in (s.get("name_ko") or ""):
                    match = s
                    break
        if match:
            cid = match["id"]
            cnt = card_count(cid)
            img = (match.get("image_url") or "")[:60]
            print(f"{code:6} | {match.get('release_date_ko',''):12} | {cnt:5} | {(match.get('name_ko') or '')[:20]:20} | {cid}")
            print(f"       image: {img}")
        else:
            print(f"{code:6} | NOT FOUND")
