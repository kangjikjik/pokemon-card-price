import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
r = httpx.get("https://pokemoncard.co.kr/card/557", headers=HEADERS, timeout=15)
r.encoding = "utf-8"
# extract title / h3
for m in re.finditer(r"<h3[^>]*>([^<]+)", r.text):
    print("h3:", m.group(1).strip())
for m in re.finditer(r"<title>([^<]+)", r.text):
    print("title:", m.group(1).strip())
imgs = re.findall(r"https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg)", r.text)
print("images:")
for u in dict.fromkeys(imgs):
    print(" ", u)
