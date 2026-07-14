import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
text = httpx.get("https://www.pokemon-card.com/products/sv/sv2.html", headers=HEADERS, timeout=20).text
idx = text.find("SV2D")
while idx != -1:
    chunk = text[max(0, idx - 500) : idx + 1200]
    imgs = re.findall(r'"(/products/2023/images/[^"]+)"', chunk)
    print("SV2D context imgs:", imgs)
    idx = text.find("SV2D", idx + 1)

idx = text.find("SV2P")
while idx != -1:
    chunk = text[max(0, idx - 500) : idx + 1200]
    imgs = re.findall(r'"(/products/2023/images/[^"]+)"', chunk)
    print("SV2P context imgs:", imgs)
    idx = text.find("SV2P", idx + 1)

text1 = httpx.get("https://www.pokemon-card.com/products/sv/sv1.html", headers=HEADERS, timeout=20).text
for label in ["スカーレットex", "バイオレットex", "product3-image", "product2-image"]:
    i = text1.find(label)
    if i >= 0:
        chunk = text1[max(0, i - 400) : i + 800]
        imgs = re.findall(r'"(?:https://www\.pokemon-card\.com)?(/[^"]+\.(?:png|jpg))"', chunk)
        print(label, imgs[:5])
