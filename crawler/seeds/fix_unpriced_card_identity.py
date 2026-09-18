"""공식 카드 상세 페이지와 DB 카드의 이름·이미지를 1:1 대조하고 즉시 교정한다.

카드번호로 pokemoncard.co.kr 상세 페이지를 직접 조회하며, 상세 페이지에
표시된 카드번호가 DB 카드번호와 일치할 때만 name_kr/image_url을 갱신한다.
스톰에메랄다는 공식 카드 이미지가 완성되지 않아 제외한다.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import httpx
import pytesseract
from dotenv import load_dotenv
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

from kr_sets import KR_SETS
from lib.pokemoncard_kr import AJAX, BASE, HEADERS, parse_detail
from utils.db import get_supabase

OUT_DIR = Path("_audit_out")
SKIP_CODES = {"MG7"}
NUMBER_RE = re.compile(r"^\s*(\d+)(?:\s*/\s*(\d+))?")


def _number(card_number: str) -> tuple[int, int | None] | None:
    m = NUMBER_RE.match(card_number or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)) if m.group(2) else None


def _norm_name(value: str) -> str:
    return re.sub(r"[\s·・\-_.]", "", (value or "").casefold())


def _feature_image(row: dict) -> str:
    feature = str(row.get("feature_image") or "").strip().lstrip("/")
    if not feature.startswith("wmimages/"):
        return ""
    return f"https://cards.image.pokemonkorea.co.kr/data/{feature.split('?')[0]}"


def _ocr_card_number(image_url: str) -> int | None:
    if not image_url or not image_url.startswith("http"):
        return None
    try:
        response = httpx.get(image_url, headers=HEADERS, timeout=25, follow_redirects=True)
        if response.status_code >= 400:
            return None
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        text = pytesseract.image_to_string(image, lang="kor+eng", config="--psm 6")
        numbers = re.findall(r"(?<!\d)(\d{1,3})\s*/\s*\d{1,3}(?!\d)", text)
        return int(numbers[-1]) if numbers else None
    except Exception:
        return None


def _same_printed(db_number: str, official_number: str) -> bool:
    db = _number(db_number)
    off = _number(official_number)
    if not db or not off or db[0] != off[0]:
        return False
    # 공식 사이트의 재수록·시크릿 카드 표기는 분모가 DB와 다를 수 있다.
    # 카드 식별과 이미지 검증에는 앞번호가 기준이므로 분모 차이는 허용한다.
    return True


def _bs_variants(bs_code: str) -> list[str]:
    raw = (bs_code or "").strip()
    values = [raw]
    if raw.lower().endswith("-kr"):
        values.append(raw[:-3])
    return [v for i, v in enumerate(values) if v and v not in values[:i]]


def _fetch_one(bs_code: str, card: dict) -> dict:
    parsed = _number(card.get("card_number") or "")
    if not parsed:
        return {"card": card, "status": "bad_db_number"}
    num = parsed[0]
    for bs in _bs_variants(bs_code):
        detail_id = f"{bs}{num:03d}"
        url = f"{BASE}/cards/detail/{detail_id}"
        try:
            r = httpx.get(url, headers=HEADERS, timeout=25, follow_redirects=True)
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
            continue
        if r.status_code != 200:
            last = f"HTTP {r.status_code}"
            continue
        r.encoding = "utf-8"
        detail = parse_detail(r.text)
        if not detail:
            last = "detail_parse_failed"
            continue
        if not _same_printed(card.get("card_number") or "", detail["printed"]):
            last = f"printed_mismatch:{detail['printed']}"
            continue
        return {
            "card": card,
            "status": "matched",
            "official": detail,
            "detail_id": detail_id,
            "detail_url": url,
        }
    # 일부 시크릿 카드는 번호 기반 상세 URL이 빈 HTML을 반환한다.
    # 공식 검색 API에서 같은 세트 코드와 카드번호를 다시 찾는다.
    try:
        rows: list[dict] = []
        page = "0"
        seen_pages: set[str] = set()
        for _ in range(20):
            if page in seen_pages:
                break
            seen_pages.add(page)
            r = httpx.post(
                AJAX,
                headers=HEADERS,
                data={
                    "action": "search_text_cards",
                    "search_text": str(num),
                    "search_params": "all",
                    "limit": page,
                },
                timeout=25,
            )
            obj = r.json()
            result = obj.get("result") or {}
            rows.extend(list(result.values()) if isinstance(result, dict) else list(result))
            next_page = str(obj.get("limit") or "")
            if not next_page or next_page == page or not result:
                break
            page = next_page
        for row in rows:
            candidate_id = str(row.get("CardNum") or "").strip()
            if not candidate_id.startswith(bs_code) or not candidate_id.rstrip().endswith(f"{num:03d}"):
                continue
            candidate_url = f"{BASE}/cards/detail/{candidate_id}"
            candidate = httpx.get(candidate_url, headers=HEADERS, timeout=25, follow_redirects=True)
            image_url = _feature_image(row)
            if image_url and candidate.status_code != 200:
                return {
                    "card": card,
                    "status": "matched",
                    "official": {
                        "name_kr": card.get("name_kr") or "",
                        "printed": card.get("card_number") or "",
                        "image_url": image_url,
                    },
                    "detail_id": candidate_id,
                    "detail_url": candidate_url,
                }
            if candidate.status_code != 200:
                continue
            candidate.encoding = "utf-8"
            detail = parse_detail(candidate.text)
            if not detail and image_url:
                return {
                    "card": card,
                    "status": "matched",
                    "official": {
                        "name_kr": card.get("name_kr") or "",
                        "printed": card.get("card_number") or "",
                        "image_url": image_url,
                    },
                    "detail_id": candidate_id,
                    "detail_url": candidate_url,
                }
            if detail and _same_printed(card.get("card_number") or "", detail["printed"]):
                return {
                    "card": card,
                    "status": "matched",
                    "official": detail,
                    "detail_id": candidate_id,
                    "detail_url": candidate_url,
                }
    except Exception:
        pass
    # 카드번호 자체가 잘못된 경우에는 DB 이름으로 공식 후보를 찾는다.
    name = (card.get("name_kr") or "").strip()
    if name:
        try:
            page = "0"
            seen_pages: set[str] = set()
            while page not in seen_pages and len(seen_pages) < 20:
                seen_pages.add(page)
                r = httpx.post(
                    AJAX,
                    headers=HEADERS,
                    data={
                        "action": "search_text_cards",
                        "search_text": name,
                        "search_params": "all",
                        "limit": page,
                    },
                    timeout=25,
                )
                obj = r.json()
                result = obj.get("result") or {}
                rows = list(result.values()) if isinstance(result, dict) else list(result)
                for row in rows:
                    candidate_id = str(row.get("CardNum") or "").strip()
                    if not candidate_id.startswith(bs_code):
                        continue
                    candidate_url = f"{BASE}/cards/detail/{candidate_id}"
                    candidate = httpx.get(
                        candidate_url, headers=HEADERS, timeout=25, follow_redirects=True
                    )
                    if candidate.status_code != 200:
                        continue
                    candidate.encoding = "utf-8"
                    detail = parse_detail(candidate.text)
                    if detail and _norm_name(detail["name_kr"]) == _norm_name(name):
                        return {
                            "card": card,
                            "status": "matched",
                            "official": detail,
                            "detail_id": candidate_id,
                            "detail_url": candidate_url,
                        }
                next_page = str(obj.get("limit") or "")
                if not next_page or next_page == page or not result:
                    break
                page = next_page
        except Exception:
            pass
    # 최후 fallback: 현재 카드 이미지에서 인쇄번호를 OCR로 읽는다.
    ocr_number = _ocr_card_number(card.get("image_url") or "")
    if ocr_number and ocr_number != num:
        return _fetch_one(bs_code, {**card, "card_number": f"{ocr_number}/{ocr_number}"})
    return {"card": card, "status": "not_found", "reason": locals().get("last", "")}


def _load_cards(sb, set_id: int) -> list[dict]:
    out: list[dict] = []
    start = 0
    while True:
        rows = (
            sb.table("cards")
            .select("id,card_number,name_kr,name_jp,rarity,image_url")
            .eq("set_id", set_id)
            .range(start, start + 999)
            .execute()
            .data
            or []
        )
        out.extend(rows)
        if len(rows) < 1000:
            # 1단계에서 별도로 남긴 번호 공백 6장은 이번 번호 기반 대조에서 제외한다.
            return [card for card in out if (card.get("card_number") or "").strip()]
        start += 1000


def main() -> None:
    sb = get_supabase()
    set_rows = sb.table("card_sets").select("id,set_code").execute().data or []
    set_ids = {row["set_code"]: row["id"] for row in set_rows}

    changes: list[dict] = []
    unmatched: list[dict] = []
    checked = 0

    for meta in KR_SETS:
        if meta.code.upper() in SKIP_CODES or not meta.bs_code:
            continue
        set_id = set_ids.get(meta.code)
        if not set_id:
            continue
        cards = _load_cards(sb, set_id)
        if not cards:
            continue
        print(f"[{meta.name_kr}] {len(cards)}장 공식 상세 대조")

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(_fetch_one, meta.bs_code, card) for card in cards]
            results = [future.result() for future in as_completed(futures)]

        matched = 0
        set_changes = 0
        for result in results:
            card = result["card"]
            checked += 1
            if result["status"] != "matched":
                unmatched.append(
                    {
                        "set": meta.name_kr,
                        "card_id": card["id"],
                        "card_number": card.get("card_number"),
                        "status": result["status"],
                        "reason": result.get("reason", ""),
                    }
                )
                continue

            matched += 1
            official = result["official"]
            old_name = (card.get("name_kr") or "").strip()
            old_img = (card.get("image_url") or "").split("?")[0].strip()
            new_name = official["name_kr"].strip()
            new_img = official["image_url"].split("?")[0].strip()
            payload: dict[str, str] = {}
            if new_name and old_name != new_name:
                payload["name_kr"] = new_name
            if new_img and old_img != new_img:
                payload["image_url"] = new_img
            if not payload:
                continue

            change = {
                "set": meta.name_kr,
                "card_id": card["id"],
                "card_number": card.get("card_number"),
                "rarity": card.get("rarity"),
                "detail_url": result["detail_url"],
                "old_name": old_name,
                "new_name": new_name,
                "old_image_url": old_img,
                "new_image_url": new_img,
                "payload": payload,
            }
            # 변경 전 값을 먼저 메모리에 기록하고, 공식 상세 검증을 통과한 행만 갱신한다.
            sb.table("cards").update(payload).eq("id", card["id"]).execute()
            changes.append(change)
            set_changes += 1

        print(f"  공식 매칭 {matched}/{len(cards)}, 수정 {set_changes}장")
        time.sleep(0.2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = OUT_DIR / f"official_identity_apply_{stamp}.json"
    latest = OUT_DIR / "official_identity_apply_latest.json"
    body = {
        "checked": checked,
        "changed": len(changes),
        "unmatched": len(unmatched),
        "changes": changes,
        "unmatched_rows": unmatched,
    }
    text = json.dumps(body, ensure_ascii=False, indent=2)
    report.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(f"\n전체 대조 {checked}장 / 수정 {len(changes)}장 / 공식 미매칭 {len(unmatched)}장")
    print(f"백업·적용 기록: {report}")


if __name__ == "__main__":
    main()
