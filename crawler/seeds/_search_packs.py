"""pokemonkorea 뉴스/카드 검색으로 단일 팩 이미지 찾기"""
from __future__ import annotations

import re
from pathlib import Path

import httpx

OUT = Path(__file__).parent / "_img_audit"
client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

DATA1 = re.compile(
    r"(https://data1\.pokemonkorea\.co\.kr/20\d{2}/[^\"'\s>]+\.(?:png|jpg|PNG|JPG))"
)
LINK = re.compile(r'href=["\']([^"\']*(?:news|card|goods)[^"\']*)["\']', re.I)

QUERIES = {
    "울트라썬": "SM4",
    "울트라문": "SM4+",
    "확장팩 소드": "S1W",
    "확장팩 실드": "S1H",
    "썬 컬렉션": "SM1C",
    "문 컬렉션": "SM1M",
    "배틀부스트 REMASTER": "SM7a",
    "빛나는 전설": "SM2+",
    "얼터제네시스": "SM12",
}


def search_news(q: str) -> list[str]:
    urls = []
    for path in [
        f"https://pokemonkorea.co.kr/news/2?search={httpx.QueryParams({'search': q})['search']}",
        f"https://pokemonkorea.co.kr/news?search={q}",
    ]:
        try:
            r = client.get("https://pokemonkorea.co.kr/news/2", params={"search": q})
            for href in LINK.findall(r.text):
                if href.startswith("/"):
                    href = "https://pokemonkorea.co.kr" + href
                if "pokemonkorea" in href and href not in urls:
                    urls.append(href)
        except Exception:
            pass
    return urls[:8]


def imgs_from(url: str) -> list[str]:
    try:
        r = client.get(url)
        return list(dict.fromkeys(DATA1.findall(r.text)))
    except Exception:
        return []


for q, code in QUERIES.items():
    print(f"\n=== {code} query={q} ===")
    links = search_news(q)
    print(f"  links={len(links)}")
    found = []
    for link in links[:5]:
        imgs = imgs_from(link)
        print(f"  {link[:70]} -> {len(imgs)} imgs")
        for u in imgs[:3]:
            print(f"    {u.split('/')[-1]}")
            found.append(u)
    # also try direct product search on pokemoncard
    # download first few unique
    for i, u in enumerate(list(dict.fromkeys(found))[:4]):
        try:
            ir = client.get(u)
            (OUT / f"search_{code}_{i}_{u.split('/')[-1]}").write_bytes(ir.content)
            print(f"  saved search_{code}_{i}")
        except Exception as e:
            print(f"  save fail {e}")

# Japanese pack images as reference (pokemon-card.com)
print("\n=== JP product pages ===")
JP = {
    "SM4": "https://www.pokemon-card.com/products/sm/sm5.html",  # guess
}
# try known JP URLs
jp_urls = [
    ("SM5S", "https://www.pokemon-card.com/products/sm/sm5S.html"),
    ("SM5M", "https://www.pokemon-card.com/products/sm/sm5M.html"),
    ("S1W", "https://www.pokemon-card.com/products/s/s1.html"),
    ("S1H", "https://www.pokemon-card.com/products/s/s1a.html"),
]
for code, url in jp_urls:
    try:
        r = client.get(url)
        print(f"{code} {r.status_code} {url}")
        imgs = re.findall(r'(https?://[^\"\']+\.(?:png|jpg|jpeg))', r.text, re.I)
        packish = [u for u in imgs if "products" in u or "pack" in u.lower() or "sm5" in u.lower() or "/s/" in u]
        for u in (packish or imgs)[:5]:
            print(f"  {u}")
    except Exception as e:
        print(code, e)
