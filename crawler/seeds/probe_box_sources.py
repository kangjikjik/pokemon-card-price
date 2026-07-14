import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

for code in ["MG6", "MG4a", "SV1S", "SV7", "SV2a", "SV3a", "SV4a"]:
    url = f"https://yuyu-tei.jp/sell/poc/s/{code}"
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
    og = re.search(r'property="og:image" content="([^"]+)"', r.text)
    imgs = re.findall(r"https://card\.yuyu-tei\.jp/[^\"']+\.(?:jpg|png)", r.text)
    print(f"\n=== {code} ({r.status_code}) ===")
    if og:
        print("og:", og.group(1))
    for u in sorted(set(imgs))[:5]:
        print(" ", u)

pages = [
    "https://www.pokemon-card.com/ex/sv/sv954/",
    "https://www.pokemon-card.com/products/sv/sv2a.html",
    "https://www.pokemon-card.com/products/sv/sv3a.html",
    "https://www.pokemon-card.com/products/sv/sv4a.html",
    "https://www.pokemon-card.com/products/sv/sv1s.html",
    "https://www.pokemon-card.com/products/sv/sv7.html",
]
for url in pages:
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
    print(f"\n=== {url} ({r.status_code}) ===")
    if r.status_code != 200:
        continue
    for pat in [
        r"https://www\.pokemon-card\.com/products/[^\"']+product-image[^\"']+",
        r"https://www\.pokemon-card\.com/products/\d+/images/[^\"']+",
        r'content="(https://www\.pokemon-card\.com/[^"]+\.(?:jpg|png))"',
    ]:
        ms = re.findall(pat, r.text)
        for m in ms[:3]:
            print(" ", m[:120])
