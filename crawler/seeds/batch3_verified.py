"""3배치 15팩 — pokemoncard.co.kr 검증값"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedSet:
    code: str
    name_kr: str
    released_at: str
    box_image_kr: str
    bs_code: str
    collectory_id: str
    msrp_pack_kr: int
    msrp_box_kr: int
    pokemoncard_page: int


BATCH3_VERIFIED: list[VerifiedSet] = [
    VerifiedSet(
        "SM6b", "창공의 카리스마", "2018-07-24",
        "https://data1.pokemonkorea.co.kr/2018/07/2018-07-26_17-42-28-79039-1532594548.png",
        "BS2018007-kr", "1f9f7fe1-34e3-4a35-afe9-b5d8ad7b0eba",
        500, 15000, 140,
    ),
    VerifiedSet(
        "SM6a", "챔피언로드", "2018-07-02",
        "https://data1.pokemonkorea.co.kr/2018/07/2018-07-03_11-26-15-16972-1530584775.png",
        "BS2018006-kr", "8175597b-51c4-4539-8486-cecb02327c68",
        1000, 20000, 137,
    ),
    VerifiedSet(
        "SM6", "드래곤스톰", "2018-06-01",
        "https://data1.pokemonkorea.co.kr/2018/06/2018-06-01_14-26-37-73162-1527830797.png",
        "BS2018005", "4f6f3f53-a199-4b71-bb40-177fad8d67a4",
        1000, 20000, 132,
    ),
    VerifiedSet(
        "SM5+", "금단의 빛", "2018-04-06",
        "https://data1.pokemonkorea.co.kr/2018/04/2018-04-05_09-59-29-28708-1522889969.png",
        "BS2018004-kr", "f034798c-ec54-4f52-8c43-a870a9fd6e68",
        500, 15000, 130,
    ),
    VerifiedSet(
        "SM5", "울트라포스", "2018-03-08",
        "https://data1.pokemonkorea.co.kr/2018/03/2018-03-27_14-45-15-66896-1522129515.PNG",
        "BS2018003", "b236bc3d-dcc2-42e5-80eb-a2f11d08e989",
        1000, 20000, 128,
    ),
    VerifiedSet(
        "SM4+", "울트라문", "2018-01-17",
        "https://data1.pokemonkorea.co.kr/2018/01/2018-01-24_11-15-48-50264-1516760148.png",
        "BS2018002-kr", "47b92c00-62b4-4368-b1db-a11571af0264",
        500, 15000, 124,
    ),
    VerifiedSet(
        "SM4", "울트라썬", "2018-01-17",
        "https://data1.pokemonkorea.co.kr/2018/01/2018-01-24_11-15-48-50264-1516760148.png",
        "BS2018001-kr", "02accc63-f4f0-4e0f-bc9e-565b9e83271d",
        500, 15000, 124,
    ),
    VerifiedSet(
        "SM4a", "GX 배틀부스트", "2017-12-13",
        "https://data1.pokemonkorea.co.kr/2017/12/2017-12-13_10-44-40-86175-1513129480.jpg",
        "BS2017013", "9d7b69c4-0300-467a-a42f-bc3257b60283",
        2000, 30000, 120,
    ),
    VerifiedSet(
        "SM2+", "빛나는 전설", "2017-11-09",
        "https://data1.pokemonkorea.co.kr/2017/11/2017-11-09_19-22-40-59966-1510222960.jpg",
        "BS2017010", "cbb990d6-3ed7-4c22-8eff-f808eda5beec",
        1000, 20000, 118,
    ),
    VerifiedSet(
        "SM1+", "새로운 시련", "2017-05-26",
        "https://data1.pokemonkorea.co.kr/2017/05/2017-05-19_19-37-39-76242-1495190259.jpg",
        "BS2017007", "56ce43c3-d8de-4bbd-87a7-c4249dc3d007",
        1000, 20000, 110,
    ),
    VerifiedSet(
        "SM1M", "문 컬렉션", "2017-02-09",
        "https://data1.pokemonkorea.co.kr/2017/02/2017-02-13_10-16-01-29809-1486948561.jpg",
        "BS2017002-kr", "1f887b29-8f28-4f27-a565-2c0557953c7d",
        500, 15000, 99,
    ),
    VerifiedSet(
        "SM1C", "썬 컬렉션", "2017-02-09",
        "https://data1.pokemonkorea.co.kr/2017/02/2017-02-13_10-16-01-29809-1486948561.jpg",
        "BS2017001-kr", "758506ad-dbac-4bed-b715-fc4f2cafa864",
        500, 15000, 99,
    ),
    VerifiedSet(
        "CP6", "20th Anniversary", "2016-09-29",
        "https://data1.pokemonkorea.co.kr/2016/09/2016-09-29_10-34-19-38231-1475112859.jpg",
        "BS2016009", "c0496d08-e69c-48a5-8ab1-aad43a5e539b",
        1000, 20000, 89,
    ),
    VerifiedSet(
        "XY11", "타오르는 투사", "2016-07-26",
        "https://data1.pokemonkorea.co.kr/2016/07/2016-07-28_09-45-50-64547-1469666750.jpg",
        "BS2016006", "d2b7771a-aeba-4d2d-82cd-05465048089e",
        500, 15000, 83,
    ),
    VerifiedSet(
        "XY9", "천공의 분노", "2016-01-01",
        "https://data1.pokemonkorea.co.kr/2016/06/2016-06-20_00-44-39-61799-1466351079.jpg",
        "BS2016001", "e4ec98a5-7551-48c6-8f65-c74f022a1bb6",
        500, 15000, 62,
    ),
]

BATCH3_CODES = [s.code for s in BATCH3_VERIFIED]
