import re
import httpx

c = httpx.Client(follow_redirects=True, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
for page in range(430, 455):
    r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
    if r.status_code != 200:
        continue
    r.encoding = "utf-8"
    h3s = re.findall(r"<h3[^>]*>([^<]+)</h3>", r.text)
    for h in h3s:
        if "GO" in h or "go" in h.lower():
            prices = re.findall(r"[\d,]+원\(1팩[^)]*\)", r.text)
            print(f"page={page} h3={h.strip()} prices={prices[:2]}")
