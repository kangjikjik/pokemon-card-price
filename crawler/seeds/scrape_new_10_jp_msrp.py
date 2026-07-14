"""일본 공식 발매가 검증"""
import re
import sys
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
JP_PACK_RE = re.compile(r"希望小売価格[：:]\s*([\d,]+)\s*円")
JP_PACK_ALT = re.compile(r"([\d,]+)円（税込）")

URLS = {
    "SV5M": "https://www.pokemon-card.com/ex/sv5/",
    "SV4x": "https://www.pokemon-card.com/ex/sv4/",
    "SV4": "https://www.pokemon-card.com/ex/sv4/",
    "SV4a": "https://www.pokemon-card.com/ex/sv4a/",
    "SV4K": "https://www.pokemon-card.com/ex/sv4/",
    "SV4M": "https://www.pokemon-card.com/ex/sv4/",
    "SV3a": "https://www.pokemon-card.com/products/sv/sv3a.html",
    "SV3": "https://www.pokemon-card.com/ex/sv3/",
    "SV2a": "https://www.pokemon-card.com/ex/sv2a/",
    "SV2D": "https://www.pokemon-card.com/ex/sv2/",
}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for code, url in URLS.items():
        r = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        m = JP_PACK_RE.search(r.text) or JP_PACK_ALT.search(r.text)
        yen = int(m.group(1).replace(",", "")) if m else 0
        print(f"{code}: {yen}円 ({url})")
