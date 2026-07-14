import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}

for url in [
    "https://www.pokemon-card.com/products/sv/assets/images/product3-image-1.png",
    "https://www.pokemon-card.com/ex/sv1/assets/images/product3-image-1.png",
    "https://www.pokemon-card.com/ex/sv2d/assets/images/ogp.png",
    "https://www.pokemon-card.com/ex/sv2/assets/images/ogp.png",
    "https://www.pokemon-card.com/products/sv/sv2.html",
]:
    r = httpx.head(url, headers=HEADERS, follow_redirects=True, timeout=12)
    print(r.status_code, url)

r = httpx.get("https://www.pokemon-card.com/products/sv/sv2.html", headers=HEADERS, timeout=20)
print("sv2 page", r.status_code, len(r.text))
if r.status_code == 200:
    import re
    imgs = re.findall(r'(?:src|content)="([^"]+\.(?:jpg|png|webp))"', r.text, re.I)
    for u in sorted(set(imgs)):
        if "product" in u.lower() or "ogp" in u.lower() or "sv2" in u.lower():
            print(" ", u)
