import re, httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}

with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as c:
    for cid in range(10080, 10130):
        cid_s = str(cid)
        url = f"https://yuyu-tei.jp/sell/poc/card/m05/{cid_s}"
        r = c.get(url)
        if r.status_code != 200:
            continue
        title = re.search(r'<title>([^<]+)</title>', r.text)
        if not title or "アビスアイ" not in title.group(1) and "M5" not in title.group(1):
            continue
        t = title.group(1)
        img = re.search(r'https://card\.yuyu-tei\.jp/poc/100_140/m05/(\d+)\.jpg', r.text)
        price = re.search(r'class="[^"]*price[^"]*"[^>]*>\s*([\d,]+)\s*円', r.text) or re.search(r'([\d,]+)\s*円', r.text)
        num = re.search(r'(\d+/\d+)', t)
        print(f"{cid_s}: {t[:70]}")
        print(f"  img={img.group(1) if img else '?'} price={price.group(1) if price else '?'}")
