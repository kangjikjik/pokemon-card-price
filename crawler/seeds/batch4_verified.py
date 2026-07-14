"""4배치 12팩 — pokemoncard.co.kr 검증값"""
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

BATCH4_VERIFIED: list[VerifiedSet] = [
    VerifiedSet(
        "XY8a", "초능력의 제왕", "2016-03-01",
        "https://data1.pokemonkorea.co.kr/2017/03/2017-03-27_19-13-10-32504-1490609590.jpg",
        "BS2016020-kr", "0029de8f-0609-4bba-a4eb-acbf7b533166",
        500, 15000, 65,
    ),
    VerifiedSet(
        "XY7", "밴디트링", "2015-07-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/XY7_main_3.jpg",
        "BS2015005", "1d133607-7792-460c-b3fe-5bc66a0c4635",
        500, 15000, 50,
    ),
    VerifiedSet(
        "XY6", "에메랄드 브레이크", "2015-04-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/XY6_main_2.jpg",
        "BS2015004", "31ef7dd6-3e18-46aa-b953-6aaaba74c0d4",
        500, 15000, 47,
    ),
    VerifiedSet(
        "XY5a", "가이아 볼케이노", "2015-02-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/XY5_main.jpg",
        "BS2015001", "342d60bd-9d23-48e2-9ca7-257aa9994c73",
        500, 15000, 44,
    ),
    VerifiedSet(
        "XY5b", "타이달스톰", "2015-02-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/XY5_main.jpg",
        "BS2015002-kr", "17829e68-80bd-4964-9031-78ccf0a55715",
        500, 15000, 44,
    ),
    VerifiedSet(
        "XY4", "팬텀게이트", "2014-11-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/XY4_main_5.jpg",
        "BS2014004", "0feace80-0157-4c85-b805-702c1cf22bf4",
        500, 15000, 40,
    ),
    VerifiedSet(
        "XY3", "라이징피스트", "2014-08-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/XY3_main_6.jpg",
        "BS2014003", "a08a8183-fdb3-4265-aa5a-f2efab9dcdd4",
        500, 15000, 36,
    ),
    VerifiedSet(
        "XY2", "와일드 블레이즈", "2014-05-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/XY2_main_7.jpg",
        "BS2014002", "7cddc814-9b66-4272-8dd2-aa8d50f1ef8e",
        500, 15000, 33,
    ),
    VerifiedSet(
        "EBB1", "EX 배틀 부스트", "2013-11-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_ex_battle_boost.png",
        "BS2013006", "b72f19e0-54b5-4ebd-aa86-8c845a60d906",
        1000, 30000, 27,
    ),
    VerifiedSet(
        "XY5", "메갈로캐논", "2013-09-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_mc.png",
        "BS2013005", "10833668-508d-48fd-bb4c-dbac817f40b1",
        1000, 30000, 25,
    ),
    VerifiedSet(
        "XY3a", "플라스마게일", "2013-03-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_plazmagail.png",
        "BS2013001", "9ea08e23-7a1d-40a6-a297-ea914601359c",
        1000, 30000, 9,
    ),
    VerifiedSet(
        "BW4", "다크러시", "2012-05-01",
        "http://pokemonkorea.co.kr/templates/default/content_image/card/card_main_darkrush.png",
        "BS2012003", "4883aa9b-6109-4bd8-a977-ef2e8225d93a",
        1000, 30000, 13,
    ),
]

BATCH4_CODES = [s.code for s in BATCH4_VERIFIED]
