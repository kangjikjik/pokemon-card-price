import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
IMG_RE = re.compile(r"(https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg))")

PAGES = [
    ("SV1V", 522),
    ("SV1S", 523),
    ("S10a", 401),
    ("S8b", 401),
    ("S10b", 447),
    ("S9a", 430),
]

c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
for code, page in PAGES:
    r = c.get(f"https://pokemoncard.co.kr/card/{page}")
    r.encoding = "utf-8"
    imgs = IMG_RE.findall(r.text)
    print(f"\n{code} page={page}")
    for u in imgs[:6]:
        print(f"  {u}")
