"""일본 공식 발매가 검증 — 신규 15세트"""
import re
import sys
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
JP_PACK_RE = re.compile(r"希望小売価格[：:]\s*([\d,]+)\s*円")
JP_PACK_ALT = re.compile(r"([\d,]+)円（税込）")

URLS = {
    "SV2P": "https://www.pokemon-card.com/ex/sv2/",
    "SV1a": "https://www.pokemon-card.com/products/sv/sv1a.html",
    "SV1V": "https://www.pokemon-card.com/ex/sv1/",
    "SV1S": "https://www.pokemon-card.com/ex/sv1/",
    "S12a": "https://www.pokemon-card.com/ex/s12a/",
    "S12": "https://www.pokemon-card.com/ex/s12/",
    "S11a": "https://www.pokemon-card.com/products/s/s11a.html",
    "S11": "https://www.pokemon-card.com/ex/s11/",
    "S10b": "https://www.pokemon-card.com/products/s/s10b.html",
    "S10a": "https://www.pokemon-card.com/ex/s10a/",
    "S9a": "https://www.pokemon-card.com/ex/s9/",
    "S9": "https://www.pokemon-card.com/ex/s9/",
    "S8": "https://www.pokemon-card.com/products/s/s8.html",
    "S8a": "https://www.pokemon-card.com/ex/s8a/",
    "S8b": "https://www.pokemon-card.com/ex/s8b/",
}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for code, url in URLS.items():
        r = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        m = JP_PACK_RE.search(r.text) or JP_PACK_ALT.search(r.text)
        yen = int(m.group(1).replace(",", "")) if m else 0
        print(f"{code}: {yen}円 ({url})")
