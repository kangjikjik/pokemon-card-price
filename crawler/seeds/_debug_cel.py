import httpx
import sys

sys.stdout.reconfigure(encoding="utf-8")
t = httpx.get("https://www.pokemon-card.com/ex/25th/products/", headers={"User-Agent": "Mozilla/5.0"}).text
idx = t.find("297")
print("idx", idx)
print(repr(t[idx - 200 : idx + 50]))
