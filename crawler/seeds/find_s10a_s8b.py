import re
import sys
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)
IMG_RE = re.compile(r"(https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg))")

QUERIES = [
    ("S10a", "Pokémon GO"),
    ("S10a", "포켓몬 GO"),
    ("S8b", "VMAX 클라이맥스"),
    ("S8b", "VMAX클라이맥스"),
]

c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
for code, needle in QUERIES:
    for page in range(380, 520):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        if needle not in r.text and needle.replace(" ", "") not in r.text.replace(" ", ""):
            continue
        m = KR_PRICE_RE.search(r.text)
        imgs = IMG_RE.findall(r.text)
        print(f"\n{code} needle={needle} page={page} pack={m.group(1) if m else '?'}")
        for u in imgs[:4]:
            if "2016-06-20" not in u:
                print(f"  {u}")
        break
