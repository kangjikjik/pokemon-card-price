import httpx
import re
from html import unescape

HEADERS = {"User-Agent": "Mozilla/5.0"}
text = httpx.get("https://www.pokemon-card.com/products/sv/sv1.html", headers=HEADERS, timeout=20).text
# all local product images
imgs = re.findall(r'(?:src|data-src)="(\./assets/images/[^"]+)"', text)
print("local imgs:")
for u in sorted(set(imgs)):
    print(" ", u)

# sv2 product images from sv2.html local assets
text2 = httpx.get("https://www.pokemon-card.com/products/sv/sv2.html", headers=HEADERS, timeout=20).text
imgs2 = re.findall(r'(?:src|data-src)="(\./assets/images/[^"]+)"', text2)
print("\nsv2 local imgs:")
for u in sorted(set(imgs2)):
    print(" ", u)
