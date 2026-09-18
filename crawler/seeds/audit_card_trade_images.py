"""가격 대상 카드의 공식 이미지와 번개장터 매물 이미지를 읽기 전용으로 대조."""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kr_sets import KR_BY_CODE
from lib.bunjang_card_price import collect_bunjang_items
from lib.card_image_verify import CardImageVerifier, bunjang_listing_image_url
from lib.price_search import build_search_queries, is_raw_kr_listing
from utils.db import get_supabase

OUT = Path("_audit_out/card_trade_image_audit.json")


def _cards(sb) -> list[dict]:
    sets = sb.table("card_sets").select("id,set_code,name_kr").execute().data or []
    out: list[dict] = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    for meta in sets:
        if meta["set_code"] not in KR_BY_CODE:
            continue
        priced = (
            sb.table("prices_kr")
            .select("card_id")
            .gte("fetched_at", cutoff)
            .execute()
            .data
            or []
        )
        priced_ids = {int(row["card_id"]) for row in priced}
        rows = (
            sb.table("cards")
            .select("id,card_number,name_kr,rarity,image_url")
            .eq("set_id", meta["id"])
            .execute()
            .data
            or []
        )
        out.extend(
            {**card, "set_code": meta["set_code"], "set_name_kr": meta["name_kr"]}
            for card in rows
            if int(card["id"]) in priced_ids and card.get("image_url")
        )
    return out


def _audit_one(card: dict) -> list[dict]:
    meta = KR_BY_CODE[card["set_code"]]
    queries = build_search_queries(
        card["set_name_kr"],
        card.get("name_kr") or "",
        card.get("rarity") or "",
        card.get("card_number") or "",
        card["set_code"],
        slim=False,
    )
    items = collect_bunjang_items(queries[:3], n=30, early_stop_sold=5)
    title_items = [
        item
        for item in items
        if is_raw_kr_listing(
            str(item.get("name") or ""),
            card.get("name_kr") or "",
            card.get("rarity") or "",
            card.get("card_number") or "",
            card["set_code"],
            card["set_name_kr"],
        )
    ]
    number = str(card.get("card_number") or "").split("/", 1)[0]
    referer = (
        f"https://pokemoncard.co.kr/cards/detail/{meta.bs_code}{int(number):03d}"
        if meta.bs_code and number.isdigit()
        else ""
    )
    findings: list[dict] = []
    with CardImageVerifier(card["image_url"], referer) as verifier:
        if verifier._load_reference() is None:
            return []
        for item in title_items[:10]:
            if not bunjang_listing_image_url(item):
                continue
            if not verifier.matches(item):
                findings.append(
                    {
                        "card_id": card["id"],
                        "set": card["set_name_kr"],
                        "set_code": card["set_code"],
                        "card_number": card.get("card_number"),
                        "name_kr": card.get("name_kr"),
                        "rarity": card.get("rarity"),
                        "listing_title": item.get("name"),
                        "listing_pid": item.get("pid"),
                        "listing_image": bunjang_listing_image_url(item),
                        "official_image": card["image_url"],
                    }
                )
    return findings


def main() -> None:
    sb = get_supabase()
    cards = _cards(sb)
    findings: list[dict] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(_audit_one, card) for card in cards]
        for future in as_completed(futures):
            findings.extend(future.result())
    unique_cards = {item["card_id"] for item in findings}
    body = {
        "cards_checked": len(cards),
        "mismatched_listings": len(findings),
        "cards_with_mismatch": len(unique_cards),
        "sample": findings[:10],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(body, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
