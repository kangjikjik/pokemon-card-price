import re
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
KR_PRICE_RE = re.compile(
    r"([\d,]+)원\(1팩[^)]*\),\s*([\d,]+)원\(1상자[^)]*\)",
    re.I,
)
IMG_RE = re.compile(r"(https://data1\.pokemonkorea\.co\.kr/[^\"'\s>]+\.(?:png|jpg))")

TARGETS = [
    ("S10a", "GO", 5000, 50000),
    ("S8b", "클라이맥스", 5000, 50000),
]

c = httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS)
for code, needle, want_pack, want_box in TARGETS:
    for page in range(380, 520):
        r = c.get(f"https://pokemoncard.co.kr/card/{page}", timeout=12)
        if r.status_code != 200:
            continue
        r.encoding = "utf-8"
        if needle not in r.text:
            continue
        m = KR_PRICE_RE.search(r.text)
        if not m:
            continue
        pack = int(m.group(1).replace(",", ""))
        box = int(m.group(2).replace(",", ""))
        if pack != want_pack or box != want_box:
            continue
        imgs = [u for u in IMG_RE.findall(r.text) if "2016-06-20" not in u]
        print(f"{code} page={page} pack={pack} box={box}")
        for u in imgs[:3]:
            print(f"  {u}")
