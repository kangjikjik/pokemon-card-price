"""스톰에메랄다와 C/U/R을 제외한 카드 이미지의 읽기 전용 대조."""
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

OUT = Path("_audit_out/card_identity_all.json")
EXCLUDED_SET = "MG7"
EXCLUDED_RARITIES = {"C", "U", "R"}
TARGET_RARITIES = {
    "RR", "RRR", "AR", "CHR", "PR", "SR", "SAR", "HR", "UR", "MUR", "P"
}
RARITY_RE = re.compile(r"\b(RRR|MUR|SAR|CHR|PR|RR|SR|HR|UR|AR|P)\b", re.I)
NUMBER_RE = re.compile(r"\b(\d{1,3})\s*/\s*(\d{1,3})\b")


def _load_cards(sb, set_id: int) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        batch = (
            sb.table("cards")
            .select("id,card_number,name_kr,rarity,image_url")
            .eq("set_id", set_id)
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        start += 1000


def _image_url(url: str) -> str:
    return url + ("&" if "?" in url else "?") + "w=512"


def _norm(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", (value or "").casefold())


def _audit(card: dict) -> dict:
    result = {
        "card_id": card["id"],
        "name_kr": card.get("name_kr") or "",
        "card_number": card.get("card_number") or "",
        "rarity": card.get("rarity") or "",
        "image_url": card.get("image_url") or "",
    }
    try:
        response = httpx.get(
            _image_url(result["image_url"]),
            headers={"Referer": "https://pokemoncard.co.kr/"},
            timeout=30,
        )
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        width, height = image.size
        top_text = pytesseract.image_to_string(image.crop((0, 0, width, int(height * 0.24))), lang="kor+eng")
        bottom_text = pytesseract.image_to_string(image.crop((0, int(height * 0.78), width, height)), lang="kor+eng")
        text = f"{top_text}\n{bottom_text}"
        printed_number = next((f"{a}/{b}" for a, b in NUMBER_RE.findall(text)), "")
        printed_rarity_match = RARITY_RE.search(text)
        printed_rarity = printed_rarity_match.group(1).upper() if printed_rarity_match else ""
        name_match = bool(_norm(result["name_kr"]) and _norm(result["name_kr"]) in _norm(top_text))
        number_match = bool(printed_number and _norm(printed_number) == _norm(result["card_number"]))
        rarity_match = bool(printed_rarity and printed_rarity == result["rarity"].upper())
        issues = []
        if not name_match:
            issues.append("name_mismatch_or_ocr_unreadable")
        if not number_match:
            issues.append("card_number_mismatch_or_ocr_unreadable")
        if not rarity_match:
            issues.append("rarity_mismatch_or_ocr_unreadable")
        result.update({
            "status": "match" if not issues else "review",
            "printed_name_text": top_text.strip(),
            "printed_number": printed_number,
            "printed_rarity": printed_rarity,
            "issues": issues,
        })
    except Exception as exc:
        result.update({"status": "unverifiable", "reason": type(exc).__name__})
    return result


def main() -> None:
    sb = get_supabase()
    set_rows = sb.table("card_sets").select("id,set_code,name_kr").execute().data or []
    set_by_code = {row["set_code"]: row for row in set_rows}
    targets: list[dict] = []
    for meta in KR_SETS:
        if meta.code == EXCLUDED_SET or meta.code not in set_by_code:
            continue
        for card in _load_cards(sb, set_by_code[meta.code]["id"]):
            if card.get("rarity") not in TARGET_RARITIES or card.get("rarity") in EXCLUDED_RARITIES:
                continue
            targets.append({**card, "set_code": meta.code, "set": set_by_code[meta.code]["name_kr"]})

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(_audit, card) for card in targets]
        for future in as_completed(futures):
            results.append(future.result())
    body = {
        "scope": "all sets except MG7; RR+ and P; excluding C/U/R",
        "cards_checked": len(results),
        "matches": sum(r["status"] == "match" for r in results),
        "review": sum(r["status"] == "review" for r in results),
        "unverifiable": sum(r["status"] == "unverifiable" for r in results),
        "rarity_mismatches": sum("rarity_mismatch" in " ".join(r.get("issues", [])) for r in results),
        "number_mismatches": sum("card_number_mismatch" in " ".join(r.get("issues", [])) for r in results),
        "name_mismatches": sum("name_mismatch" in " ".join(r.get("issues", [])) for r in results),
        "cards": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: body[k] for k in body if k != "cards"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
