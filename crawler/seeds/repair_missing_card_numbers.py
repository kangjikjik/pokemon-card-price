"""카드번호가 비어 있는 카드의 공식 번호·이미지 복구."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()

from kr_sets import KR_SETS
from lib.pokemoncard_kr import BASE, HEADERS, goods_name_for_set, parse_detail
from utils.db import get_supabase

AJAX = f"{BASE}/v2/ajax2_dev2"
OUT = Path("_audit_out/missing_card_numbers_apply.json")


def _norm(value: str) -> str:
    return re.sub(r"[\s·・\-_.'’]", "", (value or "").casefold())


def _rows(payload: dict) -> list[dict]:
    result = payload.get("result") or {}
    return list(result.values()) if isinstance(result, dict) else list(result)


def _fetch_official(goods_name: str) -> list[dict]:
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        response = client.post(
            AJAX,
            data={
                "action": "get_more_cards",
                "limit": "0",
                "GoodsName": goods_name,
                "order": "ASC",
                "orderby": "CardNum",
            },
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            match = re.search(r"(\{[\s\S]*\})", response.text)
            payload = json.loads(match.group(1)) if match else {}

        candidates: list[dict] = []
        for row in _rows(payload):
            card_id = str(row.get("CardNum") or "").strip()
            if not card_id:
                continue
            detail_response = client.get(f"{BASE}/cards/detail/{card_id}")
            if detail_response.status_code != 200:
                continue
            detail_response.encoding = "utf-8"
            detail = parse_detail(detail_response.text)
            if not detail:
                continue
            candidates.append(
                {
                    "card_number": detail["printed"],
                    "name_kr": detail["name_kr"],
                    "rarity": detail["rarity"],
                    "image_url": detail["image_url"],
                }
            )
            time.sleep(0.04)
        return candidates


def _search_official_name(name_kr: str, bs_code: str) -> list[dict]:
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        response = client.post(
            AJAX,
            data={
                "action": "search_text_cards",
                "search_text": name_kr,
                "search_params": "cardname",
                "limit": "0",
            },
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            match = re.search(r"(\{[\s\S]*\})", response.text)
            payload = json.loads(match.group(1)) if match else {}

        result = payload.get("result") or {}
        rows = list(result.values()) if isinstance(result, dict) else list(result)
        candidates: list[dict] = []
        for row in rows:
            card_id = str(row.get("CardNum") or "").strip()
            if not card_id.startswith(bs_code):
                continue
            detail_response = client.get(f"{BASE}/cards/detail/{card_id}")
            if detail_response.status_code != 200:
                continue
            detail_response.encoding = "utf-8"
            detail = parse_detail(detail_response.text)
            if detail:
                candidates.append(
                    {
                        "card_number": detail["printed"],
                        "name_kr": detail["name_kr"],
                        "rarity": detail["rarity"],
                        "image_url": detail["image_url"],
                    }
                )
            time.sleep(0.04)
        return candidates


def _load_blank_cards(sb, set_id: int) -> list[dict]:
    return (
        sb.table("cards")
        .select("id,card_number,name_kr,name_jp,rarity,image_url")
        .eq("set_id", set_id)
        .or_("card_number.is.null,card_number.eq.")
        .execute()
        .data
        or []
    )


def main() -> None:
    sb = get_supabase()
    set_ids = {
        row["set_code"]: row["id"]
        for row in (sb.table("card_sets").select("id,set_code").execute().data or [])
    }
    report = {"checked": 0, "changed": 0, "ambiguous": [], "unmatched": [], "changes": []}

    for meta in KR_SETS:
        if meta.code.upper() == "MG7" or meta.code not in set_ids:
            continue
        cards = _load_blank_cards(sb, set_ids[meta.code])
        if not cards:
            continue
        goods = goods_name_for_set(meta.name_kr)
        if not goods:
            report["unmatched"].extend(
                {"set": meta.name_kr, "card_id": c["id"], "name_kr": c.get("name_kr"), "reason": "goods_not_found"}
                for c in cards
            )
            continue

        official = _fetch_official(goods)
        for card in cards:
            report["checked"] += 1
            name_key = _norm(card.get("name_kr") or "")
            matches = [x for x in official if _norm(x["name_kr"]) == name_key]
            if not matches and card.get("name_kr"):
                matches = _search_official_name(card["name_kr"], meta.bs_code or "")
            rarity = (card.get("rarity") or "").upper()
            rarity_matches = [x for x in matches if x["rarity"].upper() == rarity]
            if len(rarity_matches) == 1:
                matches = rarity_matches
            if len(matches) != 1:
                report["ambiguous" if matches else "unmatched"].append(
                    {
                        "set": meta.name_kr,
                        "card_id": card["id"],
                        "name_kr": card.get("name_kr"),
                        "rarity": rarity,
                        "candidates": matches,
                    }
                )
                continue

            match = matches[0]
            payload = {
                "card_number": match["card_number"],
                "name_kr": match["name_kr"],
                "image_url": match["image_url"],
            }
            sb.table("cards").update(payload).eq("id", card["id"]).execute()
            report["changed"] += 1
            report["changes"].append(
                {
                    "set": meta.name_kr,
                    "card_id": card["id"],
                    "old_name": card.get("name_kr"),
                    "new_name": match["name_kr"],
                    "new_card_number": match["card_number"],
                    "new_image_url": match["image_url"],
                }
            )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"확인 {report['checked']}장 / 수정 {report['changed']}장 / "
        f"모호 {len(report['ambiguous'])}장 / 미매칭 {len(report['unmatched'])}장"
    )


if __name__ == "__main__":
    main()
