import re, httpx
HEADERS = {"User-Agent": "Mozilla/5.0"}
with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as c:
    for cid in range(10035, 10082):
        r = c.get(f"https://yuyu-tei.jp/sell/poc/card/m05/{cid}")
        if r.status_code != 200:
            continue
        title = re.search(r"<title>([^<]+)</title>", r.text)
        if not title:
            continue
        t = title.group(1)
        m = re.match(r"([A-Z]+(?:\s+ACE)?)\s+(.+?)\s+販売", t)
        if not m:
            continue
        rarity, name = m.groups()
        img = re.search(r"m05/(\d+)\.jpg", r.text)
        img_id = img.group(1) if img else ""
        print(f"{cid:5} {rarity.strip():4} {name.strip():20} img={img_id}")
