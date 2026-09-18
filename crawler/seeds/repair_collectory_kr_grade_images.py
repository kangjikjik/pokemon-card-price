"""한국판 Collectory 이미지로 등급 불일치 카드만 교체한다."""
from __future__ import annotations

import io
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
import pytesseract
from PIL import Image
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

from kr_sets import KR_SETS
from utils.db import get_supabase

OUT = Path("_audit_out/collectory_kr_grade_repair.json")
EXCLUDED_RARITIES = {"C", "U", "R"}
TARGET_RARITIES = {"RR", "RRR", "AR", "CHR", "PR", "SR", "SAR", "HR", "UR", "MUR", "P"}
NUM_RE = re.compile(r"\b(\d{1,3})\s*/\s*(\d{1,3})\b")
RARITY_RE = re.compile(r"\b(RRR|MUR|SAR|CHR|PR|RR|SR|HR|UR|AR|P)\b", re.I)


def _ocr(url: str) -> tuple[str, str]:
    response = httpx.get(url, timeout=25, follow_redirects=True)
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    width, height = image.size
    crop = image.crop((0, int(height * 0.72), width, height)).resize((width * 2, (height - int(height * 0.72)) * 2))
    text = pytesseract.image_to_string(crop, lang="kor+eng", config="--psm 6")
    number = next((f"{a}/{b}" for a, b in NUM_RE.findall(text)), "")
    rarity_match = RARITY_RE.search(text)
    return number, rarity_match.group(1).upper() if rarity_match else ""


def _candidates(set_code: str, card_number: str, rarity: str) -> list[str]:
    if not card_number or "/" not in card_number:
        return []
    number, total = card_number.replace(" ", "").split("/", 1)
    base = set_code.removesuffix("-kr")
    stem = f"{int(number):03d}_{int(total):03d}"
    return [
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}{rarity}.webp",
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}{rarity}.jpg",
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}.webp",
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}.jpg",
    ]


def _load(sb, set_id: int) -> list[dict]:
    rows, start = [], 0
    while True:
        batch = sb.table("cards").select(
            "id,card_number,name_kr,rarity,image_url"
        ).eq("set_id", set_id).range(start, start + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        start += 1000


def main() -> None:
    sb = get_supabase()
    sets = {r["set_code"]: r for r in sb.table("card_sets").select("id,set_code,name_kr").execute().data or []}
    targets = []
    for meta in KR_SETS:
        if meta.code not in sets:
            continue
        for card in _load(sb, sets[meta.code]["id"]):
            if card.get("rarity") in TARGET_RARITIES and card.get("rarity") not in EXCLUDED_RARITIES:
            targets.append(
                {
                    **card,
                    "set_code": meta.code,
                    "collectory_set": meta.bs_code,
                    "set": sets[meta.code]["name_kr"],
                }
            )

    report = {"checked": len(targets), "unchanged": 0, "changed": [], "unresolved": []}

    def one(card: dict) -> tuple[dict, dict]:
        expected_number = (card.get("card_number") or "").replace(" ", "")
        expected_rarity = (card.get("rarity") or "").upper()
        try:
            current_number, current_rarity = _ocr(card.get("image_url") or "")
        except Exception:
            current_number, current_rarity = "", ""
        if current_number == expected_number and current_rarity == expected_rarity:
            return card, {"status": "unchanged", "current_number": current_number, "current_rarity": current_rarity}
        for candidate in _candidates(card["collectory_set"], expected_number, expected_rarity):
            try:
                number, rarity = _ocr(candidate)
            except Exception:
                continue
            if number == expected_number and rarity == expected_rarity:
                return card, {
                    "status": "matched",
                    "current_number": current_number,
                    "current_rarity": current_rarity,
                    "new_image_url": candidate,
                }
        return card, {"status": "unresolved", "current_number": current_number, "current_rarity": current_rarity}

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(one, card) for card in targets]
        for future in as_completed(futures):
            card, result = future.result()
            if result["status"] == "unchanged":
                report["unchanged"] += 1
            elif result["status"] == "matched":
                sb.table("cards").update({"image_url": result["new_image_url"]}).eq("id", card["id"]).execute()
                report["changed"].append({**card, **result})
            else:
                report["unresolved"].append({**card, **result})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "checked": report["checked"],
        "unchanged": report["unchanged"],
        "changed": len(report["changed"]),
        "unresolved": len(report["unresolved"]),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
