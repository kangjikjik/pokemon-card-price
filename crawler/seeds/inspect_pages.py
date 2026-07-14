import re
import httpx

for page in [439, 443, 401]:
    r = httpx.get(f"https://pokemoncard.co.kr/card/{page}", timeout=15)
    r.encoding = "utf-8"
    prices = re.findall(r"[\d,]+원\(1팩[^)]*\), [\d,]+원\(1상자[^)]*\)", r.text)
    imgs = re.findall(r"https://data1\.pokemonkorea\.co\.kr/2022/06[^\"'\s>]+", r.text)
    print(f"\n=== page {page} ===")
    print("prices:", prices[:3])
    print("jun imgs:", imgs[:3])
