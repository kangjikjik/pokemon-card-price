import httpx, re
HEADERS = {"User-Agent": "Mozilla/5.0"}
urls = [
    "https://www.pokemon-card.com/products/sv/sv5a.html",
    "https://www.pokemon-card.com/products/sv/sv2a.html",
    "https://www.pokemon-card.com/products/mega/m6.html",
]
for url in urls:
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
    print("===", url, "===")
    imgs = re.findall(r'(?:src|href)="([^"]+\.(?:jpg|png|webp)[^"]*)"', r.text, re.I)
    for u in sorted(set(imgs)):
        if "card" in u.lower() or "pack" in u.lower() or "product" in u.lower() or "img" in u.lower() or "thumb" in u.lower():
            print(" ", u)
