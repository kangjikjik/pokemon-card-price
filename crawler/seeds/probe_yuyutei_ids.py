import re, httpx

HEADERS = {"User-Agent": "Mozilla/5.0"}
IDS = ["10096", "10099", "10100", "10101", "10102", "10103", "10104", "10105", "10106", "10107", "10108"]

with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as c:
    for cid in IDS:
        url = f"https://yuyu-tei.jp/sell/poc/card/m05/{cid}"
        r = c.get(url)
        title = re.search(r'<title>([^<]+)</title>', r.text)
        img = re.search(r'https://card\.yuyu-tei\.jp/poc/100_140/m05/\d+\.jpg', r.text)
        price = re.search(r'([\d,]+)\s*円', r.text)
        h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', r.text)
        alt = re.findall(r'alt="([^"]*081[^"]*)"', r.text)
        print(f"{cid}: status={r.status_code} title={title.group(1)[:50] if title else '?'}")
        print(f"  img={img.group() if img else 'none'} price={price.group(1) if price else '?'}")
        if alt:
            print(f"  alt={alt[0]}")
