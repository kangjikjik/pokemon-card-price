"""페이지 이미지 URL 덤프"""
import re
import httpx

for page in [50, 47, 13, 9, 27]:
    r = httpx.get(f"https://pokemoncard.co.kr/card/{page}", timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.encoding = "utf-8"
    imgs = re.findall(r'https?://[^"\'\s>]+\.(?:png|jpg|webp|PNG|JPG)', r.text)
    print(f"\n=== page {page} ===")
    for u in sorted(set(imgs)):
        if "2016-06-20" not in u:
            print(u[:110])
