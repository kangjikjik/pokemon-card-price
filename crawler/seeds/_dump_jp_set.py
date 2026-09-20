import httpx
import sys

sys.stdout.reconfigure(encoding="utf-8")
cards = httpx.get(
    "https://collectory.cc/api/sets/611cf371-dafe-42fc-b86d-895aa433e10d/cards",
    timeout=60,
).json()["cards"]
for c in sorted(cards, key=lambda x: x["card_number"]):
    n = int(c["card_number"].split("/")[0])
    if 102 <= n <= 111:
        print(f"num={c['card_number']:8} ko={c.get('name_ko',''):20} name={c.get('name','')}")
