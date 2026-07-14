"""MG6 카드 이미지 URL 검증 — DB vs 유유테이 front 패턴"""
import os
import re
import httpx
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

set_row = sb.table("card_sets").select("id").eq("set_code", "MG6").single().execute()
set_id = set_row.data["id"]
cards = (
    sb.table("cards")
    .select("id,name_jp,name_kr,rarity,card_number,image_url")
    .eq("set_id", set_id)
    .order("card_number")
    .execute()
    .data or []
)

print(f"MG6 카드 {len(cards)}장 검증\n")
errors = []
ok = 0

with httpx.Client(timeout=15, follow_redirects=True) as client:
    for c in cards:
        url = c.get("image_url") or ""
        num = c.get("card_number") or ""
        rarity = c.get("rarity") or ""
        name = c.get("name_kr") or c.get("name_jp")

        issues = []

        # 시크릿(082+)은 front/m05/{10000+num} 패턴이어야 함
        if num and "/" in num:
            card_num = int(num.split("/")[0])
            if card_num >= 82:
                expected = f"https://card.yuyu-tei.jp/poc/front/m05/{10000 + card_num}.jpg"
                if url != expected:
                    issues.append(f"URL 불일치: got={url[-30:]} expected=...{expected[-20:]}")
            elif card_num <= 81:
                if "pokemon-card.com" not in url:
                    issues.append(f"기본카드는 공식 URL 필요: {url[:60]}")

        # 잘못된 구 패턴
        if "100_140" in url:
            issues.append("구 잘못된 100_140 패턴 사용")

        # HTTP 접근 확인
        if url:
            try:
                r = client.head(url)
                if r.status_code != 200:
                    issues.append(f"HTTP {r.status_code}")
            except Exception as e:
                issues.append(f"HTTP 오류: {e}")

        if issues:
            errors.append((name, rarity, num, issues))
            print(f"FAIL [{rarity}] {name} ({num})")
            for i in issues:
                print(f"     - {i}")
        else:
            ok += 1

print(f"\n결과: OK {ok} / FAIL {len(errors)} / TOTAL {len(cards)}")
if errors:
    raise SystemExit(1)
