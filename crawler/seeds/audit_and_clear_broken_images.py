"""전체 카드 이미지 URL을 검증하고 실제로 깨진 URL만 비운다."""
from __future__ import annotations

import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

from utils.db import get_supabase

OUT = Path("_audit_out/broken_card_images_apply.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def load_all(sb, table: str, fields: str) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        batch = sb.table(table).select(fields).range(start, start + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        start += 1000


def check(card: dict) -> dict:
    url = (card.get("image_url") or "").strip()
    result = {**card, "url": url, "broken": False, "reason": ""}
    if not url:
        return result
    try:
        response = httpx.get(url, headers=HEADERS, timeout=25, follow_redirects=True)
        result["status_code"] = response.status_code
        result["final_url"] = str(response.url)
        content_type = (response.headers.get("content-type") or "").lower()
        result["content_type"] = content_type
        if response.status_code >= 400:
            result["broken"] = True
            result["reason"] = f"http_{response.status_code}"
            return result
        if len(response.content) < 200:
            result["broken"] = True
            result["reason"] = "empty_or_too_small"
            return result
        try:
            with Image.open(io.BytesIO(response.content)) as image:
                image.verify()
            result["bytes"] = len(response.content)
        except Exception as exc:
            result["broken"] = True
            result["reason"] = f"invalid_image:{type(exc).__name__}"
            return result
    except Exception as exc:
        result["broken"] = True
        result["reason"] = f"request:{type(exc).__name__}"
    return result


def main() -> None:
    sb = get_supabase()
    sets = load_all(sb, "card_sets", "id,set_code,name_kr")
    set_by_id = {row["id"]: row for row in sets}
    cards = load_all(sb, "cards", "id,set_id,card_number,name_kr,rarity,image_url")
    targets = [card for card in cards if (card.get("image_url") or "").strip()]

    checked: list[dict] = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(check, card) for card in targets]
        for future in as_completed(futures):
            checked.append(future.result())

    broken = []
    for row in checked:
        if not row["broken"]:
            continue
        meta = set_by_id.get(row.get("set_id"), {})
        row["set_code"] = meta.get("set_code")
        row["set_name"] = meta.get("name_kr")
        # Only the image URL is cleared; card identity and price history stay intact.
        sb.table("cards").update({"image_url": None}).eq("id", row["id"]).execute()
        broken.append(row)

    report = {
        "policy": "all cards with non-empty image_url; clear only HTTP errors, request failures, or invalid image bytes",
        "cards_total": len(cards),
        "cards_with_images": len(targets),
        "cards_checked": len(checked),
        "broken_cleared": len(broken),
        "broken": sorted(
            broken,
            key=lambda row: (
                row.get("set_name") or "",
                row.get("card_number") or "",
                row.get("id") or 0,
            ),
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
