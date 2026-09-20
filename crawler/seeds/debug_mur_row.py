import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")
import httpx
from lib.collectory_public import TR_ROW_RE, _row_text

cid = "6c3dc15d-5497-4591-bdfb-dc802cc7cbb0"  # MUR darkrai
html = httpx.get(f"https://collectory.cc/cards/{cid}", timeout=60).text
for row in TR_ROW_RE.findall(html):
    if "SNKRDUNK" not in row:
        continue
    parts = _row_text(row)
    price_m = re.search(r"₩\s*([\d,]+)", row)
    price = int(price_m.group(1).replace(",", "")) if price_m else 0
    print("price", f"{price:,}", "| parts[2:6]", parts[2:6] if len(parts) > 2 else parts)
