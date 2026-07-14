import httpx, re
HEADERS = {"User-Agent": "Mozilla/5.0"}
for code in ["SV5a", "SV2a", "MG6", "SV4a"]:
    url = f"https://yuyu-tei.jp/sell/poc/s/{code}"
    r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
    # og:image or product images
    og = re.search(r'property="og:image"\s+content="([^"]+)"', r.text)
    print(f"=== {code} ===")
    if og:
        print("og:", og.group(1))
    # box product section
    for pat in [
        r'https://img\.yuyu-tei\.jp/[^"\']+',
        r'https://card\.yuyu-tei\.jp/[^"\']+box[^"\']*',
        r'https://[^"\']*box[^"\']*\.jpg',
    ]:
        found = set(re.findall(pat, r.text, re.I))
        for u in sorted(found)[:5]:
            print(" ", u)
