import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)

for page in range(395, 520):
    r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
    if r.status_code != 200:
        continue
    r.encoding = "utf-8"
    if "5,000원(1팩" not in r.text:
        continue
    # extract h3 near price
    idx = r.text.find("5,000원(1팩")
    chunk = r.text[max(0, idx - 800) : idx + 200]
    h3 = re.findall(r"<h3[^>]*>([^<]+)", chunk)
    print(f"page={page} h3={h3[-3:] if h3 else '?'}")
