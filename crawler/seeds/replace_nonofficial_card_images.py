"""비공식 카드 이미지만 공식 pokemoncard.co.kr 이미지 URL로 교체한다."""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

from kr_sets import KR_SETS
from lib.pokemoncard_kr import AJAX, BASE, HEADERS, parse_detail
from utils.db import get_supabase

OUT = Path("_audit_out/nonofficial_card_image_replacement.json")
OFFICIAL_HOST = "cards.image.pokemonkorea.co.kr"


def _number(value: str) -> int | None:
    try:
        return int((value or "").split("/", 1)[0].strip())
    except (TypeError, ValueError):
        return None


def _feature_image(row: dict) -> str:
    feature = str(row.get("feature_image") or "").strip().lstrip("/")
    if not feature.startswith("wmimages/"):
        return ""
    return f"https://{OFFICIAL_HOST}/data/{feature.split('?')[0]}"


def _search_rows(query: str) -> list[dict]:
    rows: list[dict] = []
    page = "0"
    seen: set[str] = set()
    with httpx.Client(headers=HEADERS, timeout=25, follow_redirects=True) as client:
        for _ in range(20):
            if page in seen:
                break
            seen.add(page)
            response = client.post(
                AJAX,
                data={
                    "action": "search_text_cards",
                    "search_text": query,
                    "search_params": "all",
                    "limit": page,
                },
            )
            payload = response.json()
            result = payload.get("result") or {}
            batch = list(result.values()) if isinstance(result, dict) else list(result)
            rows.extend(batch)
            next_page = str(payload.get("limit") or "")
            if not batch or not next_page or next_page == page:
                break
            page = next_page
    return rows


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


def _fetch_official(meta, card: dict) -> dict:
    number = _number(card.get("card_number") or "")
    if number is None or not meta.bs_code:
        name = (card.get("name_kr") or "").strip()
        if name and meta.bs_code:
            candidates = [
                row
                for row in _search_rows(name)
                if str(row.get("CardNum") or "").strip().startswith(meta.bs_code)
                and _feature_image(row)
            ]
            if len(candidates) == 1:
                return {"status": "matched", "image_url": _feature_image(candidates[0]), "url": ""}
        return {"status": "unresolved", "reason": "missing_card_number"}
    url = f"{BASE}/cards/detail/{meta.bs_code}{number:03d}"
    try:
        response = httpx.get(url, headers=HEADERS, timeout=25, follow_redirects=True)
        if response.status_code != 200:
            detail = None
        else:
            response.encoding = "utf-8"
            detail = parse_detail(response.text)
        if detail and detail["number"] == number and OFFICIAL_HOST in detail["image_url"]:
            return {"status": "matched", "image_url": detail["image_url"], "url": url}
    except Exception as exc:
        detail = None

    # 상세 HTML 파싱 실패 시에도 공식 검색 결과의 세트·번호·이미지를 사용한다.
    candidates = [
        row
        for row in _search_rows(str(number))
        if str(row.get("CardNum") or "").strip().startswith(meta.bs_code)
        and str(row.get("CardNum") or "").strip().rstrip().endswith(f"{number:03d}")
        and _feature_image(row)
    ]
    if len(candidates) == 1:
        return {"status": "matched", "image_url": _feature_image(candidates[0]), "url": url}

    return {"status": "unresolved", "reason": "official_search_no_unique_match"}


def main() -> None:
    sb = get_supabase()
    set_ids = {
        row["set_code"]: row["id"]
        for row in (sb.table("card_sets").select("id,set_code").execute().data or [])
    }
    targets: list[tuple[object, dict]] = []
    for meta in KR_SETS:
        if meta.code in set_ids and meta.bs_code:
            targets.extend((meta, card) for card in _load_cards(sb, set_ids[meta.code]))

    report = {"checked": 0, "changed": 0, "already_official": 0, "unresolved": [], "changes": []}

    def one(target: tuple[object, dict]) -> tuple[object, dict, dict]:
        meta, card = target
        if OFFICIAL_HOST in (card.get("image_url") or ""):
            return meta, card, {"status": "already_official"}
        return meta, card, _fetch_official(meta, card)

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(one, target) for target in targets]
        for future in as_completed(futures):
            meta, card, result = future.result()
            report["checked"] += 1
            if result["status"] == "already_official":
                report["already_official"] += 1
                continue
            if result["status"] != "matched":
                report["unresolved"].append(
                    {
                        "set": meta.name_kr,
                        "set_code": meta.code,
                        "card_id": card["id"],
                        "card_number": card.get("card_number"),
                        "name_kr": card.get("name_kr"),
                        "rarity": card.get("rarity"),
                        "old_image_url": card.get("image_url") or "",
                        "reason": result.get("reason", ""),
                    }
                )
                continue
            old_url = card.get("image_url") or ""
            new_url = result["image_url"]
            if old_url == new_url:
                continue
            sb.table("cards").update({"image_url": new_url}).eq("id", card["id"]).execute()
            report["changed"] += 1
            report["changes"].append(
                {
                    "set": meta.name_kr,
                    "set_code": meta.code,
                    "card_id": card["id"],
                    "card_number": card.get("card_number"),
                    "name_kr": card.get("name_kr"),
                    "rarity": card.get("rarity"),
                    "old_image_url": old_url,
                    "new_image_url": new_url,
                }
            )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"확인 {report['checked']}장 / 이미 공식 {report['already_official']}장 / "
        f"교체 {report['changed']}장 / 미확정 {len(report['unresolved'])}장"
    )


if __name__ == "__main__":
    main()
