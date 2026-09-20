"""드라이런: 스톰에메랄다 제외한 전체 팩의 '시세 미등록' 카드 중
공식(pokemoncard.co.kr) 이미지/한글명과 DB가 다른 항목을 찾고 제안 생성."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import time

import httpx
from dotenv import load_dotenv

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

from utils.db import get_supabase
from kr_sets import KR_SETS
from lib.pokemoncard_kr import goods_name_for_set
from lib.trainer_item_cards import is_trainer_or_item_card, card_number_int

AJAX = "https://pokemoncard.co.kr/v2/ajax2_dev2"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://pokemoncard.co.kr/cards"}

def fetch_all_official_cards(goods_name: str) -> dict[int, dict]:
    """GoodsName으로 AJAX 호출해 카드 목록(인쇄번호-> {name_kr,image_url})을 반환."""
    c = httpx.Client(headers=HEADERS, timeout=30)
    try:
        r = c.post(
            AJAX,
            data={"action": "get_more_cards", "limit": "0", "GoodsName": goods_name, "order": "ASC", "orderby": "CardNum"},
        )
        r.raise_for_status()
        txt = r.text
        obj = None
        try:
            obj = r.json()
        except Exception:
            # sometimes the response contains HTML warnings before/after JSON
            m = re.search(r'({\\s*\"status\"[\\s\\S]*})', txt)
            if not m:
                m = re.search(r'(\\{[\\s\\S]*\\})', txt)
            if m:
                try:
                    obj = json.loads(m.group(1))
                except Exception:
                    obj = {}
            else:
                obj = {}
        res = obj.get("result") or {}
        rows = list(res.values()) if isinstance(res, dict) else list(res)
        out: dict[int, dict] = {}
        for row in rows:
            cardnum = str(row.get("CardNum") or "")
            # printed number: last 3 digits of CardNum if typical BS...NNN
            m = re.search(r"(\\d{1,4})$", cardnum)
            if not m:
                continue
            num = int(m.group(1))
            name = (row.get("CardName") or row.get("title") or "").strip()
            feat = (row.get("feature_image") or "").lstrip("/")
            if feat:
                img = f"https://cards.image.pokemonkorea.co.kr/data/{feat}".split("?")[0]
            else:
                img = ""
            out[num] = {"name_kr": name, "image_url": img}
        return out
    finally:
        c.close()


def main() -> None:
    sb = get_supabase()
    results: list[dict] = []
    problems: list[str] = []
    for s in KR_SETS:
        if s.code.upper() == "MG7":
            continue
        goods = goods_name_for_set(s.name_kr)
        if not goods:
            problems.append(f"{s.name_kr}: 공식 제품명 매칭 없음")
            continue
        print(f"[{s.name_kr}] goods={goods!r}")
        official_map = fetch_all_official_cards(goods)
        # load DB cards for set
        row = sb.table("card_sets").select("id").eq("set_code", s.code).single().execute().data
        if not row:
            problems.append(f"{s.name_kr}: DB 세트 없음")
            continue
        set_id = row["id"]
        cards = (
            sb.table("cards")
            .select("id,card_number,name_kr,name_jp,rarity,image_url")
            .eq("set_id", set_id)
            .execute()
            .data
            or []
        )
        for c in cards:
            cid = c["id"]
            # check price existence
            price_rows = (
                sb.table("prices_kr").select("price_krw").eq("card_id", cid).gt("price_krw", 0).limit(1).execute().data
            ) or []
            if price_rows:
                continue  # has price, skip
            # no price -> candidate
            num = card_number_int(c.get("card_number") or "")
            if num is None:
                # skip if no number
                continue
            off = official_map.get(num)
            if not off:
                problems.append(f"{s.name_kr} {c.get('card_number')}: 공식 카드 미발견")
                continue
            db_name = (c.get("name_kr") or "").strip()
            db_img = (c.get("image_url") or "").split("?")[0]
            off_name = off.get("name_kr") or ""
            off_img = (off.get("image_url") or "").split("?")[0]
            diff_name = db_name != off_name
            diff_img = db_img != off_img and off_img != ""
            if diff_name or diff_img:
                results.append(
                    {
                        "set": s.name_kr,
                        "card_id": cid,
                        "card_number": c.get("card_number"),
                        "db_name": db_name,
                        "off_name": off_name,
                        "db_img": db_img,
                        "off_img": off_img,
                        "diff_name": diff_name,
                        "diff_img": diff_img,
                    }
                )
        # be gentle
        time.sleep(0.12)

    outp = Path("_audit_out/dryrun_all_cards_changes.json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, "w", encoding="utf-8") as f:
        json.dump({"proposals": results, "problems": problems, "count": len(results)}, f, ensure_ascii=False, indent=2)
    print("written", outp, "count", len(results))


if __name__ == "__main__":
    main()

