import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
r = httpx.get("https://pokemoncard.co.kr/card/558", headers=HEADERS, timeout=15)
r.encoding = "utf-8"
imgs = re.findall(r"https://data1\.pokemonkorea\.co\.kr/2023/08/[^\"'\s>]+\.png", r.text)
for u in dict.fromkeys(imgs):
    idx = r.text.find(u)
    ctx = re.sub(r"\s+", " ", r.text[max(0, idx - 200): idx + len(u) + 200])
    print("===", u.split("/")[-1][:50], "===")
    print(ctx[:400])
    print()
