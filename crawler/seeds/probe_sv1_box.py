import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

for code, slug in [("SV1S", "sv1s"), ("SV1V", "sv1v"), ("SV2D", "sv2d")]:
    paths = [
        f"https://www.pokemon-card.com/ex/{slug}/assets/images/ogp.png",
        f"https://www.pokemon-card.com/ex/sv/{slug}/assets/images/ogp.png",
        f"https://www.pokemon-card.com/products/2023/images/{code}_2.jpg",
        f"https://www.pokemon-card.com/products/2023/images/{code}_banner.jpg",
        f"https://www.pokemon-card.com/products/2023/images/{code}_carousel.jpg",
        f"https://www.pokemon-card.com/products/2024/images/{code}_2.jpg",
    ]
    for p in paths:
        r = httpx.head(p, headers=HEADERS, follow_redirects=True, timeout=12)
        if r.status_code == 200:
            print(f"{code}: {p}")
            break
    else:
        # try ex page html
        for base in [f"https://www.pokemon-card.com/ex/{slug}/", f"https://www.pokemon-card.com/products/sv/{slug}.html"]:
            r = httpx.get(base, headers=HEADERS, follow_redirects=True, timeout=20)
            if r.status_code != 200:
                continue
            imgs = re.findall(r'(?:src|content)="([^"]+\.(?:jpg|png|webp))"', r.text, re.I)
            picks = [u for u in imgs if "ogp" in u or "product-image" in u or code.lower() in u.lower()]
            if picks:
                print(f"{code} from {base}: {picks[:3]}")
                break
        else:
            print(f"{code}: NOT FOUND")
