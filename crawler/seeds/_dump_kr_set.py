import httpx
import sys

sys.stdout.reconfigure(encoding="utf-8")
cards = httpx.get(
    "https://collectory.cc/api/sets/111a2e55-8991-414b-a5da-009b3553e6cd/cards",
    timeout=60,
).json()["cards"]
for c in sorted(cards, key=lambda x: x["card_number"]):
    n = int(c["card_number"].split("/")[0])
    if 102 <= n <= 117:
        img = (c.get("image_url") or "").split("?")[0]
        jp = c.get("name_ja") or c.get("name") or ""
        print(f"num={c['card_number']:8} ko={c.get('name_ko',''):24} jp={jp:22} img={img}")
