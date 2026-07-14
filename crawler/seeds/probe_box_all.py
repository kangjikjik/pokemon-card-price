import httpx, re
HEADERS = {"User-Agent": "Mozilla/5.0"}
codes = ["SV1S","SV1V","SV2D","SV2a","SV3a","SV4a","SV5a","SV7","SV8a","MG4a","MG6"]
for code in codes:
    paths = [
        f"https://www.pokemon-card.com/products/sv/{code.lower()}.html",
        f"https://www.pokemon-card.com/products/mega/{code.lower().replace('mg','m')}.html",
        f"https://www.pokemon-card.com/products/mega/{code.lower()}.html",
    ]
    for url in paths:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        if r.status_code != 200 or len(r.text) < 5000:
            continue
        box = re.search(r'product-image-1\.(?:png|jpg|webp)', r.text)
        jpg = re.search(rf'/products/\d+/images/{code}_2\.jpg', r.text, re.I)
        banner = re.search(rf'/products/\d+/images/{code}_banner\.jpg', r.text, re.I)
        if box or jpg or banner:
            print(code, url)
            if box: print("  product-image-1")
            if jpg: print("  _2.jpg")
            if banner: print("  banner")
            break
