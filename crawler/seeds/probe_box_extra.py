import httpx, re
HEADERS = {"User-Agent": "Mozilla/5.0"}
extra = [
    "https://www.pokemon-card.com/products/sv/sv1s.html",
    "https://www.pokemon-card.com/products/sv/sv1v.html",
    "https://www.pokemon-card.com/products/sv/sv2d.html",
    "https://www.pokemon-card.com/products/sv/sv3a.html",
    "https://www.pokemon-card.com/products/sv/sv4a.html",
    "https://www.pokemon-card.com/products/sv/sv7.html",
    "https://www.pokemon-card.com/products/mega/mg4a.html",
    "https://www.pokemon-card.com/products/mega/mg6.html",
    "https://www.pokemon-card.com/products/mega/m6a.html",
    "https://www.pokemon-card.com/products/mega/mega6.html",
]
for url in extra:
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
    print(url, r.status_code, len(r.text))
    if r.status_code == 200:
        for pat in [r'product-image-1\.[^"\']+', r'/products/\d+/images/[^"\']+_2\.jpg', r'og:image" content="([^"]+)']:
            m = re.search(pat, r.text)
            if m:
                print(" ", m.group(0) if m.lastindex is None else m.group(1))
