import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}

for page in [556, 557, 558]:
    r = httpx.get(f"https://pokemoncard.co.kr/card/{page}", headers=HEADERS, timeout=15)
    r.encoding = "utf-8"
    print("=== page", page, "===")
    print("흑염", "흑염" in r.text, "지배자", "지배자" in r.text)
    imgs = re.findall(r"https://data1\.pokemonkorea\.co\.kr/2023/08/[^\"'\s>]+\.png", r.text)
    for u in dict.fromkeys(imgs):
        print(" ", u)
