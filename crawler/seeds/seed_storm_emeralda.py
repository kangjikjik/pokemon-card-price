"""
스톰에메랄다(MG7 / JP: M6) 카드 데이터 시드.

- 기본 76장 · 시크릿 37장 (AR 12 / SR 18 / SAR 6 / MUR 1) = 113장
- 발매일: 2026-08-21 (KR), 2026-07-31 (JP)
- 이미지: 기본 카드는 pokemon-card.com CDN (PG값 확인 필요 → 아래 TODO)
          시크릿 카드는 유유테이 front/m06/

실행:
  python -m seeds.seed_storm_emeralda
  python crawler/seeds/seed_storm_emeralda.py

TODO: pokemon-card.com/card-search/index.php 에서 MG7(M6) 세트를 열고
      URL의 ?pg=XXXX 값을 확인 후 아래 PG 변수를 업데이트하면
      기본 76장의 공식 카드 이미지를 자동으로 가져올 수 있습니다.
"""
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ──────────────────────────────────────────────────
# 세트 기본 정보
# ──────────────────────────────────────────────────
SET_CODE = "MG7"
NAME_KR = "스톰에메랄다"
NAME_JP = "ストームエメラルダ"
NAME_EN = "Storm Emeralda"
TOTAL_BASE = 76   # 카드번호 001/076 ~ 076/076

# 기본 카드 이미지: pokemon-card.com API (PG 값 확인 후 사용)
# TODO: 아래 PG 값을 실제 값으로 교체하세요 (MG6=954, MG7=?)
PG: str = "955"  # pokemon-card.com card-search pg param for M6 (Storm Emeralda)
JP_BASE_URL = "https://www.pokemon-card.com"

# 시크릿 카드 이미지: 유유테이 m06 디렉터리
YUYU_FRONT = "https://card.yuyu-tei.jp/poc/front/m06/{page_id}.jpg"

RARITY_RANK = {
    "MUR": 9, "SAR": 8, "SR": 7, "AR": 6, "ACE": 5,
    "RR": 4, "R": 3, "U": 2, "C": 1,
}

# ──────────────────────────────────────────────────
# 기본 76장 레어도 (기본값 C, 이 dict에 없으면 C)
# ──────────────────────────────────────────────────
BASE_RARITY: dict[int, str] = {
    # Double Rare (RR) — ex 카드
    9: "RR",   # 메가갑주무사 ex
    15: "RR",  # 히트로토무 ex
    21: "RR",  # 약어리 ex
    24: "RR",  # 라이코 ex
    33: "RR",  # 메가골루그 ex
    48: "RR",  # 메가칼라마네로 ex
    58: "RR",  # 메가레쿠쟈 ex
    62: "RR",  # 파이어로 ex
    # Rare (R)
    5: "R",    # 밤선인 (Cacturne)
    11: "R",   # 윈디 (Arcanine)
    18: "R",   # 가이오가 (Kyogre)
    31: "R",   # 기라티나 (Giratina)
    39: "R",   # 그란돈 (Groudon)
    43: "R",   # 니드퀸 (Nidoqueen)
    52: "R",   # 짜랑고우거 (Kommo-o)
    56: "R",   # 파비코리 (Altaria)
    # Uncommon (U) — 2~3진화·트레이너
    13: "U",   # 마그마번
    20: "U",   # 탱탱겔
    23: "U",   # 에레키블
    25: "U",   # 볼트로스
    28: "U",   # 찌리비크
    34: "U",   # 러브로스
    38: "U",   # 강철톤
    40: "U",   # 랜드로스
    49: "U",   # Druddigon (크리무간)
    59: "U",   # 토네로스
    64: "U",   # 모험의 등불
    65: "U",   # 커스텀 조끼
    66: "U",   # 메가레쿠쟈 캡
    68: "U",   # 아론
    69: "U",   # 피아나의 신뢰
    70: "U",   # 풍과 란의 수행
    71: "U",   # 전설의 해구 L
    72: "U",   # 전설의 해구 R
    73: "U",   # 전설의 산정 L
    74: "U",   # 전설의 산정 R
    75: "U",   # 전설의 용암호 L
    76: "U",   # 전설의 용암호 R
}

# ──────────────────────────────────────────────────
# 기본 76장 한글/일어명 전체 목록
# ──────────────────────────────────────────────────
# (num, name_kr, name_jp)
BASE_CARDS: list[tuple[int, str, str]] = [
    (1,  "헤라크로스",         "ヘラクロス"),
    (2,  "비구술",             "アメタマ"),
    (3,  "비나방",             "アメモース"),
    (4,  "선인왕",             "サボネア"),
    (5,  "밤선인",             "ノクタス"),
    (6,  "세꿀버리",           "ミツハニー"),
    (7,  "비퀸",               "ビークイン"),
    (8,  "꼬시레",             "コソクムシ"),
    (9,  "메가갑주무사 ex",    "メガグソクムシャex"),
    (10, "가디",               "ガーディ"),
    (11, "윈디",               "ウインディ"),
    (12, "마그마",             "ブーバー"),
    (13, "마그마번",           "ブーバーン"),
    (14, "코터스",             "コータス"),
    (15, "히트로토무 ex",      "ヒートロトムex"),
    (16, "앤티골",             "クイタラン"),
    (17, "만타인",             "マンタイン"),
    (18, "가이오가",           "カイオーガ"),
    (19, "탱그릴",             "プルリル"),
    (20, "탱탱겔",             "ブルンゲル"),
    (21, "약어리 ex",          "ヨワシex"),
    (22, "에레브",             "エレブー"),
    (23, "에레키블",           "エレキブル"),
    (24, "라이코 ex",          "ライコウex"),
    (25, "볼트로스",           "ボルトロス"),
    (26, "찌르성게",           "バチンウニ"),
    (27, "찌리비",             "カイデン"),
    (28, "찌리비크",           "タイカイデン"),
    (29, "슬리프",             "スリープ"),
    (30, "슬리퍼",             "スリーパー"),
    (31, "기라티나",           "ギラティナ"),
    (32, "골비람",             "ゴビット"),
    (33, "메가골루그 ex",      "メガゴルーグex"),
    (34, "러브로스",           "エナモリ"),
    (35, "모래두지",           "サンド"),
    (36, "고지",               "サンドパン"),
    (37, "롱스톤",             "イワーク"),
    (38, "강철톤",             "ハガネール"),
    (39, "그란돈",             "グラードン"),
    (40, "랜드로스",           "ランドロス"),
    (41, "니드런♀",            "ニドラン♀"),
    (42, "니드리나",           "ニドリーナ"),
    (43, "니드퀸",             "ニドクイン"),
    (44, "페이검",             "イトマル"),
    (45, "아리아도스",         "アリアドス"),
    (46, "깜까미",             "ヤミラミ"),
    (47, "오케이징",            "マーイーカ"),
    (48, "메가칼라마네로 ex",  "メガカラマネロex"),
    (49, "크리만",             "クリムガン"),
    (50, "짜랑꼬",             "ジャラコ"),
    (51, "짜랑고우",           "ジャランゴ"),
    (52, "짜랑고우거",         "ジャラランガ"),
    (53, "모토마",             "モトトカゲ"),
    (54, "루리리",             "ルリリ"),
    (55, "파비코",             "チルット"),
    (56, "파비코리",           "チルタリス"),
    (57, "켈리몬",             "カクレオン"),
    (58, "메가레쿠쟈 ex",      "メガレックウザex"),
    (59, "토네로스",           "トルネロス"),
    (60, "화살꼬빈",           "ヤヤコマ"),
    (61, "불화살빈",           "ヒノヤコマ"),
    (62, "파이어로 ex",        "ファイアローex"),
    (63, "맛있는 주먹밥",      "おいしいおむすび"),
    (64, "모험의 랜턴",        "ぼうけんのランタン"),
    (65, "커스텀 조끼",        "とくちゅうチョッキ"),
    (66, "메가레쿠쟈 캡",      "メガレックウザキャップ"),
    (67, "MC의 응원",          "MCの盛り上げ"),
    (68, "길리",               "ギリー"),
    (69, "히가나의 신뢰",      "ヒガナの信頼"),
    (70, "풍과 란의 수행",     "フウとランの修行"),
    (71, "전설의 해구 L",      "伝説の海溝"),
    (72, "전설의 해구 R",      "伝説の海溝"),
    (73, "전설의 산정 L",      "伝説の山頂"),
    (74, "전설의 산정 R",      "伝説の山頂"),
    (75, "전설의 용암동 L",    "伝説の溶岩洞"),
    (76, "전설의 용암동 R",    "伝説の溶岩洞"),
]

# ──────────────────────────────────────────────────
# 시크릿 카드 37장 (카드번호, 레어도, 일본어명, 한글명)
# ──────────────────────────────────────────────────
SECRET_CARDS: list[tuple[int, str, str, str]] = [
    # AR (077-088)
    (77,  "AR",  "アメモース",       "비나방"),
    (78,  "AR",  "ガーディ",         "가디"),
    (79,  "AR",  "ブーバーン",       "마그마번"),
    (80,  "AR",  "カイオーガ",       "가이오가"),
    (81,  "AR",  "エレキブル",       "에레키블"),
    (82,  "AR",  "バチンウニ",       "찌르성게"),
    (83,  "AR",  "エナモリ",         "러브로스"),
    (84,  "AR",  "グラードン",       "그란돈"),
    (85,  "AR",  "マーイーカ",       "오케이징"),
    (86,  "AR",  "ルリリ",           "루리리"),
    (87,  "AR",  "チルタリス",       "파비코리"),
    (88,  "AR",  "カクレオン",       "켈리몬"),
    # SR (089-106)
    (89,  "SR",  "メガグソクムシャex", "메가갑주무사 ex"),
    (90,  "SR",  "ヒートロトムex",   "히트로토무 ex"),
    (91,  "SR",  "ヨワシex",         "약어리 ex"),
    (92,  "SR",  "ライコウex",       "라이코 ex"),
    (93,  "SR",  "メガゴルーグex",   "메가골루그 ex"),
    (94,  "SR",  "メガカラマネロex", "메가칼라마네로 ex"),
    (95,  "SR",  "メガレックウザex", "메가레쿠쟈 ex"),
    (96,  "SR",  "ファイアローex",   "파이어로 ex"),
    (97,  "SR",  "ぼうけんのランタン",   "모험의 랜턴"),
    (98,  "SR",  "ポケモンキャッチャー", "포켓몬 캐처"),
    (99,  "SR",  "とくちゅうチョッキ",  "커스텀 조끼"),
    (100, "SR",  "MCの盛り上げ",        "MC의 응원"),
    (101, "SR",  "ギリー",              "길리"),
    (102, "SR",  "ヒガナの信頼",        "히가나의 신뢰"),
    (103, "SR",  "フウとランの修行",    "풍과 란의 수행"),
    (104, "SR",  "グロウ草エネルギー",  "그로우 풀 에너지"),
    (105, "SR",  "ニトロ炎エネルギー",  "니트로 불꽃 에너지"),
    (106, "SR",  "バブル水エネルギー",  "버블 물 에너지"),
    # SAR (107-112)
    (107, "SAR", "メガグソクムシャex", "메가갑주무사 ex"),
    (108, "SAR", "ライコウex",        "라이코 ex"),
    (109, "SAR", "メガゴルーグex",    "메가골루그 ex"),
    (110, "SAR", "メガレックウザex",  "메가레쿠쟈 ex"),
    (111, "SAR", "ギリー",             "길리"),
    (112, "SAR", "ヒガナの信頼",      "히가나의 신뢰"),
    # MUR (113)
    (113, "MUR", "メガレックウザex",  "메가레쿠쟈 ex"),
]

# ──────────────────────────────────────────────────
# 기본 카드 이미지 조회 (pokemon-card.com API)
# PG 값이 TODO이면 이미지 없이 저장
# ──────────────────────────────────────────────────
def _fetch_base_images(pg: str) -> dict[int, str]:
    """카드번호 -> 이미지 URL (pokemon-card.com API). PG='TODO'이면 빈 dict."""
    import urllib.request
    import json as _json

    if pg == "TODO":
        print("  [INFO] PG 미설정 -- 기본 카드 이미지 없이 저장합니다.")
        return {}

    all_cards: list = []
    for p in range(1, 8):
        url = f"{JP_BASE_URL}/card-search/resultAPI.php?pg={pg}&page={p}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = _json.loads(r.read())
            batch = data.get("cardList", [])
            if not batch:
                break
            all_cards.extend(batch)
            if p >= data.get("maxPage", 1):
                break
        except Exception as e:
            print(f"  [WARN] pg={pg} page={p} 페치 실패: {e}")
            break

    if not all_cards:
        return {}

    # cardID 오프셋: 첫 번째 카드(card #1)의 cardID - 1
    min_id = min(int(c.get("cardID", 0)) for c in all_cards if c.get("cardID"))
    offset = min_id - 1  # M6: 50339 - 1 = 50338

    images: dict[int, str] = {}
    for card in all_cards:
        thumb = card.get("cardThumbFile", "")
        card_id = int(card.get("cardID", 0))
        num = card_id - offset
        if 1 <= num <= TOTAL_BASE and thumb:
            images[num] = JP_BASE_URL + thumb
    print(f"  [INFO] 기본 카드 이미지 {len(images)}장 로드 완료 (offset={offset})")
    return images


def main() -> None:
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    # 기본 이미지 (PG 설정 시)
    image_map = _fetch_base_images(PG)

    # 박스 이미지: kr_sets.py 에서 가져옴
    import sys as _sys, pathlib as _pathlib
    _seeds_dir = _pathlib.Path(__file__).parent
    if str(_seeds_dir) not in _sys.path:
        _sys.path.insert(0, str(_seeds_dir))
    from kr_sets import KR_SETS
    _meta = next((s for s in KR_SETS if s.code == SET_CODE), None)
    box_image_kr = _meta.box_image_kr if _meta else ""

    # ─── card_sets upsert ───
    r = sb.table("card_sets").upsert(
        {
            "set_code": SET_CODE,
            "name_kr": NAME_KR,
            "name_jp": NAME_JP,
            "name_en": NAME_EN,
            "image_url": box_image_kr,
        },
        on_conflict="set_code",
    ).execute()
    set_id = r.data[0]["id"]
    print(f"[{NAME_KR}({SET_CODE})] set_id={set_id}")

    # ─── 기존 카드 삭제 ───
    sb.table("cards").delete().eq("set_id", set_id).execute()

    saved = 0

    # ─── 기본 76장 ───
    for num, name_kr, name_jp in BASE_CARDS:
        rarity = BASE_RARITY.get(num, "C")
        img = image_map.get(num, "")
        sb.table("cards").insert({
            "set_id": set_id,
            "name_jp": name_jp,
            "name_kr": name_kr,
            "name_en": "",
            "rarity": rarity,
            "rarity_rank": RARITY_RANK.get(rarity, 1),
            "image_url": img,
            "card_number": f"{num:03d}/076",
            "image_color": "from-emerald-600 via-teal-700 to-cyan-800",
        }).execute()
        saved += 1

    # ─── 시크릿 37장 ───
    for num, rarity, name_jp, name_kr in SECRET_CARDS:
        page_id = 10000 + num
        img = YUYU_FRONT.format(page_id=page_id)
        sb.table("cards").insert({
            "set_id": set_id,
            "name_jp": name_jp,
            "name_kr": name_kr,
            "name_en": "",
            "rarity": rarity,
            "rarity_rank": RARITY_RANK.get(rarity, 1),
            "image_url": img,
            "card_number": f"{num:03d}/076",
            "image_color": "from-amber-600 via-orange-700 to-red-800",
        }).execute()
        saved += 1

    from collections import Counter
    all_cards = sb.table("cards").select("rarity").eq("set_id", set_id).execute()
    counts = Counter(c["rarity"] for c in (all_cards.data or []))

    print(f"\n[완료] {saved}장 저장")
    for r_name, n in counts.most_common():
        print(f"  {r_name}: {n}장")
    if PG == "TODO":
        print("\n[주의]  기본 카드 이미지 없음 -- PG 값 설정 후 재실행 필요")


if __name__ == "__main__":
    main()
