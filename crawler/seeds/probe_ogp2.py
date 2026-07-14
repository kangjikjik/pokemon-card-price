import httpx

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
    for path in [
        f"https://www.pokemon-card.com/ex/{slug}/assets/images/ogp.png",
        f"https://www.pokemon-card.com/products/sv/assets/images/product-image-1.png",
        f"https://www.pokemon-card.com/products/2024/images/{code}_2.jpg",
        f"https://www.pokemon-card.com/products/2024/images/{code}_banner.jpg",
        f"https://www.pokemon-card.com/products/2023/images/{code}_carousel.jpg",
        f"https://www.pokemon-card.com/products/2025/images/{code}_2.jpg",
    ]:
        r = httpx.head(path, headers=HEADERS, follow_redirects=True, timeout=12)
        if r.status_code == 200:
            print(f"{code}: {path}")
            break
    else:
        print(f"{code}: NOT FOUND")
