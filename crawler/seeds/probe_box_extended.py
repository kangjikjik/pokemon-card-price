import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
codes = ["SV1S", "SV1V", "SV2D", "SV2a", "SV3a", "SV4a", "SV5a", "SV7", "SV8a", "MG4a", "MG6"]

patterns = [
    "https://www.pokemon-card.com/products/sv/{c}.html",
    "https://www.pokemon-card.com/products/sv/{cl}.html",
    "https://www.pokemon-card.com/products/2024/{c}_banner.jpg",
    "https://www.pokemon-card.com/products/2025/{c}_banner.jpg",
    "https://www.pokemon-card.com/products/2026/{c}_banner.jpg",
]

for code in codes:
    cl = code.lower()
    found = None
    for pat in patterns:
        url = pat.format(c=code, cl=cl)
        if url.endswith((".jpg", ".png")):
            r = httpx.head(url, headers=HEADERS, follow_redirects=True, timeout=15)
            if r.status_code == 200:
                found = url
                break
            continue
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        if r.status_code != 200 or len(r.text) < 3000:
            continue
        m = re.search(r'(https?://[^"\']+product-image-1\.(?:png|jpg|webp))', r.text)
        if not m:
            m = re.search(rf'(https?://[^"\']+/{code}_2\.jpg)', r.text, re.I)
        if not m:
            m = re.search(rf'(https?://[^"\']+/{code}_banner\.jpg)', r.text, re.I)
        if not m:
            rel = re.search(r'(/products/\d+/images/[^"\']+\.(?:jpg|png))', r.text)
            if rel:
                m = type("M", (), {"group": lambda self, n: "https://www.pokemon-card.com" + rel.group(1)})()
        if m:
            found = m.group(1) if hasattr(m, "group") else m
            break
    print(f"{code}: {found or 'NOT FOUND'}")
