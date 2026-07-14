import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
for code in ["SV1S", "SV1V", "SV2D"]:
    for suffix in ["_2.jpg", "_banner.jpg", "_carousel.jpg", "_box.jpg", "_product.jpg"]:
        for y in ["2023", "2024"]:
            url = f"https://www.pokemon-card.com/products/{y}/images/{code}{suffix}"
            r = httpx.head(url, headers=HEADERS, follow_redirects=True, timeout=10)
            if r.status_code == 200:
                print(code, url)

# sv2 product-image from page absolute paths
import re
text = httpx.get("https://www.pokemon-card.com/products/sv/sv2.html", headers=HEADERS, timeout=20).text
for u in sorted(set(re.findall(r'"/products/2023/images/[^"]+\.(?:png|jpg)"', text))):
    if "SV2" in u or "sv2" in u.lower() or "1508" in u or "1509" in u:
        print("sv2 candidate", u)
