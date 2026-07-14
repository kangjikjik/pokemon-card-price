"""
일본어 카드명 → 공식 한국어 명칭 변환 스크립트
실행: python -m seeds.update_kr_from_jp  (crawler/ 폴더 안에서)

1. PokeAPI에서 포켓몬 종족명 ja/ko 매핑 자동 생성
2. 트레이너/접두사(メガ 등) 수동 매핑
3. cards.name_jp → name_kr 업데이트
"""

import os
import re
import sys
import time
import json
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ─── 접두사/접미사 매핑 ─────────────────────────────────────────────────────
PREFIX_MAP = {
    "メガ": "메가",
    "ウルトラ": "울트라",
    "ひかる": "빛나는 ",
    "かがやく": "빛나는 ",
    "アローラ": "알로라 ",
    "ガラル": "가라르 ",
    "ヒスイ": "히스이 ",
    "パルデア": "팔데아 ",
}

SUFFIX_KEEP = {"ex", "EX", "V", "VMAX", "VSTAR", "GX"}

# ─── 트레이너/아이템 카드 (일본어 → 한국어) ─────────────────────────────────
TRAINER_JP_KR: dict[str, str] = {
    "オーリム博士の気迫": "오림박사의 기백",
    "センリ": "센리",
    "メロコ": "멜로코",
    "ネモ": "네모",
    "ペパー": "페퍼",
    "ボタン": "보따리",
    "ナンジャモ": "난자모",
    "オルティガ": "올티가",
    "ゼイユ": "제이유",
    "スグリ": "스구리",
    "アカマツ": "아카마츠",
    "スイレン": "수련",
    "マオ": "마오",
    "リーリエ": "릴리에",
    "グズマ": "구즈마",
    "リーリエの決心": "릴리에의 결심",
    "ナンジャモのハイテク": "난자모의 하이테크",
    "ボスの指令": "보스의 지령",
    "博士の研究": "박사의 연구",
    "ふしぎなアメ": "이상한사탕",
    "ふしぎなアメセット": "이상한사탕 세트",
    "ネストボール": "네스트볼",
    "ハイパーボール": "하이퍼볼",
    "スーパーボール": "슈퍼볼",
    "モンスターボール": "몬스터볼",
    "ふしぎなアメ": "이상한사탕",
    "エネルギー回収": "에너지 재생",
    "スーパーエネルギー回収": "슈퍼 에너지 재생",
    "基本草エネルギー": "기본 풀 에너지",
    "基本炎エネルギー": "기본 불꽃 에너지",
    "基本水エネルギー": "기본 물 에너지",
    "基本雷エネルギー": "기본 번개 에너지",
    "基本超エネルギー": "기본 에스퍼 에너ギー",
    "基本闘エネルギー": "기본 격투 에너ギー",
    "基本悪エネルギー": "기본 악 에너지",
    "基本鋼エネルギー": "기본 강철 에너ギー",
    "ジャッジマン": "저지맨",
    "ネルケ": "넬케",
    "パルデアの学生": "팔데아 학생",
    "N": "N",
    "ロケット団": "로켓단",
    "エリカ": "이바키",
    "サカキ": "비주기",
    "ホップ": "호프",
    "マリィ": "마리",
    "ダイゴ": "대웅",
    "ヒビキ": "히ビ키",
    "シロナ": "시로나",
    "ミカン": "미캔",
    "スピンロトム": "스핀로토무",
    "ミカンのまなざし": "미캔의 눈빛",
    "ヒビキのマグカルゴ": "히비키의 마그마단더",
    "ホップのザシアンex": "호프의 자시안 ex",
    "ホップのウールー": "호프의 울버꼬",
    "ホップのオーロット": "호프의 대로트",
    "マリィのオーロンゲex": "마리의 오롱털 ex",
    "ダイゴのメタグロスex": "대웅의 메타그로스 ex",
    "シロナのミカルゲ": "시로나의 화강돌",
    "ガラル タチフサグマ": "가라르 가로막구리",
    "ナナミ": "나나미",
    "マサキ": "이수",
    "アオキ": "아오키",
    "シキミ": "시키미",
    "チリ": "칠리",
    "パラソルおねえさん": "페어리콩 언니",
    "サワロ": "사구아로",
    "アイリス": "아이리스",
    "タケシ": "이수",
    "アクロマ": "아크로마",
    "アンズ": "앙즈",
    "カシオペア": "카시오페아",
    "クセロシキ": "크세로시키",
    "ジニア": "지니아",
    "スター団": "스타단",
    "カエデ": "단풍",
    "ミモザ": "미라",
    "サーファー": "서퍼",
    "シアノ": "시아노",
    "シトロン": "시트론",
    "Raifort": "레이포트",
    "Tyme": "타임",
    "Friends in Paldea": "팔데아의 친구들",
    "エリカの招待": "이바키의 초대",
    "サカキのカリスマ": "비주기의 카리스마",
    "ナナミの手助け": "나나미의 도움",
    "マサキの転送": "이수의 이동",
    "アイリスの闘志": "아이리스의 투지",
    "怖いお兄さん": "무서운 오빠",
    "タケシのスカウト": "이수의 스카우트",
    "アクロマの執念": "아크로마의 집념",
    "アンズの秘技": "앙즈의 비기",
    "クセロシキのたくらみ": "크세로시키의 책략",
    "スター団のしたっぱ": "스타단 조무래기",
    "Nのポイントアップ": "N의 포인트 업",
    "ガラスのラッパ": "유리 뿔피리",
    "ロケット団のレシーバー": "로켓단 리시버",
    "シトロンの機転": "시트론의 기전",
    "カウンターゲイン": "카운터 게인",
    "カナリィ": "카나리",
    "からておうの稽古": "태권왕의 가르침",
    "バーベナとヘレナ": "베르베나와 헬레나",
    "ジャミングタワー": "재밍 타워",
    "ミカンのまなざし": "미카ン의 눈빛",
}


def fetch_pokemon_names() -> dict[str, str]:
    """PokeAPI에서 ja→ko 포켓몬 이름 매핑 생성 (캐시 사용)"""
    cache_path = Path(__file__).parent / "jp_kr_pokemon_cache.json"
    if cache_path.exists():
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"[캐시] 포켓몬 매핑 {len(data)}개 로드")
        return data

    jp_to_kr: dict[str, str] = {}
    print("[PokeAPI] 포켓몬 이름 매핑 수집 중...")

    with httpx.Client(timeout=30) as client:
        # 전체 포켓몬 species 목록
        resp = client.get("https://pokeapi.co/api/v2/pokemon-species?limit=1025")
        resp.raise_for_status()
        results = resp.json()["results"]

        for i, item in enumerate(results):
            try:
                r = client.get(item["url"])
                data = r.json()
                ja_name = ""
                ko_name = ""
                for n in data.get("names", []):
                    lang = n["language"]["name"]
                    if lang in ("ja-hrkt", "ja"):
                        ja_name = n["name"]
                    elif lang == "ko":
                        ko_name = n["name"]
                if ja_name and ko_name:
                    jp_to_kr[ja_name] = ko_name
                if (i + 1) % 100 == 0:
                    print(f"  {i + 1}/{len(results)} 처리...")
                time.sleep(0.05)
            except Exception:
                continue

    print(f"  포켓몬 매핑 {len(jp_to_kr)}개 생성")
    cache_path.write_text(json.dumps(jp_to_kr, ensure_ascii=False, indent=2), encoding="utf-8")
    return jp_to_kr


def fetch_en_to_kr() -> dict[str, str]:
    """PokeAPI 캐시에서 en→ko 매핑 생성"""
    cache_path = Path(__file__).parent / "en_kr_pokemon_cache.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    en_to_kr: dict[str, str] = {}
    print("[PokeAPI] 영어→한국어 매핑 수집 중...")
    with httpx.Client(timeout=30) as client:
        resp = client.get("https://pokeapi.co/api/v2/pokemon-species?limit=1025")
        for item in resp.json()["results"]:
            try:
                data = client.get(item["url"]).json()
                en_name = ko_name = ""
                for n in data.get("names", []):
                    if n["language"]["name"] == "en":
                        en_name = n["name"]
                    elif n["language"]["name"] == "ko":
                        ko_name = n["name"]
                if en_name and ko_name:
                    en_to_kr[en_name] = ko_name
                time.sleep(0.03)
            except Exception:
                continue
    cache_path.write_text(json.dumps(en_to_kr, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  영어 매핑 {len(en_to_kr)}개")
    return en_to_kr


def translate_en_name(name_en: str, en_to_kr: dict[str, str]) -> str:
    """영어 카드명 → 한국어 (포켓몬 이름 기반)"""
    if not name_en:
        return ""
    if name_en in TRAINER_JP_KR.values():
        return name_en

    result = name_en
    # 접두사
    for prefix, kr_prefix in [("Mega ", "메가"), ("Radiant ", "빛나는 "), ("Team Rocket's ", "로켓단의 ")]:
        if result.startswith(prefix):
            result = kr_prefix + result[len(prefix):]
            break

    suffix = ""
    for suf in [" VMAX", " VSTAR", " V", " ex", " EX", " GX"]:
        if result.endswith(suf):
            suffix = suf.replace(" ex", " ex").replace(" EX", " ex")
            if suf.strip().lower() == "ex":
                suffix = " ex"
            elif suf == " VMAX":
                suffix = " VMAX"
            elif suf == " VSTAR":
                suffix = " VSTAR"
            elif suf == " V":
                suffix = " V"
            elif suf == " GX":
                suffix = " GX"
            result = result[: -len(suf)]
            break

    translated = False
    for en_name in sorted(en_to_kr.keys(), key=len, reverse=True):
        if en_name.lower() in result.lower():
            idx = result.lower().find(en_name.lower())
            result = result[:idx] + en_to_kr[en_name] + result[idx + len(en_name):]
            translated = True
            break
    if not translated and result in en_to_kr:
        result = en_to_kr[result]
        translated = True
    return (result + suffix) if translated else ""


def translate_name(name_jp: str, jp_to_kr: dict[str, str]) -> str:
    """일본어 카드명 → 한국어 변환"""
    if not name_jp:
        return ""

    # 트레이너 카드 전체 매칭
    if name_jp in TRAINER_JP_KR:
        return TRAINER_JP_KR[name_jp]

    # 트레이너의 포켓몬 (例: ナンジャモのハラバリーex, Nのゾロアークex)
    if "の" in name_jp and name_jp not in TRAINER_JP_KR:
        trainer_part, rest = name_jp.split("の", 1)
        trainer_kr = TRAINER_JP_KR.get(trainer_part, "")
        if trainer_kr:
            rest_kr = translate_name(rest, jp_to_kr)
            if rest_kr:
                return trainer_kr + "의 " + rest_kr

    result = name_jp

    # 접두사 변환
    for jp_prefix, kr_prefix in PREFIX_MAP.items():
        if result.startswith(jp_prefix):
            result = kr_prefix + result[len(jp_prefix):]
            break

    # 접미사 분리 (ex, V 등)
    suffix = ""
    for suf in sorted(SUFFIX_KEEP, key=len, reverse=True):
        if result.endswith(suf):
            suffix = suf
            result = result[: -len(suf)]
            break

    # 포켓몬 이름 매칭 (긴 이름 우선) - 전체 문자열 치환
    translated = False
    for jp_name in sorted(jp_to_kr.keys(), key=len, reverse=True):
        if jp_name in result:
            result = result.replace(jp_name, jp_to_kr[jp_name], 1)
            translated = True
            break

    if not translated and result in jp_to_kr:
        result = jp_to_kr[result]
        translated = True

    if not translated:
        return ""  # 변환 실패

    if suffix.lower() == "ex":
        return result + " ex"
    return result + suffix


def fetch_all_cards(sb) -> list[dict]:
    """Supabase 1000건 제한 우회 — 전체 cards 조회"""
    all_cards: list[dict] = []
    offset = 0
    page_size = 1000
    while True:
        batch = (
            sb.table("cards")
            .select("id, name_jp, name_en, name_kr, set_id")
            .range(offset, offset + page_size - 1)
            .execute()
            .data or []
        )
        all_cards.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return all_cards


def has_hangul(text: str) -> bool:
    return bool(re.search(r"[\uAC00-\uD7A3]", text))


def has_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", text or ""))


def needs_retranslation(kr: str, jp: str) -> bool:
    """한글이 있어도 일본어 잔존·번역 실패면 재번역"""
    kr = (kr or "").strip()
    jp = (jp or "").strip()
    if not kr:
        return True
    if jp and kr == jp:
        return True
    if has_japanese(kr):
        return True
    return False


def update_kr_names(sb, jp_to_kr: dict[str, str], en_to_kr: dict[str, str]) -> tuple[int, int]:
    """DB 카드 name_kr 업데이트"""
    cards = fetch_all_cards(sb)
    print(f"  전체 카드 {len(cards)}장 조회")

    updated = 0
    skipped = 0

    for card in cards:
        kr = (card.get("name_kr") or "").strip()
        jp = (card.get("name_jp") or "").strip()
        en = (card.get("name_en") or "").strip()

        if not needs_retranslation(kr, jp):
            skipped += 1
            continue

        new_kr = ""
        if jp:
            new_kr = translate_name(jp, jp_to_kr)
        if not new_kr and en:
            new_kr = translate_en_name(en, en_to_kr)

        if new_kr and new_kr != kr:
            sb.table("cards").update({"name_kr": new_kr}).eq("id", card["id"]).execute()
            updated += 1
        else:
            skipped += 1

    return updated, skipped


def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("[ERROR] .env에 SUPABASE_URL, SUPABASE_SERVICE_KEY가 필요합니다.")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    jp_to_kr = fetch_pokemon_names()
    en_to_kr = fetch_en_to_kr()

    print("\n[한국어 이름 업데이트] 시작...")
    updated, skipped = update_kr_names(sb, jp_to_kr, en_to_kr)
    print(f"[완료] {updated}개 업데이트, {skipped}개 스킵 (이미 한국어 있음)")

    # 수동 매핑 테이블로 추가 업데이트
    print("\n[수동 매핑 업데이트]...")
    from seeds.update_kr_names import update_names
    en_updated = update_names(sb)
    print(f"[완료] 수동 매핑 {en_updated}개 추가")


if __name__ == "__main__":
    main()
