import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
text = httpx.get("https://www.pokemon-card.com/products/sv/sv1.html", headers=HEADERS, timeout=20).text
imgs = re.findall(r'"(/products/\d+/images/[^"]+)"', text)
print("all product imgs", len(imgs))
for u in imgs:
    print(u)

# ex sv1 absolute assets
text2 = httpx.get("https://www.pokemon-card.com/ex/sv1/", headers=HEADERS, timeout=20).text
assets = re.findall(r'"(?:https://www\.pokemon-card\.com)?(/ex/sv1/assets/images/[^"]+)"', text2)
assets += re.findall(r'"(\./assets/images/[^"]+)"', text2)
for u in sorted(set(assets)):
    if "product" in u or "icon" in u or "ogp" in u:
        print("asset", u)
