import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
r = httpx.get("https://www.pokemon-card.com/products/sv/sv1.html", headers=HEADERS, timeout=20)
text = r.text
for code in ["SV1S", "SV1V", "sv1s", "sv1v"]:
    idx = text.find(code)
    while idx != -1:
        chunk = text[max(0, idx - 300) : idx + 500]
        imgs = re.findall(r'(?:src|data-src|href)="([^"]+\.(?:jpg|png|webp))"', chunk, re.I)
        if imgs:
            print(f"near {code}:", imgs)
        idx = text.find(code, idx + 1)

for url in [
    "https://www.pokemon-card.com/ex/sv1/assets/images/product3-image-1.png",
    "https://www.pokemon-card.com/products/sv/assets/images/product-image-1.png",
]:
    rr = httpx.head(url, headers=HEADERS, follow_redirects=True, timeout=12)
    print(rr.status_code, url)

# search sv2 for box-ish product images
r2 = httpx.get("https://www.pokemon-card.com/products/sv/sv2.html", headers=HEADERS, timeout=20)
for m in re.finditer(r"product\d?-image-\d+\.png", r2.text):
    print("sv2", m.group())
