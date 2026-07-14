import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
urls = [
    "https://www.pokemon-card.com/products/mega/m5.html",
    "https://www.pokemon-card.com/products/mega/mg6.html",
    "https://www.pokemon-card.com/products/mega/",
    "https://www.pokemon-card.com/ex/mega/",
    "https://www.pokemon-card.com/ex/mega/m5/",
    "https://www.pokemon-card.com/products/2026/",
]
for url in urls:
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
        print(url, r.status_code, len(r.text))
        if r.status_code == 200:
            imgs = re.findall(
                r'(?:src|href)="([^"]*(?:product|box|package|image)[^"]*\.(?:jpg|png|webp))"',
                r.text,
                re.I,
            )
            for u in sorted(set(imgs))[:10]:
                print(" ", u[:120])
            if "アビス" in r.text or "abyss" in r.text.lower() or "M5" in r.text:
                print("  [has abyss/m5 content]")
    except Exception as e:
        print(url, e)
