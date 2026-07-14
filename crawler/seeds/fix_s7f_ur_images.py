"""
S7F UR 126-128 image_url — yuyutei front 이미지 (검증 후 DB 반영).

출처: https://card.yuyu-tei.jp/poc/front/s08/10{card_no}.jpg
패턴: 카드번호 126 → page_id 10126 (10000 + card_no)

실행:
  python fix_s7f_ur_images.py           # 검증만
  python fix_s7f_ur_images.py --apply   # DB 반영
"""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")

APPLY = "--apply" in sys.argv

URLS: dict[tuple[str, str], str] = {
    ("126/100", "UR"): "https://card.yuyu-tei.jp/poc/front/s08/10126.jpg",
    ("127/100", "UR"): "https://card.yuyu-tei.jp/poc/front/s08/10127.jpg",
    ("128/100", "UR"): "https://card.yuyu-tei.jp/poc/front/s08/10128.jpg",
}


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    sid = sb.table("card_sets").select("id").eq("set_code", "S7F").single().execute().data["id"]
    client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

    fixed = 0
    for (num, rar), url in URLS.items():
        r = client.get(url)
        if r.status_code != 200 or len(r.content) < 5000:
            print(f"  FAIL verify {num} {rar}: {r.status_code}")
            continue
        rows = (
            sb.table("cards")
            .select("id,name_kr,image_url")
            .eq("set_id", sid)
            .eq("card_number", num)
            .eq("rarity", rar)
            .execute()
            .data
            or []
        )
        if not rows:
            print(f"  skip {num} {rar}: card not found")
            continue
        row = rows[0]
        print(f"  OK {num} {rar} {row.get('name_kr')} -> {url} ({len(r.content)} bytes)")
        if APPLY:
            sb.table("cards").update({"image_url": url}).eq("id", row["id"]).execute()
        fixed += 1

    print(f"\nfixed={fixed} apply={APPLY}")


if __name__ == "__main__":
    main()
