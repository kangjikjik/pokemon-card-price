import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

# SV2a product page deep parse
r = httpx.get("https://www.pokemon-card.com/products/sv/sv2a.html", headers=HEADERS, timeout=20)
print("SV2a imgs:")
for u in sorted(set(re.findall(r'(?:src|data-src|href)="([^"]+\.(?:jpg|png|webp))"', r.text, re.I))):
    if "product" in u or "image" in u or "box" in u or "package" in u:
        print(" ", u)

# try ex pages
for slug in ["sv2a", "sv3a", "sv5a", "sv8a", "sv7", "sv4a", "sv1s", "sv1v", "sv2d", "m5", "m2a"]:
    url = f"https://www.pokemon-card.com/ex/{'mega' if slug.startswith('m') else 'sv'}/{slug}/"
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
    if r.status_code != 200:
        continue
    imgs = re.findall(r'(?:src|content)="([^"]+\.(?:jpg|png|webp))"', r.text, re.I)
    boxish = [u for u in imgs if any(k in u.lower() for k in ["product", "box", "package", "ogp", "banner", "carousel"])]
    print(f"\n{slug} ({url}):")
    for u in sorted(set(boxish))[:6]:
        print(" ", u)

# direct image probes for MG6/M5
candidates = [
    "https://www.pokemon-card.com/ex/mega/m5/assets/images/ogp.png",
    "https://www.pokemon-card.com/ex/m5/assets/images/ogp.png",
    "https://www.pokemon-card.com/products/mega/assets/images/product-image-1.png",
    "https://www.pokemon-card.com/products/2026/images/MG6_2.jpg",
    "https://www.pokemon-card.com/products/2026/images/M5_2.jpg",
    "https://www.pokemon-card.com/products/2026/images/MG6_banner.jpg",
]
print("\nDirect probes:")
for url in candidates:
    rr = httpx.head(url, headers=HEADERS, follow_redirects=True, timeout=15)
    print(rr.status_code, url)
