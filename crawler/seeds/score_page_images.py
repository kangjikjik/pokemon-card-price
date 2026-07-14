"""문제 페이지 이미지 후보 점수화"""
import httpx
import re
from kr_sets import KR_BY_CODE
from sync_box_images import pick_best_box, score_url, DATA1_IMG, PLACEHOLDER

BAD = re.compile(r"hover|banner|bg_|collection|gms\d", re.I)

for code in ["SM5+", "SM5", "SM4+", "SM4", "SM4a", "SM7a", "SM12", "SM2+", "SM3+", "SM6b"]:
    s = KR_BY_CODE[code]
    r = httpx.get(f"https://pokemoncard.co.kr/card/{s.pokemoncard_page}", timeout=15)
    r.encoding = "utf-8"
    imgs = list(dict.fromkeys(
        u for u in DATA1_IMG.findall(r.text) if PLACEHOLDER not in u
    ))
    print(f"\n=== {code} p{s.pokemoncard_page} stored={s.box_image_kr.split('/')[-1] if s.box_image_kr else 'none'} ===")
    for u in sorted(imgs, key=score_url, reverse=True)[:8]:
        print(f"  {score_url(u):3} {u.split('/')[-1]}")
