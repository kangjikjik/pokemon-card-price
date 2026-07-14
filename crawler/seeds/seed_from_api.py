"""
[DEPRECATED] pokemontcg.io — 영미권 API, 한국 판과 불일치. 사용 금지.

대신 사용:
  - seeds/seed_jp_official.py  (일본 공식 카드)
  - seeds/seed_from_collectory.py  (collectory KR 세트)
  - seeds/kr_sets.py  (한국 발매일 마스터)
"""
import sys

print("ERROR: seed_from_api.py는 pokemontcg.io(영미권) 기반이라 사용하지 않습니다.")
print("  → seeds/seed_jp_official.py 또는 seeds/seed_from_collectory.py를 사용하세요.")
sys.exit(1)

# ─── 아래 코드는 참고용으로만 보존 ───

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
POKEMON_API_BASE = "https://api.pokemontcg.io/v2"

# ─── 희귀도 매핑 ─────────────────────────────────────────────────────────────
# pokemontcg.io 영어 희귀도명 → (DB 저장명, rarity_rank)
RARITY_MAP: dict[str, tuple[str, int]] = {
    "Special Illustration Rare": ("SAR", 6),
    "Hyper Rare":                ("UR",  7),
    "Illustration Rare":         ("IR",  4),
    "Double Rare":               ("RR",  3),
    "Ultra Rare":                ("UR-ex", 5),
    "Shiny Ultra Rare":          ("SUR", 8),
    "Shiny Rare":                ("SR",  2),
    "Rare Holo V":               ("V",   3),
    "Rare Holo VMAX":            ("VMAX",3),
    "Rare Holo VSTAR":           ("VSTAR",3),
}
TARGET_RARITIES = set(RARITY_MAP.keys())

# ─── 세트 매핑 ────────────────────────────────────────────────────────────────
# pokemontcg.io set ID → (DB set_code, 한국어 이름)
SET_MAP: dict[str, tuple[str, str]] = {
    "sv1":     ("SV1",    "스칼렛 & 바이올렛"),
    "sv2":     ("SV2",    "팔데아 에볼브드"),
    "sv3":     ("SV3",    "흑요 불꽃"),
    "sv3pt5":  ("SV2a",   "포켓몬 카드 151"),
    "sv4":     ("SV3a",   "역설의 균열"),
    "sv4pt5":  ("SV4",    "팔데아 페이트"),
    "sv5":     ("SV4a",   "시간의 가마우지"),
    "sv6":     ("SV5",    "트와일라잇 마스커레이드"),
    "sv6pt5":  ("SV5a",   "베일드 페이블"),
    "sv7":     ("SV6",    "스텔라 크라운"),
    "sv8":     ("SV6a",   "서징 스파크스"),
    "sv8pt5":  ("SV7",    "프리즈매틱 에볼루션"),
    "sv9":     ("SV8",    "저니 투게더"),
    "sv10":    ("SV9",    "데스티니 라이벌스"),
}

# ─── 카드 이름 한국어 매핑 (주요 카드만) ──────────────────────────────────────
NAME_KR: dict[str, str] = {
    "Charizard ex":          "리자몽 ex",
    "Mew ex":                "뮤 ex",
    "Pikachu ex":            "피카츄 ex",
    "Mewtwo ex":             "뮤츠 ex",
    "Eevee ex":              "이브이 ex",
    "Gardevoir ex":          "가디안 ex",
    "Miraidon ex":           "미라이돈 ex",
    "Koraidon ex":           "코라이돈 ex",
    "Palafin ex":            "물결손 ex",
    "Arcanine ex":           "윈디 ex",
    "Meowscarada ex":        "마스카니아 ex",
    "Skeledirge ex":         "코라이가 ex",
    "Quaquaval ex":          "퀄리아볼트 ex",
    "Iono":                  "이오나",
    "Professor's Research":  "박사의 연구",
    "Lusamine":              "루자민",
    "Sabrina's Suggestion":  "나쁜 선생님의 제안",
    "Venusaur ex":           "이상해꽃 ex",
    "Blastoise ex":          "거북왕 ex",
    "Alakazam ex":           "후딘 ex",
    "Aerodactyl ex":         "프테라 ex",
    "Zapdos ex":             "썬더 ex",
    "Moltres ex":            "파이어 ex",
    "Articuno ex":           "프리져 ex",
    "Ninetales ex":          "나인테일 ex",
    "Raichu ex":             "라이츄 ex",
    "Gyarados ex":           "갸라도스 ex",
    "Gengar ex":             "팬텀 ex",
    "Dragonite ex":          "드래곤나이트 ex",
    "Snorlax":               "잠만보",
    "Mamoswine ex":          "맘모꾸리 ex",
    "Baxcalibur ex":         "카이류가 ex",
    "Iron Valiant ex":       "아이언 발리언트 ex",
    "Roaring Moon ex":       "미래의 달 ex",
    "Shaymin ex":            "쉐이미 ex",
    "Comfey":                "포포모",
    "Radiant Charizard":     "빛나는 리자몽",
    "Radiant Gardevoir":     "빛나는 가디안",
    "Radiant Blastoise":     "빛나는 거북왕",
    "Umbreon VMAX":          "블래키 VMAX",
    "Leafeon VMAX":          "리피아 VMAX",
    "Sylveon VMAX":          "님피아 VMAX",
    "Espeon VMAX":           "에브이 VMAX",
    "Glaceon VMAX":          "글레이시아 VMAX",
    "Flareon VMAX":          "부스터 VMAX",
    "Jolteon VMAX":          "쥬피썬더 VMAX",
    "Vaporeon VMAX":         "샤워즈 VMAX",
    "Toxtricity VMAX":       "독침붕 VMAX",
    "Rayquaza VMAX":         "레쿠쟈 VMAX",
    "Duraludon VMAX":        "두랄루돈 VMAX",
    "Zacian V":              "자시안 V",
    "Zamazenta V":           "자마젠타 V",
    "Eternatus VMAX":        "에테르나투스 VMAX",
}

# ─── 그라디언트 컬러 매핑 ─────────────────────────────────────────────────────
def get_image_color(pokemon_name: str) -> str:
    colors: dict[str, str] = {
        "Charizard": "from-orange-500 via-red-600 to-rose-700",
        "Mew":       "from-pink-400 via-fuchsia-500 to-purple-600",
        "Pikachu":   "from-yellow-300 via-yellow-400 to-amber-500",
        "Mewtwo":    "from-purple-500 via-violet-600 to-indigo-700",
        "Eevee":     "from-amber-400 via-orange-400 to-yellow-500",
        "Gardevoir": "from-green-300 via-teal-400 to-emerald-500",
        "Miraidon":  "from-blue-400 via-cyan-500 to-teal-600",
        "Koraidon":  "from-red-500 via-orange-600 to-amber-700",
        "Umbreon":   "from-yellow-400 via-gray-800 to-black",
        "Rayquaza":  "from-emerald-500 via-green-600 to-lime-700",
        "Sylveon":   "from-pink-300 via-rose-400 to-fuchsia-500",
        "Vaporeon":  "from-blue-400 via-cyan-500 to-sky-600",
        "Glaceon":   "from-sky-300 via-blue-400 to-indigo-500",
        "Leafeon":   "from-green-400 via-lime-500 to-emerald-600",
        "Espeon":    "from-purple-400 via-violet-500 to-fuchsia-600",
    }
    for pokemon, color in colors.items():
        if pokemon.lower() in pokemon_name.lower():
            return color
    return "from-slate-600 via-slate-700 to-slate-800"


async def fetch_sv_sets(client: httpx.AsyncClient) -> list[dict]:
    """SV 시리즈 세트 목록 가져오기"""
    resp = await client.get(
        f"{POKEMON_API_BASE}/sets",
        params={"q": 'series:"Scarlet & Violet"', "pageSize": "50"},
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


async def fetch_cards_for_rarity(
    client: httpx.AsyncClient, set_id: str, rarity: str
) -> list[dict]:
    """특정 세트+희귀도 카드 가져오기 (단순 쿼리)"""
    resp = await client.get(
        f"{POKEMON_API_BASE}/cards",
        params={
            "q":        f'set.id:{set_id} rarity:"{rarity}"',
            "pageSize": "250",
            "select":   "id,name,number,rarity,images",
        },
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


async def fetch_cards_for_set(
    client: httpx.AsyncClient, set_id: str
) -> list[dict]:
    """특정 세트에서 고희귀 카드 전부 가져오기 (희귀도별 순차 요청)"""
    all_cards: list[dict] = []
    seen_ids: set[str] = set()

    for rarity in TARGET_RARITIES:
        try:
            cards = await fetch_cards_for_rarity(client, set_id, rarity)
            for card in cards:
                if card["id"] not in seen_ids:
                    seen_ids.add(card["id"])
                    all_cards.append(card)
            await asyncio.sleep(0.2)  # API rate limit
        except Exception as e:
            print(f"    [경고] {rarity} 조회 실패: {e}")
            continue

    return all_cards


def upsert_set(supabase_client, api_set: dict) -> int | None:
    """card_sets 테이블에 세트 upsert, 저장된 id 반환"""
    set_id = api_set["id"]
    if set_id not in SET_MAP:
        return None

    set_code, name_kr = SET_MAP[set_id]
    released_at = api_set.get("releaseDate", "").replace("/", "-") or None

    result = (
        supabase_client.table("card_sets")
        .upsert(
            {
                "set_code":    set_code,
                "name_kr":     name_kr,
                "name_en":     api_set.get("name", ""),
                "released_at": released_at,
            },
            on_conflict="set_code",
        )
        .execute()
    )
    if result.data:
        return result.data[0]["id"]

    # upsert가 빈 data 반환 시 select로 조회
    existing = (
        supabase_client.table("card_sets")
        .select("id")
        .eq("set_code", set_code)
        .execute()
    )
    return existing.data[0]["id"] if existing.data else None


def upsert_card(supabase_client, card: dict, db_set_id: int) -> bool:
    """cards 테이블에 카드 upsert"""
    rarity_en = card.get("rarity", "")
    rarity_db, rarity_rank = RARITY_MAP.get(rarity_en, (rarity_en, 0))

    name_en = card.get("name", "")
    name_kr = NAME_KR.get(name_en, "")  # 매핑 없으면 빈 문자열

    image_url = (
        card.get("images", {}).get("large")
        or card.get("images", {}).get("small")
        or ""
    )
    image_color = get_image_color(name_en)
    card_number = card.get("number", "")

    # (set_id, card_number) 기준 중복 방지 → upsert 전 존재 확인
    existing = (
        supabase_client.table("cards")
        .select("id")
        .eq("set_id", db_set_id)
        .eq("card_number", card_number)
        .execute()
    )
    payload = {
        "set_id":      db_set_id,
        "card_number": card_number,
        "name_kr":     name_kr,
        "name_en":     name_en,
        "rarity":      rarity_db,
        "rarity_rank": rarity_rank,
        "image_url":   image_url,
        "image_color": image_color,
    }

    if existing.data:
        # 이미 존재 → update (이미지 URL만 갱신)
        supabase_client.table("cards").update(
            {"image_url": image_url, "name_en": name_en, "rarity": rarity_db}
        ).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase_client.table("cards").insert(payload).execute()

    return True


async def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("[ERROR] .env에 SUPABASE_URL, SUPABASE_SERVICE_KEY가 필요합니다.")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    headers = {
        "Accept":     "application/json",
        "User-Agent": "PokePriceSeeder/1.0",
    }
    # POKEMON_TCG_API_KEY 환경변수가 있으면 헤더에 추가 (없어도 동작)
    api_key = os.getenv("POKEMON_TCG_API_KEY", "").strip()
    if api_key:
        headers["X-Api-Key"] = api_key
        print("[API] API 키 사용")
    else:
        print("[API] API 키 없음 - 무료 요청으로 진행 (일 1,000회 제한)")

    total_sets = 0
    total_cards = 0

    async with httpx.AsyncClient(headers=headers, timeout=60) as client:
        print("\n[1/3] SV 시리즈 세트 목록 가져오는 중...")
        api_sets = await fetch_sv_sets(client)
        sv_sets = [s for s in api_sets if s["id"] in SET_MAP]
        print(f"    대상 세트: {len(sv_sets)}개 (전체 SV 중 매핑된 것)")

        for api_set in sv_sets:
            set_id = api_set["id"]
            set_code, name_kr = SET_MAP[set_id]
            print(f"\n[세트] {name_kr} ({set_code}) ...")

            db_set_id = upsert_set(sb, api_set)
            if db_set_id is None:
                print("  -> DB 저장 실패, 스킵")
                continue
            total_sets += 1

            # 카드 가져오기 (희귀도별 요청)
            set_card_count = 0
            cards = await fetch_cards_for_set(client, set_id)
            for card in cards:
                ok = upsert_card(sb, card, db_set_id)
                if ok:
                    set_card_count += 1
                    total_cards += 1

            print(f"  -> 저장 완료: {set_card_count}장")

    print(f"\n[완료] 세트 {total_sets}개, 카드 {total_cards}장 DB 저장 완료")


if __name__ == "__main__":
    asyncio.run(main())
