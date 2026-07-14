import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

candidates = []
for y in ["2023", "2024", "2025"]:
    for code in ["SV1S", "SV1V", "SV2D", "SV1s", "SV1v", "SV2d"]:
        for suffix in ["_2.jpg", "_banner.jpg", "_carousel.jpg", "_box.jpg"]:
            candidates.append(f"https://www.pokemon-card.com/products/{y}/images/{code}{suffix}")

for code, slug in [("SV1S", "sv1s"), ("SV1V", "sv1v"), ("SV2D", "sv2d"), ("SV1", "sv1")]:
    candidates.extend([
        f"https://www.pokemon-card.com/ex/{slug}/assets/images/ogp.png",
        f"https://www.pokemon-card.com/ex/sv/{slug}/assets/images/ogp.png",
        f"https://www.pokemon-card.com/ex/sv1/{slug}/assets/images/ogp.png",
    ])

seen = set()
for url in candidates:
    if url in seen:
        continue
    seen.add(url)
    r = httpx.head(url, headers=HEADERS, follow_redirects=True, timeout=10)
    if r.status_code == 200:
        print(r.status_code, url)

# scarlet ex / violet ex combined pages
for url in [
    "https://www.pokemon-card.com/products/sv/sv1.html",
    "https://www.pokemon-card.com/ex/sv1/",
    "https://www.pokemon-card.com/ex/sv1s/",
    "https://www.pokemon-card.com/ex/sv1v/",
]:
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
    print("page", url, r.status_code)
    if r.status_code == 200:
        imgs = re.findall(r'(?:src|content)="([^"]+\.(?:jpg|png|webp))"', r.text, re.I)
        for u in sorted(set(imgs)):
            if any(k in u.lower() for k in ["ogp", "product", "box", "package", "sv1"]):
                print(" ", u[:120])
