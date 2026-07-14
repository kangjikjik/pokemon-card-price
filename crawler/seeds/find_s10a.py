import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)
IMG_RE = re.compile(r"(https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg))")

NEEDLES = ["포켓몬 GO", "Pokémon GO", "Pokemon GO", "포켓몬GO"]

c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
for page in range(380, 460):
    r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
    if r.status_code != 200:
        continue
    r.encoding = "utf-8"
    for needle in NEEDLES:
        if needle not in r.text:
            continue
        m = KR_PRICE_RE.search(r.text)
        pack = int(m.group(1).replace(",", "")) if m else 0
        print(f"page={page} needle={needle} pack={pack}")
        imgs = [u for u in IMG_RE.findall(r.text) if "2016-06-20" not in u]
        for u in imgs[:4]:
            print(f"  {u}")
        break
