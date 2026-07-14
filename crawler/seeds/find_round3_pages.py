import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)
IMG_RE = re.compile(r"(https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg))")

SETS = [
    ("S5P", "1611813416"),
    ("S6G", "1620799398"),  # ghost might use lance img - need separate
    ("S4SV", "1606382413"),
    ("S4B", "1602061417"),
    ("S3H", "1599620160"),
    ("S3Z", "1594372460"),
    ("S2R", "1591145463"),
    ("S6H", "1630376411"),  # eevee - wrong, need eevee box
]

c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
for code, key in SETS:
    for page in range(330, 400):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        if key not in r.text:
            continue
        m = KR_PRICE_RE.search(r.text)
        h3 = re.findall(r"<h3[^>]*>([^<]+)</h3>", r.text)
        imgs = [u for u in IMG_RE.findall(r.text) if key.split("-")[-1][:8] in u or key in u]
        print(f"{code} page={page} pack={m.group(1) if m else '?'} h3={h3[:2]}")
        for u in imgs[:2]:
            print(f"  {u}")
        break

# eevee heroes separate search
for page in range(370, 385):
    r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
    r.encoding = "utf-8"
    if "이브이 히어로" in r.text or "이브이히어로" in r.text.replace(" ", ""):
        m = KR_PRICE_RE.search(r.text)
        imgs = IMG_RE.findall(r.text)
        print(f"S6H page={page} pack={m.group(1) if m else '?'}")
        for u in imgs[:3]:
            if "2016-06-20" not in u:
                print(f"  {u}")
        break

# S6G ghost - separate img
for page in range(360, 370):
    r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
    r.encoding = "utf-8"
    if "칠흑" in r.text:
        m = KR_PRICE_RE.search(r.text)
        imgs = [u for u in IMG_RE.findall(r.text) if "2021/05" in u or "2021/06" in u]
        print(f"S6G page={page} pack={m.group(1) if m else '?'}")
        for u in imgs[:3]:
            print(f"  {u}")
        break
