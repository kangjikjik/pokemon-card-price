import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

sets = {
    "SV2a": "sv2a",
    "SV3a": "sv3a",
    "SV4a": "sv4a",
    "SV5a": "sv5a",
    "SV7": "sv7",
    "SV8a": "sv8a",
    "SV1S": "sv1s",
    "SV1V": "sv1v",
    "SV2D": "sv2d",
    "MG6": "m5",
    "MG4a": "m2a",
}

for code, slug in sets.items():
    url = f"https://www.pokemon-card.com/ex/{'mega' if slug.startswith('m') else 'sv'}/{slug}/assets/images/ogp.png"
    if slug.startswith("m"):
        url = f"https://www.pokemon-card.com/ex/{slug}/assets/images/ogp.png"
    r = httpx.head(url, headers=HEADERS, follow_redirects=True, timeout=15)
    print(f"{code}: {r.status_code} {url}")

# also check product-image patterns on ex pages
for code, slug in sets.items():
    base = f"https://www.pokemon-card.com/ex/{slug}/"
    r = httpx.get(base, headers=HEADERS, follow_redirects=True, timeout=20)
    if r.status_code != 200:
        print(f"{code} page {r.status_code}")
        continue
    imgs = re.findall(r'(?:src|content)="([^"]+\.(?:jpg|png|webp))"', r.text, re.I)
    picks = [u for u in sorted(set(imgs)) if "assets/images" in u]
    print(f"{code} page imgs: {picks[:4]}")
