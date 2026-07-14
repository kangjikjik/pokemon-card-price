"""
image_url 비어 있는 RR+ 카드에 collectory CDN URL 탐색 후 DB 반영.

실행:
  python fix_missing_card_images.py           # 드라이런
  python fix_missing_card_images.py --apply   # DB 반영
"""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")

APPLY = "--apply" in sys.argv

# KR set_code -> JP collectory path variants
JP_CODE: dict[str, list[str]] = {
    "S2": ["S2", "s2"],
    "S7D": ["S7D", "s7D", "S7d", "s7d"],
    "S7F": ["S8", "s8"],
    "S11": ["S11", "s11"],
    "S12": ["S12", "s12"],
    "SM9": ["SM9a", "sm9a", "SM9", "sm9"],
}

# 수동 확정 URL (probe 실패분)
MANUAL: dict[tuple[str, str, str], str] = {
    ("S7F", "039/100", "RR"): "https://cdn.collectory.cc/cards/jp/S8/039_100RR.webp",
    ("S7F", "110/100", "SR"): "https://cdn.collectory.cc/cards/jp/S8/110_100.webp",
    ("S7F", "126/100", "UR"): "https://cdn.collectory.cc/cards/jp/S8/126_100UR.webp",
    ("S7F", "127/100", "UR"): "https://cdn.collectory.cc/cards/jp/S8/127_100UR.webp",
    ("S7F", "128/100", "UR"): "https://cdn.collectory.cc/cards/jp/S8/128_100UR.webp",
    ("S11", "131/100", "SSR"): "https://cdn.collectory.cc/cards/jp/S11/131_100SSR.webp",
    ("S12", "137/098", "SSR"): "https://cdn.collectory.cc/cards/jp/S12/137_098SSR.webp",
}


def norm_parts(num: str) -> tuple[str, str, str, str]:
    left, right = (num or "").split("/", 1)
    return left, left.zfill(3), right, str(int(left)) if left.isdigit() else left


def probe_url(client: httpx.Client, url: str) -> bool:
    try:
        r = client.get(url)
        return r.status_code == 200 and len(r.content) > 5000
    except Exception:
        return False


def find_url(client: httpx.Client, code: str, num: str, rar: str) -> str | None:
    key = (code, num, rar)
    if key in MANUAL:
        url = MANUAL[key]
        if probe_url(client, url):
            return url

    left, left3, right, left_int = norm_parts(num)
    jp_codes = JP_CODE.get(code, [code])
    suffixes = [rar, ""] if rar else [""]
    for jp in jp_codes:
        for lf in {left, left3, left_int}:
            for suf in suffixes:
                for sep in ("_", "-"):
                    candidates = [
                        f"https://cdn.collectory.cc/cards/jp/{jp}/{lf}{sep}{right}{suf}.webp",
                        f"https://cdn.collectory.cc/cards/jp/{jp}/{lf}{sep}{right}.webp",
                    ]
                    for url in candidates:
                        if probe_url(client, url):
                            return url
    return None


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    sets = sb.table("card_sets").select("id,set_code").execute().data or []
    set_by_id = {s["id"]: s["set_code"] for s in sets}

    cards: list[dict] = []
    offset = 0
    while True:
        batch = (
            sb.table("cards")
            .select("id,set_id,card_number,rarity,name_kr,image_url")
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        cards.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    missing = [c for c in cards if not (c.get("image_url") or "").strip()]
    print(f"missing image_url: {len(missing)}")

    client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    fixed = 0
    still = 0
    for c in sorted(missing, key=lambda x: (set_by_id[x["set_id"]], x.get("card_number") or "")):
        code = set_by_id[c["set_id"]]
        num = c.get("card_number") or ""
        rar = c.get("rarity") or ""
        url = find_url(client, code, num, rar)
        if url:
            print(f"  OK {code:6} {num:9} {rar:4} -> {url}")
            if APPLY:
                sb.table("cards").update({"image_url": url}).eq("id", c["id"]).execute()
            fixed += 1
        else:
            print(f"  -- {code:6} {num:9} {rar:4} {c.get('name_kr') or ''}")
            still += 1

    print(f"\nfixed={fixed} still_missing={still} apply={APPLY}")


if __name__ == "__main__":
    main()
