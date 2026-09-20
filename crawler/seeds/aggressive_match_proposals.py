"""Aggressive automatic matching for '공식 카드 미발견' problems.

Tries multiple strategies (goods list, pack page, AJAX text search) to find candidates.
Writes proposals to _audit_out/aggressive_proposals.json (no DB writes).
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

SRC = Path("_audit_out/dryrun_all_cards_changes.json")
OUT = Path("_audit_out/aggressive_proposals.json")

def fetch_official_map_by_goods(goods_name: str) -> dict[int, dict]:
    """Fetch cards via AJAX get_more_cards and map by printed number."""
    c = httpx.Client(headers=HEADERS, timeout=30)
    try:
        r = c.post(AJAX, data={"action":"get_more_cards","limit":"0","GoodsName":goods_name,"orderby":"CardNum","order":"ASC"})
        txt = r.text
        try:
            obj = r.json()
        except Exception:
            # extract JSON-like blob
            m = re.search(r'(\{[\s\S]*\})', txt)
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
            name = (row.get("CardName") or "").strip()
            feat = (row.get("feature_image") or "").lstrip("/")
            img = f"https://cards.image.pokemonkorea.co.kr/data/{feat}".split("?")[0] if feat else ""
            out[num] = {"name_kr": name, "image_url": img, "cardnum_full": cardnum}
        return out
    finally:
        c.close()

def fetch_pack_page_by_bs(bs_code: str) -> list[dict]:
    """Fetch /cards?pack=BS... HTML and parse card entries."""
    url = f"https://pokemoncard.co.kr/cards?pack={bs_code}"
    r = httpx.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return []
    html = r.text
    # find card hrefs and image srcs under card_wrap div
    items = []
    for m in re.finditer(r'<a href="(/cards/detail/[^"]+)".*?<img src="([^"]+)"', html, re.S):
        href = m.group(1)
        img = m.group(2).split("?")[0]
        # try extract printed num from href or img
        mn = re.search(r'(\d{1,4})', href)
        num = int(mn.group(1)) if mn else None
        items.append({"href": href, "img": img, "num": num})
    return items

def ajax_search_text(q: str) -> list[dict]:
    c = httpx.Client(headers=HEADERS, timeout=20)
    try:
        r = c.post(AJAX, data={"action":"search_text_cards","search_text":q,"limit":"0","search_params":"all"})
        txt = r.text
        try:
            obj = r.json()
        except Exception:
            m = re.search(r'(\{[\s\S]*\})', txt)
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
    if not SRC.exists():
        print("dryrun source missing", SRC)
        return
    data = json.loads(SRC.read_text(encoding="utf-8"))
    probs = data.get("problems", [])
    proposals = []
    for p in probs:
        if "공식 제품명 매칭 없음" in p:
            # skip set-level product missing
            continue
        m = re.match(r"^(.*?)\s+(\d{1,4}(?:/\d{1,4})?)", p)
        if not m:
            continue
        set_name = m.group(1).strip()
        printed = m.group(2).strip()
        printed_num = int(printed.split("/")[0])
        s = find_set_by_name(set_name)
        candidate = None
        # Try goods map
        if s:
            goods = goods_name_for_set(s.name_kr)
            if goods:
                offmap = fetch_official_map_by_goods(goods)
                candidate = offmap.get(printed_num)
        # Try pack bs_code page
        if not candidate and s and getattr(s, "bs_code", None):
            items = fetch_pack_page_by_bs(s.bs_code)
            for it in items:
                if it.get("num") == printed_num or str(printed_num) in it.get("href",""):
                    candidate = {"name_kr": "", "image_url": it.get("img"), "cardnum_full": it.get("href")}
                    break
        # Try AJAX search by printed number
        if not candidate:
            rows = ajax_search_text(str(printed_num))
            for r in rows:
                cardnum = str(r.get("CardNum") or "")
                if cardnum.endswith(str(printed_num)):
                    feat = (r.get("feature_image") or "").lstrip("/")
                    img = f"https://cards.image.pokemonkorea.co.kr/data/{feat}".split("?")[0] if feat else ""
                    candidate = {"name_kr": (r.get("CardName") or "").strip(), "image_url": img, "cardnum_full": cardnum}
                    break
        # Tokened search fallback
        if not candidate and s:
            tokens = [t for t in s.name_kr.split() if len(t) > 2][:3]
            for t in tokens:
                rows = ajax_search_text(t)
                if rows:
                    r = rows[0]
                    feat = (r.get("feature_image") or "").lstrip("/")
                    img = f"https://cards.image.pokemonkorea.co.kr/data/{feat}".split("?")[0] if feat else ""
                    candidate = {"name_kr": (r.get("CardName") or "").strip(), "image_url": img, "cardnum_full": r.get("CardNum")}
                    break
        proposals.append({"set": set_name, "printed": printed, "candidate": candidate})
        time.sleep(0.08)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"proposals": proposals, "count": len(proposals)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT, "count", len(proposals))

if __name__ == "__main__":
    main()

