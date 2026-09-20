import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")
import httpx
from lib.collectory_public import TR_ROW_RE, _row_text

cid = "95cbdbb8-0f6a-4455-9d79-95428501d641"
html = httpx.get(f"https://collectory.cc/cards/{cid}", timeout=60).text
for row in TR_ROW_RE.findall(html):
    if "SNKRDUNK" not in row:
        continue
    parts = _row_text(row)
    price_m = re.search(r"₩\s*([\d,]+)", row)
    price = int(price_m.group(1).replace(",", "")) if price_m else 0
    if 20000 <= price <= 40000:
        print("RAW?", price, parts[:6])
