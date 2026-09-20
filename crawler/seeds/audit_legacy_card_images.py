"""2018-2022 발매 세트의 카드 이미지와 DB 카드 식별 정보 읽기 전용 대조."""
from __future__ import annotations

import io
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytesseract
from dotenv import load_dotenv
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
from utils.db import get_supabase

OUT = Path("_audit_out/legacy_card_image_identity_audit.json")
NUMBER_RE = re.compile(r"\b(\d{1,3})\s*/\s*(\d{1,3})\b")
RARITY_RE = re.compile(r"\b(RRR|MUR|SAR|CHR|PR|RR|SR|HR|UR|AR|CSR|SSR|PROMO|RRR)\b", re.I)


def load_all(sb, table: str, fields: str, **filters: object) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        query = sb.table(table).select(fields)
        for key, value in filters.items():
            query = query.eq(key, value)
        batch = query.range(start, start + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        start += 1000


def url_number_hint(url: str) -> str:
    """URL에 번호가 명시된 주요 이미지 호스트의 번호 힌트."""
    value = (url or "").split("?", 1)[0]
    path = urlparse(value).path
    match = re.search(r"(?:^|/)(\d{1,3})_(\d{1,3})(?:[A-Za-z_-]*\.(?:png|jpe?g|webp))$", path, re.I)
    if match:
        return f"{int(match.group(1))}/{int(match.group(2))}"
    match = re.search(r"(?:_|/)(\d{1,3})(?:_hires)?\.(?:png|jpe?g|webp)$", path, re.I)
    return f"{int(match.group(1))}/?" if match else ""


def audit(card: dict) -> dict:
    result = {
        **card,
        "image_url": card.get("image_url") or "",
        "url_host": urlparse(card.get("image_url") or "").netloc,
        "url_number_hint": url_number_hint(card.get("image_url") or ""),
        "status": "unverifiable",
        "issues": [],
    }
    url = result["image_url"]
    if not url:
        result["status"] = "no_image"
        return result
    try:
        response = httpx.get(url, timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        with Image.open(io.BytesIO(response.content)) as source:
            image = source.convert("RGB")
        width, height = image.size
        top = pytesseract.image_to_string(image.crop((0, 0, width, int(height * 0.26))), lang="kor+eng")
        bottom = pytesseract.image_to_string(image.crop((0, int(height * 0.75), width, height)), lang="kor+eng")
        text = f"{top}\n{bottom}"
        numbers = [f"{int(a)}/{int(b)}" for a, b in NUMBER_RE.findall(text)]
        printed_number = next((value for value in numbers if value == card.get("card_number")), numbers[0] if numbers else "")
        issues: list[str] = []
        # Only call this definite when OCR found a different explicit number.
        if numbers and card.get("card_number") not in numbers:
            issues.append("printed_number_mismatch")
        if result["url_number_hint"] and result["url_number_hint"] != card.get("card_number"):
            issues.append("url_number_mismatch")
        result.update({
            "status": "mismatch" if issues else ("match" if printed_number == card.get("card_number") else "review"),
            "printed_number": printed_number,
            "ocr_numbers": numbers,
            "printed_rarity": (RARITY_RE.search(text).group(1).upper() if RARITY_RE.search(text) else ""),
            "ocr_text": text.strip(),
            "issues": issues,
            "bytes": len(response.content),
            "dimensions": [width, height],
        })
    except Exception as exc:
        result.update({"status": "unverifiable", "reason": f"{type(exc).__name__}: {exc}"})
    return result


def main() -> None:
    sb = get_supabase()
    sets = load_all(sb, "card_sets", "id,set_code,name_kr,released_at")
    targets = [
        row for row in sets
        if row.get("released_at") and "2018-01-01" <= row["released_at"] <= "2022-12-31"
    ]
    cards: list[dict] = []
    for meta in targets:
        cards.extend(
            {**card, "set_code": meta["set_code"], "set_name": meta["name_kr"], "released_at": meta["released_at"]}
            for card in load_all(
                sb, "cards", "id,set_id,card_number,name_kr,rarity,image_url", set_id=meta["id"]
            )
            if (card.get("image_url") or "").strip()
        )
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(audit, card) for card in cards]
        for future in as_completed(futures):
            results.append(future.result())
    mismatches = [row for row in results if row["status"] == "mismatch"]
    body = {
        "scope": "all cards with image_url in sets released 2018-2022; read-only OCR and URL-number audit",
        "sets_checked": len(targets),
        "cards_with_images": len(cards),
        "matches": sum(row["status"] == "match" for row in results),
        "definite_mismatches": len(mismatches),
        "review": sum(row["status"] == "review" for row in results),
        "unverifiable": sum(row["status"] == "unverifiable" for row in results),
        "by_set": {},
        "mismatches": sorted(mismatches, key=lambda row: (row["set_name"], row.get("card_number") or "")),
        "non_korean_sources": sorted(
            [row for row in results if row["url_host"] not in {"cdn.collectory.cc", "cards.image.pokemonkorea.co.kr"}],
            key=lambda row: (row["set_name"], row.get("card_number") or ""),
        ),
    }
    for meta in targets:
        rows = [row for row in results if row["set_code"] == meta["set_code"]]
        body["by_set"][meta["set_code"]] = {
            "name": meta["name_kr"],
            "released_at": meta["released_at"],
            "cards_with_images": len(rows),
            "definite_mismatches": sum(row["status"] == "mismatch" for row in rows),
            "review": sum(row["status"] == "review" for row in rows),
            "unverifiable": sum(row["status"] == "unverifiable" for row in rows),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: body[key] for key in ("scope", "sets_checked", "cards_with_images", "matches", "definite_mismatches", "review", "unverifiable")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
