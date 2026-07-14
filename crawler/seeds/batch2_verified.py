"""2배치 15팩 — pokemoncard.co.kr 검증값"""
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


BATCH2_VERIFIED: list[VerifiedSet] = [
    VerifiedSet(
        "S2", "반역크래시", "2020-04-16",
        "https://data1.pokemonkorea.co.kr/2021/07/2021-07-30_13-41-27-64374-1627620087.png",
        "BS2020005-kr", "f2764878-6073-4691-8252-36a5feda61a6",
        1000, 30000, 297,
    ),
    VerifiedSet(
        "S1a", "VMAX라이징", "2020-03-26",
        "https://data1.pokemonkorea.co.kr/2020/03/2020-03-19_17-16-22-65387-1584605782.png",
        "BS2020004-kr", "68d9fa83-0786-4141-8e47-8eb2c4f31e99",
        1000, 30000, 291,
    ),
    VerifiedSet(
        "S1W", "소드", "2020-02-07",
        "https://data1.pokemonkorea.co.kr/2021/07/2021-07-30_13-41-27-64374-1627620087.png",
        "BS2020002", "17de57f7-83ed-44ef-8a8c-c532407ab394",
        1000, 30000, 286,
    ),
    VerifiedSet(
        "S1H", "실드", "2020-02-07",
        "https://data1.pokemonkorea.co.kr/2021/07/2021-07-30_13-41-27-64374-1627620087.png",
        "BS2020003", "5ddc68ce-514c-490b-846e-3c9dfca1bfd4",
        1000, 30000, 286,
    ),
    VerifiedSet(
        "SM12a", "TAG TEAM GX 태그올스타즈", "2019-12-06",
        "https://data1.pokemonkorea.co.kr/2019/12/2019-12-24_19-43-26-43898-1577184206.png",
        "BS2019017", "885b7cb1-7a47-4718-a8dd-eb2f929e881b",
        2000, 30000, 271,
    ),
    VerifiedSet(
        "SM12", "얼터제네시스", "2019-11-14",
        "https://data1.pokemonkorea.co.kr/2019/11/gms05_hover.png",
        "BS2019016-kr", "4391a84d-4cf6-494e-aaed-b32e4e78a60b",
        500, 15000, 261,
    ),
    VerifiedSet(
        "SM11b", "드림리그", "2019-10-11",
        "https://data1.pokemonkorea.co.kr/2019/10/2019-10-28_09-44-42-25011-1572223482.png",
        "BS2019015", "28af28cd-edcb-4234-8291-aabb5bc11593",
        1000, 20000, 257,
    ),
    VerifiedSet(
        "SM11a", "미라클트윈", "2019-08-07",
        "https://data1.pokemonkorea.co.kr/2019/09/2019-09-03_18-02-37-10300-1567501357.png",
        "BS2019013-kr", "8b6beb3d-422f-47a1-bf3d-d27f0ebbc489",
        500, 15000, 211,
    ),
    VerifiedSet(
        "SM10", "더블블레이즈", "2019-05-10",
        "https://data1.pokemonkorea.co.kr/2019/05/2019-05-10_13-56-08-88742-1557464168.png",
        "BS2019007-kr", "4702f8bc-f4c6-4a18-8c3d-ab60b1fb893d",
        500, 15000, 180,
    ),
    VerifiedSet(
        "SM9", "나이트유니슨", "2019-03-20",
        "https://data1.pokemonkorea.co.kr/2019/03/2019-03-19_19-16-12-98877-1552990572.png",
        "BS2019003-kr", "e73363cb-6e58-464b-b5e4-1eed097866cf",
        1000, 20000, 166,
    ),
    VerifiedSet(
        "SM8b", "GX 울트라샤이니", "2019-02-28",
        "https://data1.pokemonkorea.co.kr/2019/02/2019-02-28_17-59-01-53294-1551344341.png",
        "BS2019002", "1758a1f2-dca4-4956-8e8e-49468c486163",
        2000, 30000, 163,
    ),
    VerifiedSet(
        "SM9a", "태그볼트", "2019-01-16",
        "https://data1.pokemonkorea.co.kr/2019/01/2019-01-16_14-18-18-42584-1547615898.png",
        "BS2019001-kr", "ee356460-f869-4d0a-a611-b506b15c7048",
        500, 15000, 156,
    ),
    VerifiedSet(
        "SM8", "플라스마 스파크", "2018-11-15",
        "https://data1.pokemonkorea.co.kr/2018/11/2018-11-15_18-20-18-24380-1542273618.jpg",
        "BS2018012-kr", "d9a8e5c0-8fe5-4651-9d2a-f88fcd92fb90",
        1000, 20000, 152,
    ),
    VerifiedSet(
        "SM7", "버스트임팩트", "2018-10-16",
        "https://data1.pokemonkorea.co.kr/2018/10/2018-10-18_14-20-18-82250-1539840018.jpg",
        "BS2018010-kr", "cea23066-004d-4e9b-bb85-81ffe66cd644",
        500, 15000, 149,
    ),
    VerifiedSet(
        "SM7a", "GX 배틀부스트 REMASTER", "2017-12-13",
        "https://data1.pokemonkorea.co.kr/2017/12/2017-12-13_10-44-40-86175-1513129480.jpg",
        "BS2018011-kr", "662e9195-2eaa-480b-9286-35ae9e7f69b5",
        2000, 30000, 120,
    ),
]

BATCH2_CODES = [s.code for s in BATCH2_VERIFIED]
