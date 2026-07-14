import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
r = httpx.get("https://www.pokemon-card.com/products/sv/sv2.html", headers=HEADERS, timeout=20)
text = r.text

# find SV2D / SV2P box sections
for m in re.finditer(r"SV2[DP]", text):
    start = max(0, m.start() - 200)
    chunk = text[start : m.start() + 400]
    imgs = re.findall(r'(?:src|data-src)="([^"]+\.(?:jpg|png|webp))"', chunk, re.I)
    if imgs:
        print("near", m.group(), ":", imgs)

# product-image patterns
for pat in ["product-image", "product2-image", "product3-image", "box", "package"]:
    hits = re.findall(rf'[^"\']*{pat}[^"\']*\.(?:png|jpg)', text, re.I)
    if hits:
        print(f"\n{pat}:", sorted(set(hits))[:8])

# direct SV2D product image guesses
for url in [
    "https://www.pokemon-card.com/products/2023/images/1509_SV2D_pillow_img.png",
    "https://www.pokemon-card.com/products/2023/images/1508_SV2P_pillow_img.png",
]:
    rr = httpx.head(url, headers=HEADERS, follow_redirects=True, timeout=12)
    print(rr.status_code, url)

# sv1 product images
r1 = httpx.get("https://www.pokemon-card.com/products/sv/sv1.html", headers=HEADERS, timeout=20)
for pat in ["product-image", "product2-image", "product3-image", "sv1s", "sv1v"]:
    hits = re.findall(rf'[^"\']*{pat}[^"\']*\.(?:png|jpg)', r1.text, re.I)
    if hits:
        print(f"\nsv1 {pat}:", sorted(set(hits))[:6])
