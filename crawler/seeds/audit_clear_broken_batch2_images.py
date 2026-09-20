"""두 번째 35팩의 실제 표시 불가 이미지만 삭제한다."""
from __future__ import annotations

import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase

TARGETS = {
    "S11a", "S11", "S10b", "S10a", "S9", "S9a", "S8", "S8a", "S8b",
    "S7F", "S7R", "S7D", "S6H", "S6G", "S6L", "S5F", "S5S", "S5P",
    "S4SV", "S4B", "S3H", "S3Z", "S2R", "S2", "S1a", "S1W", "S1H",
    "SM12a", "SM12", "SM11b", "SM11a", "SM10", "SM9", "SM8b", "SM9a",
}
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"}


def check(row: dict) -> dict:
    result = {**row, "broken": False, "reason": ""}
    try:
        response = httpx.get(row["image_url"], headers=HEADERS, timeout=30, follow_redirects=True)
        result["status_code"] = response.status_code
        result["content_type"] = response.headers.get("content-type", "")
        result["bytes"] = len(response.content)
        if response.status_code >= 400:
            result["broken"] = True
            result["reason"] = f"http_{response.status_code}"
            return result
        if len(response.content) < 200:
            result["broken"] = True
            result["reason"] = "empty_or_too_small"
            return result
        if not result["content_type"].lower().startswith("image/"):
            result["broken"] = True
            result["reason"] = "not_image_content_type"
            return result
        with Image.open(io.BytesIO(response.content)) as image:
            image.verify()
        with Image.open(io.BytesIO(response.content)) as image:
            result["width"], result["height"] = image.size
            if image.width < 20 or image.height < 20:
                result["broken"] = True
                result["reason"] = "image_too_small"
    except Exception as exc:
        result["broken"] = True
        result["reason"] = f"{type(exc).__name__}:{exc}"
    return result


def main() -> None:
    sb = get_supabase()
    sets = sb.table("card_sets").select("id,set_code,name_kr").in_("set_code", list(TARGETS)).execute().data or []
    set_by_id = {row["id"]: row for row in sets}
    cards = []
    for set_row in sets:
        cards.extend(
            sb.table("cards")
            .select("id,set_id,card_number,name_kr,rarity,image_url")
            .eq("set_id", set_row["id"])
            .execute()
            .data
            or []
        )
    targets = [row for row in cards if (row.get("image_url") or "").strip()]
    checked = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(check, row) for row in targets]
        for future in as_completed(futures):
            checked.append(future.result())

    broken = []
    for row in checked:
        if not row["broken"]:
            continue
        sb.table("cards").update({"image_url": None}).eq("id", row["id"]).execute()
        meta = set_by_id.get(row["set_id"], {})
        broken.append({
            **row,
            "set_code": meta.get("set_code"),
            "set_name": meta.get("name_kr"),
        })
    report = {
        "scope": "batch2_35_daldagury",
        "cards_with_images_checked": len(targets),
        "broken_cleared": len(broken),
        "broken": sorted(broken, key=lambda row: (row.get("set_code") or "", row.get("card_number") or "", row["id"])),
    }
    out = Path("_audit_out/broken_batch2_images_apply.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "cards_with_images_checked": report["cards_with_images_checked"],
        "broken_cleared": report["broken_cleared"],
        "broken": report["broken"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
