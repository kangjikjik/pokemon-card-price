import httpx
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}
text = httpx.get("https://www.pokemon-card.com/products/sv/sv1.html", headers=HEADERS, timeout=20).text
# hash pngs often used for product shots
hash_pngs = re.findall(r'"/products/\d+/images/([a-f0-9]{40}\.png)"', text)
print("sv1 hash pngs", len(hash_pngs))
for h in hash_pngs[:6]:
    url = f"https://www.pokemon-card.com/products/2023/images/{h}"
    print(url)

text2 = httpx.get("https://www.pokemon-card.com/products/sv/sv2.html", headers=HEADERS, timeout=20).text
hash_pngs2 = re.findall(r'"/products/\d+/images/([a-f0-9]{40}\.png)"', text2)
print("sv2 hash pngs", len(hash_pngs2))
for h in hash_pngs2[:6]:
    print(f"https://www.pokemon-card.com/products/2023/images/{h}")

# check if sv1 page has separate sv1s/sv1v product sections with jpg
for m in re.finditer(r"スカーレット|バイオレット|SV1S|SV1V", text):
    chunk = text[m.start(): m.start()+800]
    imgs = re.findall(r'"(/products/[^"]+\.(?:png|jpg))"', chunk)
    if imgs:
        print("section", m.group(), imgs[:3])
