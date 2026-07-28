"""유유테이 일본판 싱글 판매가 수집."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from urllib.parse import quote

import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REQUEST_DELAY_SEC = 2.0
RETRY_WAIT_SEC = (30, 60, 120)

# KR set_code → 유유테이 収録弾 vers[]
YUYU_VERS: dict[str, str] = {
    "MG6": "m05",
    "MG5a": "m04",
    "MG5": "m03",
    "MG4a": "m02a",
    "MG4": "m02",
    "MG3a": "m01s",
    "MG3": "m01l",
    "MG2a": "sv11w",
    "MG2": "sv11b",
    "MG1b": "sv10",
    "MG1a": "sv09a",
    "SV8a": "sv09",
    "SV8": "sv08a",
    "SV7": "sv08",
    "SV6a": "sv07a",
    "SV6": "sv07",
    "SV5a": "sv06a",
    "SV5K": "sv06",
    "SV5M": "sv05a",
    "SV4x": "sv05m",
    "SV4": "sv05k",
    "SV4a": "sv04a",
    "SV4K": "sv04k",
    "SV4M": "sv04m",
    "SV3a": "sv03a",
    "SV3": "sv03",
    "SV2a": "sv02a",
    "SV2D": "sv02d",
    "SV2P": "sv02p",
    "SV1a": "sv01a",
    "SV1V": "sv01v",
    "SV1S": "sv01s",
    "S12a": "s12a",
    # S/SM era — KR↔JP 코드 불일치 보정
    "S12": "s12",
    "S11a": "s11a",
    "S11": "s11",
    "S10b": "s10a",
    "S10a": "s10b",
    "S9a": "s10d",
    "S9": "s10p",
    "S8": "s09a",
    "S8a": "s09",
    "S8b": "s08b",
    "S7F": "s08",
    "CEL": "s08a",
    "S7R": "s07r",
    "S7D": "s07d",
    "S6H": "s06a",
    "S6G": "s06k",
    "S6L": "s06h",
    "S5F": "s05a",
    "S5S": "s05i",
    "S5P": "s05r",
    "S4SV": "s04a",
    "S4B": "s04",
    "S3H": "s03a",
    "S3Z": "s03",
    "S2R": "s02a",
    "S2": "s02",
    "S1a": "s01a",
    "S1W": "s01w",
    "S1H": "s01h",
    "SM12a": "sm12a",
    "SM12": "sm12",
    "SM11b": "sm11b",
    "SM11a": "sm11",
    "SM10": "sm10",
    "SM9": "sm09a",
    "SM9a": "sm09",
    "SM8b": "sm08b",
    "SM8": "sm07a",   # KR 플라스마 스파크 = JP SM7a 迅雷スパーク
    "SM7": "sm08",    # KR 버스트임팩트 = JP SM8 超爆インパクト
    "SM6b": "sm07",
    "SM6a": "sm06b",
    "SM6": "sm06a",
    "SM5+": "sm06",
    "SM5": "sm05plus",
    "SM4+": "sm05m",
    "SM4": "sm05s",
}

RARE_FILTERS = ("", "RR", "AR", "SR", "SAR", "MUR", "UR", "HR", "ACE", "CSR", "PR")


@dataclass(frozen=True)
class YuyuListing:
    card_number: str
    rarity: str
    name_jp: str
    price_jpy: int


def _card_block_re(vers: str) -> re.Pattern[str]:
    v = re.escape(vers)
    return re.compile(
        rf'href="https://yuyu-tei\.jp/sell/poc/card/{v}/\d+"\s*>.*?'
        r'alt="\s*(\d+/\d+)\s+([A-Z+]+)\s+([^"]+)".*?'
        r'<strong[^>]*>\s*([\d,]+)\s*円',
        re.DOTALL,
    )


def normalize_card_number(num: str) -> str:
    n = re.sub(r"\s+", "", (num or "").strip())
    if "/" not in n:
        return n.lstrip("0") or n
    left, right = n.split("/", 1)
    try:
        return f"{int(left)}/{right}"
    except ValueError:
        return n


def card_numbers_match(db_num: str, yuyu_num: str) -> bool:
    db = normalize_card_number(db_num)
    yu = normalize_card_number(yuyu_num)
    if db == yu:
        return True
    if "/" not in (db_num or "") and "/" in yu:
        left = yu.split("/", 1)[0]
        return db == left.lstrip("0") or db == left
    return False


def _get_page(client: httpx.Client, url: str) -> str | None:
    for attempt, wait in enumerate((*RETRY_WAIT_SEC, None)):
        resp = client.get(url, timeout=30)
        if resp.status_code == 429:
            if wait is None:
                return None
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.text
    return None


def fetch_set_listings(vers: str, client: httpx.Client) -> dict[str, YuyuListing]:
    """vers 기준 유유테이 판매가 — 카드번호당 최저가."""
    block_re = _card_block_re(vers)
    out: dict[str, YuyuListing] = {}

    for i, rare in enumerate(RARE_FILTERS):
        if i > 0:
            time.sleep(REQUEST_DELAY_SEC)
        query = f"search_word=&vers%5B%5D={vers}&kizu=0"
        if rare:
            query += f"&rare={rare}"
        url = f"https://yuyu-tei.jp/sell/poc/s/search?{query}"
        text = _get_page(client, url)
        if text is None:
            break
        for num, rar, name, price in block_re.findall(text):
            key = normalize_card_number(num)
            p = int(price.replace(",", ""))
            if p <= 0:
                continue
            cur = out.get(key)
            if cur is None or p < cur.price_jpy:
                out[key] = YuyuListing(
                    card_number=key,
                    rarity=rar.strip(),
                    name_jp=name.strip(),
                    price_jpy=p,
                )
    return out


def fetch_card_listing(
    vers: str,
    card_number: str,
    name_jp: str,
    rarity: str,
    client: httpx.Client,
) -> YuyuListing | None:
    """--fallback: 미등록 카드 1장만 유유테i 검색 (세트 전체 스크랩 없음)."""
    block_re = _card_block_re(vers)
    r_upper = (rarity or "").upper()
    words: list[str] = []
    num = normalize_card_number(card_number)
    if num:
        words.append(num)
    if name_jp:
        words.append(name_jp.strip())
    if not words:
        return None

    best: YuyuListing | None = None
    for word in words:
        query = f"search_word={quote(word)}&vers%5B%5D={vers}&kizu=0"
        if r_upper in RARE_FILTERS and r_upper:
            query += f"&rare={r_upper}"
        url = f"https://yuyu-tei.jp/sell/poc/s/search?{query}"
        text = _get_page(client, url)
        if not text:
            continue
        for found_num, rar, name, price in block_re.findall(text):
            if card_number and not card_numbers_match(card_number, found_num):
                continue
            p = int(price.replace(",", ""))
            if p <= 0:
                continue
            listing = YuyuListing(
                card_number=normalize_card_number(found_num),
                rarity=rar.strip(),
                name_jp=name.strip(),
                price_jpy=p,
            )
            if best is None or p < best.price_jpy:
                best = listing
        if best:
            return best
        time.sleep(REQUEST_DELAY_SEC)
    return best
