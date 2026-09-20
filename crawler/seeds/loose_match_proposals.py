"""생성: loose-match proposals for problems from dryrun_all_cards_changes.json

Heuristic:
 - Try goods map fetch (all cards for set) and match by printed number.
 - Fallback: call /v2/ajax2_dev2?action=search_text_cards with search_text equal to
   printed number and name tokens, parse results and pick candidates where CardNum endswith printed number.
 - Output proposals JSON for user review (no DB writes).
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

from kr_sets import KR_SETS
from lib.pokemoncard_kr import goods_name_for_set

AJAX = "https://pokemoncard.co.kr/v2/ajax2_dev2"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://pokemoncard.co.kr/cards"}

P_JSON = Path("_audit_out/dryrun_all_cards_changes.json")
OUT = Path("_audit_out/loose_match_proposals.json")

def fetch_all_official_cards(goods_name: str) -> dict[int, dict]:
    c = httpx.Client(headers=HEADERS, timeout=30)
    try:
        r = c.post(AJAX, data={"action":"get_more_cards","limit":"0","GoodsName":goods_name,"order":"ASC","orderby":"CardNum"})
        txt = r.text
        try:
            obj = r.json()
        except Exception:
            # try to extract JSON blob
            m = re.search(r'(\{[\\s\\S]*\\})', txt)
            obj = json.loads(m.group(1)) if m else {}
        res = obj.get("result") or {}
        rows = list(res.values()) if isinstance(res, dict) else list(res)
        out = {}
        for row in rows:
            cardnum = str(row.get("CardNum") or "")
            m = re.search(r"(\d{1,4})$", cardnum)
            if not m:
                continue
            num = int(m.group(1))
            name = (row.get("CardName") or row.get("title") or "").strip()
            feat = (row.get("feature_image") or "").lstrip("/")
            img = f"https://cards.image.pokemonkorea.co.kr/data/{feat}".split("?")[0] if feat else ""
            out[num] = {"name_kr": name, "image_url": img, "cardnum_full": cardnum}
        return out
    finally:
        c.close()

def search_text_cards(q: str) -> list[dict]:
    c = httpx.Client(headers=HEADERS, timeout=20)
    try:
        r = c.post(AJAX, data={"action":"search_text_cards","search_text":q,"limit":"0","search_params":"all"})
        try:
            obj = r.json()
        except Exception:
            txt = r.text
            m = re.search(r'(\{[\\s\\S]*\\})', txt)
            obj = json.loads(m.group(1)) if m else {}
        res = obj.get("result") or {}
        rows = list(res.values()) if isinstance(res, dict) else list(res)
        return rows
    finally:
        c.close()

def find_set_by_name(name_kr: str):
    for s in KR_SETS:
        if s.name_kr == name_kr or name_kr in s.name_kr:
            return s
    return None

def main():
    if not P_JSON.exists():
        print("dryrun file missing:", P_JSON)
        return
    data = json.loads(P_JSON.read_text(encoding="utf-8"))
    probs = data.get("problems", [])
    proposals = []
    seen = set()
    for p in probs:
        # parse "SETNAME NNN/..." or skip product-matching problems
        if "공식 제품명 매칭 없음" in p:
            continue
        m = re.match(r"^(.*?)\\s+(\\d{1,4}(?:/\\d{1,4})?)[:\\s]", p)
        if not m:
            continue
        set_name = m.group(1).strip()
        printed = m.group(2).strip()
        printed_num = int(printed.split("/")[0])
        key = f"{set_name}|{printed}"
        if key in seen:
            continue
        seen.add(key)
        s = find_set_by_name(set_name)
        goods = goods_name_for_set(s.name_kr) if s else None
        candidate = None
        if goods:
            offmap = fetch_all_official_cards(goods)
            candidate = offmap.get(printed_num)
        if not candidate:
            # try search by printed number
            rows = search_text_cards(str(printed_num))
            for r in rows:
                cardnum = str(r.get("CardNum") or "")
                if cardnum.endswith(str(printed_num)):
                    feat = (r.get("feature_image") or "").lstrip("/")
                    img = f"https://cards.image.pokemonkorea.co.kr/data/{feat}".split("?")[0] if feat else ""
                    candidate = {"name_kr": (r.get("CardName") or "").strip(), "image_url": img, "cardnum_full": cardnum}
                    break
            # try tokens from set_name
            if not candidate and s:
                tokens = [t for t in s.name_kr.split() if len(t) > 2][:3]
                for t in tokens:
                    rows = search_text_cards(t)
                    for r in rows:
                        cardnum = str(r.get("CardNum") or "")
                        feat = (r.get("feature_image") or "").lstrip("/")
                        img = f"https://cards.image.pokemonkorea.co.kr/data/{feat}".split("?")[0] if feat else ""
                        candidate = {"name_kr": (r.get("CardName") or "").strip(), "image_url": img, "cardnum_full": cardnum}
                        break
                    if candidate:
                        break
        proposals.append({"set": set_name, "printed": printed, "candidate": candidate})
        time.sleep(0.08)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"proposals": proposals, "count": len(proposals)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT, "count", len(proposals))

if __name__ == "__main__":
    main()

