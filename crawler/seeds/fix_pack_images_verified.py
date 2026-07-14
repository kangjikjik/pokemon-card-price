"""잘못된 박스 이미지를 세트명 확인된 단일 팩 이미지로 교체.

검증 기준: 이미지에 해당 세트 한글명이 보이는 단일 부스터 팩.
듀얼/포스터만 있는 경우 공식 이미지에서 해당 팩만 크롭해 public/set-boxes 에 저장.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import replace
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image
from supabase import create_client

from apply_batch1 import ensure_kr_sets_footer, write_kr_sets
from kr_sets import KR_SETS, KrSet
from revert_featured_55 import write_set_images

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "web" / "public" / "set-boxes"
PUBLIC.mkdir(parents=True, exist_ok=True)
AUDIT = Path(__file__).parent / "_img_audit"

client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

# 원격 URL로 이미 단일 팩이 확인된 것
REMOTE_OK: dict[str, str] = {
    # 금단의 빛 팩 (울트라네크로즈마)
    "SM5+": "https://data1.pokemonkorea.co.kr/2018/03/2018-03-27_14-42-19-96152-1522129339.PNG",
    # 울트라포스 팩
    "SM5": "https://data1.pokemonkorea.co.kr/2018/03/2018-03-27_14-45-15-66896-1522129515.PNG",
    # GX 배틀부스트 팩
    "SM4a": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
    # REMASTER — 동일 하이클래스팩 아트 (공식 단일 팩)
    "SM7a": "https://data1.pokemonkorea.co.kr/2017/11/2017-11-23_17-15-43-42091-1511424943.png",
    # 빛나는 전설
    "SM2+": "https://data1.pokemonkorea.co.kr/2017/10/2017-10-24_18-33-58-94770-1508837638.png",
    # 얼터제네시스
    "SM12": "https://data1.pokemonkorea.co.kr/2019/11/2019-11-27_15-03-02-87345-1574834582.png",
    # 태그올스타즈 박스
    "SM12a": "https://data1.pokemonkorea.co.kr/2019/11/2019-11-27_14-58-02-27796-1574834282.png",
    # 더블블레이즈
    "SM10": "https://data1.pokemonkorea.co.kr/2019/05/2019-05-02_11-39-44-89132-1556764784.jpg",
    # 태그볼트 (포스터/경품안내 아님)
    "SM9a": "https://data1.pokemonkorea.co.kr/2019/01/2019-01-08_16-09-33-68309-1546931373.jpg",
    # 챔피언로드
    "SM6a": "https://data1.pokemonkorea.co.kr/2018/06/2018-06-22_18-47-50-16043-1529660870.png",
    # 반역크래시
    "S2": "https://data1.pokemonkorea.co.kr/2020/04/2020-04-09_15-43-53-72986-1586414633.png",
    # 초능력의 제왕
    "XY8a": "http://pokemonkorea.co.kr/templates/default/content_image/card/XY10_main_OuZo_4.jpg",
    # 20th Anniversary 3팩 제품샷
    "CP6": "https://data1.pokemonkorea.co.kr/2016/09/2016-09-20_13-45-22-59022-1474346722.jpg",
}

# 듀얼/포스터에서 크롭할 소스
CROPS: dict[str, tuple[str, tuple[int, int, int, int]]] = {
    # Ultra Sun / Ultra Moon 나란히
    "SM4": (
        "https://data1.pokemonkorea.co.kr/2018/01/2018-01-08_10-25-24-68181-1515374724.png",
        (0, 0, 155, 280),
    ),
    "SM4+": (
        "https://data1.pokemonkorea.co.kr/2018/01/2018-01-08_10-25-24-68181-1515374724.png",
        (155, 0, 310, 280),
    ),
    # 썬/문 컬렉션 나란히
    "SM1C": (
        "https://data1.pokemonkorea.co.kr/2017/01/2017-01-30_14-43-58-88992-1485755038.png",
        (0, 0, 155, 280),
    ),
    "SM1M": (
        "https://data1.pokemonkorea.co.kr/2017/01/2017-01-30_14-43-58-88992-1485755038.png",
        (155, 0, 310, 280),
    ),
    # 소드/실드 — VMAX 안내 포스터 속 팩
    "S1W": (
        "https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-07-55-87507-1580796475.png",
        (920, 1295, 1105, 1665),
    ),
    "S1H": (
        "https://data1.pokemonkorea.co.kr/2020/02/2020-02-04_15-07-55-87507-1580796475.png",
        (920, 1865, 1105, 2235),
    ),
}

# 시각 검증 시 기대 키워드 (파일명/메모용)
EXPECT: dict[str, str] = {
    "SM4": "울트라썬",
    "SM4+": "울트라문",
    "SM1C": "썬 컬렉션",
    "SM1M": "문 컬렉션",
    "S1W": "소드",
    "S1H": "실드",
    "SM5+": "금단의 빛",
    "SM5": "울트라포스",
    "SM4a": "GX 배틀부스트",
    "SM7a": "GX 배틀부스트",
    "SM9a": "태그볼트",
    "SM10": "더블블레이즈",
    "SM12": "얼터제네시스",
    "S2": "반역크래시",
    "SM2+": "빛나는 전설",
    "SM6a": "챔피언로드",
    "XY8a": "초능력의 제왕",
    "CP6": "20th",
    "SM12a": "태그올스타즈",
}


def download(url: str) -> bytes:
    r = client.get(url)
    r.raise_for_status()
    return r.content


def make_crops() -> dict[str, str]:
    """크롭 이미지를 public/set-boxes 에 저장하고 사이트 상대경로 반환"""
    cache: dict[str, Image.Image] = {}
    out: dict[str, str] = {}
    for code, (url, box) in CROPS.items():
        if url not in cache:
            raw = download(url)
            tmp = AUDIT / f"_src_{code}.bin"
            tmp.write_bytes(raw)
            cache[url] = Image.open(tmp).convert("RGBA")
        im = cache[url]
        crop = im.crop(box)
        # 업스케일해서 카드 그리드에서 덜 뭉개지게
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.LANCZOS)
        path = PUBLIC / f"{code.replace('+', 'plus')}.png"
        crop.save(path, optimize=True)
        # 검증용 복사
        crop.save(AUDIT / f"final_{code}.png")
        out[code] = f"/set-boxes/{path.name}"
        print(f"crop {code} -> {path.name} expect={EXPECT.get(code)} size={crop.size}")
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    local = make_crops()
    fixes: dict[str, str] = {**REMOTE_OK, **local}

    updated: list[KrSet] = []
    changed = []
    for s in KR_SETS:
        ns = s
        if s.code in fixes:
            new_url = fixes[s.code]
            if new_url != s.box_image_kr:
                changed.append((s.code, s.name_kr, s.box_image_kr, new_url))
                ns = replace(s, box_image_kr=new_url)
        if ns.box_image_kr:
            # 로컬 경로는 DB에도 저장 (프론트 preset이 우선)
            sb.table("card_sets").update({"image_url": ns.box_image_kr}).eq("set_code", s.code).execute()
        updated.append(ns)

    write_kr_sets(updated)
    ensure_kr_sets_footer()
    write_set_images(updated)

    print(f"\nupdated {len(changed)} sets:")
    for code, name, old, new in changed:
        print(f"  {code} ({name})")
        print(f"    - {(old or '')[-50:]}")
        print(f"    + {new}")


if __name__ == "__main__":
    main()
