"""
공식 한국어 카드 명칭 DB 업데이트 스크립트
실행: python -m seeds.update_kr_names  (crawler/ 폴더 안에서)

포켓몬 공식 한국어 명칭 기준으로 name_kr 필드를 업데이트합니다.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# ─── 공식 한국어 이름 매핑 ────────────────────────────────────────────────────
# 영어 이름 → 공식 한국어 이름 (한국 포켓몬코리아 공식 발매 명칭 기준)
KR_NAMES: dict[str, str] = {
    # ── 포켓몬 ex / VMAX / VSTAR ──────────────────────────────────────────────
    "Venusaur ex":           "이상해꽃 ex",
    "Charizard ex":          "리자몽 ex",
    "Blastoise ex":          "거북왕 ex",
    "Pikachu ex":            "피카츄 ex",
    "Raichu ex":             "라이츄 ex",
    "Ninetales ex":          "나인테일 ex",
    "Gyarados ex":           "갸라도스 ex",
    "Alakazam ex":           "후딘 ex",
    "Gengar ex":             "팬텀 ex",
    "Aerodactyl ex":         "프테라 ex",
    "Snorlax ex":            "잠만보 ex",
    "Dragonite ex":          "드래곤나이트 ex",
    "Mew ex":                "뮤 ex",
    "Mewtwo ex":             "뮤츠 ex",
    "Arcanine ex":           "윈디 ex",
    "Machamp ex":            "괴력몬 ex",
    "Golem ex":              "딱구리 ex",
    "Slowbro ex":            "야도란 ex",
    "Kangaskhan ex":         "캥카 ex",
    "Scyther ex":            "스라크 ex",
    "Jynx ex":               "루주라 ex",
    "Electabuzz ex":         "에레브 ex",
    "Magmar ex":             "마그마 ex",
    "Pinsir ex":             "쁘사이저 ex",
    "Tauros ex":             "켄타로스 ex",
    "Eevee ex":              "이브이 ex",
    "Vaporeon ex":           "샤워즈 ex",
    "Jolteon ex":            "쥬피썬더 ex",
    "Flareon ex":            "부스터 ex",
    "Porygon ex":            "폴리곤 ex",
    "Omanyte ex":            "암나이트 ex",
    "Omastar ex":            "암스타 ex",
    "Kabuto ex":             "투구 ex",
    "Kabutops ex":           "투구푸스 ex",
    "Articuno ex":           "프리져 ex",
    "Zapdos ex":             "썬더 ex",
    "Moltres ex":            "파이어 ex",
    # SV 시리즈
    "Miraidon ex":           "미라이돈 ex",
    "Koraidon ex":           "코라이돈 ex",
    "Gardevoir ex":          "가디안 ex",
    "Lucario ex":            "루카리오 ex",
    "Garchomp ex":           "한카리아스 ex",
    "Armarouge ex":          "가디엔 ex",
    "Ceruledge ex":          "기다검 ex",
    "Tyranitar ex":          "마기라스 ex",
    "Salamence ex":          "보만다 ex",
    "Espeon ex":             "에브이 ex",
    "Umbreon ex":            "블래키 ex",
    "Leafeon ex":            "리피아 ex",
    "Glaceon ex":            "글레이시아 ex",
    "Sylveon ex":            "님피아 ex",
    "Tinkaton ex":           "딱쇠쟁이 ex",
    "Kilowattrel ex":        "킬로와터 ex",
    "Palafin ex":            "물결손 ex",
    "Annihilape ex":         "열폭원숭 ex",
    "Maushold ex":           "가족쥐 ex",
    "Dudunsparce ex":        "두두파팡 ex",
    "Kingambit ex":          "흑철패왕 ex",
    "Baxcalibur ex":         "카이류가 ex",
    "Gholdengo ex":          "황금신칸 ex",
    "Iron Hands ex":         "아이언 핸즈 ex",
    "Iron Valiant ex":       "아이언 발리언트 ex",
    "Iron Leaves ex":        "아이언 리브스 ex",
    "Iron Boulder ex":       "아이언 볼더 ex",
    "Iron Crown ex":         "아이언 크라운 ex",
    "Roaring Moon ex":       "울부짖달 ex",
    "Walking Wake ex":       "달리는 워터스 ex",
    "Gouging Fire ex":       "타오르는 블레이즈 ex",
    "Raging Bolt ex":        "질주하는 썬더 ex",
    "Flutter Mane ex":       "나부끼는 메인 ex",
    "Scream Tail ex":        "울부짖는 테일 ex",
    "Sandy Shocks ex":       "번쩍이는 샌드 ex",
    "Slither Wing ex":       "꿈틀대는 윙 ex",
    "Groudon ex":            "그란돈 ex",
    "Kyogre ex":             "가이오가 ex",
    "Rayquaza ex":           "레쿠쟈 ex",
    "Latios ex":             "라티오스 ex",
    "Latias ex":             "라티아스 ex",
    "Deoxys ex":             "테오키스 ex",
    "Dialga ex":             "디아루가 ex",
    "Palkia ex":             "팔키아 ex",
    "Giratina ex":           "기라티나 ex",
    "Cresselia ex":          "크레세리아 ex",
    "Reshiram ex":           "레시라무 ex",
    "Zekrom ex":             "제크로무 ex",
    "Kyurem ex":             "큐레무 ex",
    "Xerneas ex":            "제르네아스 ex",
    "Yveltal ex":            "이벨타르 ex",
    "Zygarde ex":            "지가르데 ex",
    "Solgaleo ex":           "솔가레오 ex",
    "Lunala ex":             "루나아라 ex",
    "Necrozma ex":           "네크로즈마 ex",
    "Shaymin ex":            "쉐이미 ex",
    "Manaphy ex":            "마나피 ex",
    "Pecharunt ex":          "모모왐 ex",
    "Munkidori ex":          "후루야데 ex",
    "Okidogi ex":            "오키도기 ex",
    "Fezandipiti ex":        "페잔디피티 ex",
    # ── 트레이너 카드 ────────────────────────────────────────────────────────
    "Iono":                  "이오나",
    "Arven":                 "아르벵",
    "Nemona":                "네모",
    "Penny":                 "페니",
    "Geeta":                 "체계이",
    "Clavell":               "클라벨",
    "Grusha":                "라이스",
    "Larry":                 "앤초비",
    "Tulip":                 "잠보네",
    "Rika":                  "리카",
    "Hassel":                "유버트",
    "Saguaro":               "사구아로",
    "Jacq":                  "제크",
    "Professor Sada":        "사다 박사",
    "Professor Turo":        "투로 박사",
    "Professor's Research":  "박사의 연구",
    "Boss's Orders":         "보스의 지령",
    "Marnie":                "마리",
    "Hop":                   "홉",
    "Leon":                  "단델",
    "Gloria":                "유리",
    "Bede":                  "비트",
    "Sonia":                 "소니아",
    "Raihan":                "키바나",
    "Melony":                "메로네",
    "Nessa":                 "네로리",
    "Bea":                   "사이토",
    "Allister":              "오니온",
    "Opal":                  "박하",
    "Gordie":                "고니시",
    "Piers":                 "네로",
    "Klara":                 "쿠쿠이",
    "Avery":                 "시미",
    "Mustard":               "머스타드",
    "Peonia":                "페오니아",
    # SV1-SV4 트레이너/아이템
    "Miriam":                "미리암",
    "Katy":                  "카티",
    "Team Star Grunt":       "스타단 조무래기",
    "Giacomo":               "자이모",
    "Dendra":                "덴드라",
    "Falkner":               "비전",
    "Poppy":                 "포피",
    "Ryme":                  "라임",
    "Ortega":                "올티가",
    "Mela":                  "멜라",
    "Norman":                "성호",
    "Roark":                 "강석",
    "Shauntal":              "말리화",
    "Clive":                 "클라이브",
    "Erika's Invitation":    "이바키의 초대",
    "Giovanni's Charisma":   "비주기의 카리스마",
    "Daisy's Help":          "데이지의 도움",
    "Bill's Transfer":       "이수의 이동",
    "Artazon":               "아르타존",
    "Nest Ball":             "네스트볼",
    "Rare Candy":            "이상한사탕",
    "Super Rod":             "고급 낚싯대",
    "Superior Energy Retrieval": "슈퍼 에너지 재생",
    "Switch":                "교체",
    "Counter Catcher":       "카운터캐처",
    "Luxurious Cape":        "고급 망토",
    "Reversal Energy":       "리버설 에너지",
    "Basic Fighting Energy": "기본 격투 에너지",
    "Basic Lightning Energy": "기본 번개 에너지",
    "Basic Water Energy":    "기본 물 에너지",
    "Basic Grass Energy":    "기본 풀 에너지",
    "Basic Fire Energy":     "기본 불꽃 에너지",
    "Basic Psychic Energy":  "기본 에스퍼 에너지",
    "Judge":                 "심판",
    "Paldean Student":       "팔데아 학생",
    "Bianca's Devotion":     "블랙시티의 헌신",
    "Eri":                   "에리",
    "Morty's Conviction":    "봉인의 신념",
    "Salvatore":             "살바토레",
    "Explorer's Guidance":   "탐험가의 안내",
    "Ciphermaniac's Codebreaking": "암호마니아의 해독",
    "Kieran":                "키에란",
    "Lana's Aid":            "수련의 도움",
    "Carmine":               "주홍",
    "Perrin":                "페린",
    "Buddy-Buddy Poffin":    "친구 친구 포핀",
    "Enhanced Hammer":       "강화 해머",
    "Rescue Board":          "구조 보드",
    "Luminous Energy":       "루미너스 에너지",
    "Caretaker":             "관리인",
    "Lucian":                "루시안",
    "Cassiopeia":            "카시오페아",
    "Colress's Tenacity":    "플라드의 집념",
    "Janine's Secret Art":   "시연의 비전",
    "Xerosic's Machinations": "플라드의 계략",
    "Earthen Vessel":        "대지의 그릇",
    "Powerglass":            "파워글래스",
    "Basic Darkness Energy": "기본 악 에너지",
    "Basic Metal Energy":    "기본 강철 에너지",
    "Briar":                 "브라이어",
    "Lacey":                 "레이시",
    "Crispin":               "크리스핀",
    # ── 기타 포켓몬 ─────────────────────────────────────────────────────────
    "Snorlax":               "잠만보",
    "Clefairy":              "삐삐",
    "Clefable":              "픽시",
    "Jigglypuff":            "푸린",
    "Wigglytuff":            "푸크린",
    "Psyduck":               "고라파덕",
    "Golduck":               "골덕",
    "Growlithe":             "가디",
    "Arcanine":              "윈디",
    "Ponyta":                "포니타",
    "Rapidash":              "날쌩마",
    "Gastly":                "고오스",
    "Haunter":               "고우스트",
    "Gengar":                "팬텀",
    "Kangaskhan":            "캥카",
    "Scyther":               "스라크",
    "Electabuzz":            "에레브",
    "Magmar":                "마그마",
    "Magikarp":              "잉어킹",
    "Gyarados":              "갸라도스",
    "Lapras":                "라프라스",
    "Eevee":                 "이브이",
    "Vaporeon":              "샤워즈",
    "Jolteon":               "쥬피썬더",
    "Flareon":               "부스터",
    "Espeon":                "에브이",
    "Umbreon":               "블래키",
    "Leafeon":               "리피아",
    "Glaceon":               "글레이시아",
    "Sylveon":               "님피아",
    "Ditto":                 "메타몽",
    "Dragonite":             "드래곤나이트",
    "Pikachu":               "피카츄",
    "Raichu":                "라이츄",
    "Charizard":             "리자몽",
    "Blastoise":             "거북왕",
    "Venusaur":              "이상해꽃",
    "Mewtwo":                "뮤츠",
    "Mew":                   "뮤",
    "Gardevoir":             "가디안",
    "Lucario":               "루카리오",
    "Garchomp":              "한카리아스",
    "Miraidon":              "미라이돈",
    "Koraidon":              "코라이돈",
    "Rayquaza":              "레쿠쟈",
    "Giratina V":            "기라티나 V",
    "Lugia V":               "루기아 V",
    "Lugia VSTAR":           "루기아 VSTAR",
    "Origin Forme Giratina V": "오리진폼 기라티나 V",
    "Radiant Charizard":     "빛나는 리자몽",
    "Radiant Gardevoir":     "빛나는 가디안",
    "Radiant Blastoise":     "빛나는 거북왕",
    "Radiant Greninja":      "빛나는 게꼬마르",
    "Radiant Eternatus":     "빛나는 에테르나투스",
    "Comfey":                "포포모",
    "Cramorant":             "가마우지",
    "Sableye":               "깜놀",
    "Klefki":                "열쇠젤리",
    "Zoroark":               "조로아크",
    "Zoroark VSTAR":         "조로아크 VSTAR",
    "Mewtwo VSTAR":          "뮤츠 VSTAR",
    "Umbreon VMAX":          "블래키 VMAX",
    "Leafeon VMAX":          "리피아 VMAX",
    "Sylveon VMAX":          "님피아 VMAX",
    "Espeon VMAX":           "에브이 VMAX",
    "Glaceon VMAX":          "글레이시아 VMAX",
    "Flareon VMAX":          "부스터 VMAX",
    "Jolteon VMAX":          "쥬피썬더 VMAX",
    "Vaporeon VMAX":         "샤워즈 VMAX",
    "Eternatus VMAX":        "에테르나투스 VMAX",
    "Rayquaza VMAX":         "레쿠쟈 VMAX",
    "Calyrex VMAX":          "바드렉스 VMAX",
    "Ice Rider Calyrex VMAX": "얼음 기수 바드렉스 VMAX",
    "Shadow Rider Calyrex VMAX": "저승 기수 바드렉스 VMAX",
    "Zacian V":              "자시안 V",
    "Zamazenta V":           "자마젠타 V",
    "Zacian VSTAR":          "자시안 VSTAR",
    # SV7 트레이너
    "Amarys":                "아마리스",
    "Atticus":               "아티커스",
    "Drayton":               "드레이턴",
    "Brassius":              "브라시우스",
    "Crispin":               "크리스핀",
    "Yveltal":               "이벨타르",
    "Friends in Paldea":     "팔데아의 친구들",
    "Raifort":               "레이포트",
    "Tyme":                  "타임",
}


def update_names(sb) -> int:
    """DB에서 name_en을 조회하여 name_kr이 비어 있는 카드에 한국어 이름 업데이트"""
    from seeds.update_kr_from_jp import fetch_all_cards

    cards = fetch_all_cards(sb)

    updated = 0
    skipped = 0

    for card in cards:
        en = (card.get("name_en") or "").strip()
        kr = (card.get("name_kr") or "").strip()

        # 이미 한글이 있으면 스킵
        if kr and any("\uAC00" <= c <= "\uD7A3" for c in kr):
            skipped += 1
            continue

        # 매핑 테이블에서 찾기 (영어 이름)
        new_kr = KR_NAMES.get(en, "")
        if not new_kr and en:
            # 부분 매칭: "Charizard ex SAR" → "Charizard ex"
            for key in sorted(KR_NAMES.keys(), key=len, reverse=True):
                if en.startswith(key) or key in en:
                    suffix = en[len(key):].strip()
                    new_kr = KR_NAMES[key] + (f" {suffix}" if suffix else "")
                    break
        if not new_kr:
            continue

        sb.table("cards").update({"name_kr": new_kr}).eq("id", card["id"]).execute()
        updated += 1

    return updated


def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("[ERROR] .env에 SUPABASE_URL, SUPABASE_SERVICE_KEY가 필요합니다.")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    print("[한국어 이름 업데이트] 시작...")
    count = update_names(sb)
    print(f"[완료] {count}개 카드 이름 업데이트 완료")


if __name__ == "__main__":
    main()
