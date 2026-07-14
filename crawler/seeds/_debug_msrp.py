import httpx
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
c = httpx.Client(timeout=25, headers={"User-Agent": "Mozilla/5.0"})
t = c.get("https://www.pokemon-card.com/ex/25th/products/").text
patterns = [
    r"拡張パック 25th ANNIVERSARY COLLECTION.{0,120}?([\d,]+)\s*円",
    r"25th ANNIVERSARY COLLECTION.{0,200}?希望小売価格[：:\s]*([\d,]+)\s*円",
]
for p in patterns:
    m = re.search(p, t, re.S)
    print(p, m.group(1) if m else None)

# brute find tag bolt PR ids
for n in range(40, 60):
    url = f"https://prtimes.jp/main/html/rd/p/0000000{n}.000026665.html"
    r = c.get(url)
    if r.status_code != 200:
        continue
    if "タッグボルト" in r.text and "150" in r.text:
        print("TAG PR", n, re.findall(r"150円.{0,15}", r.text)[:2])
