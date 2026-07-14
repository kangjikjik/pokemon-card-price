"""
일본 포켓몬카드 공식 사이트에서 SV/MEGA 시리즈 고희귀 카드 수집
실행: python -m seeds.seed_jp_official  (crawler/ 폴더 안에서)

- pokemon-card.com resultAPI.php 사용
- 세트별 SAR / HR(UR금박) / SR 수집
- Supabase cards 테이블에 upsert
"""

import asyncio
import os
import re
import sys

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
JP_BASE = "https://www.pokemon-card.com"

# ─── 일본 공식 pg 값 → (DB set_code, 한국어 이름, 일본어 이름) ─────────────────
# pg 값은 일본 공식 사이트 resultAPI.php의 세트 선택 파라미터
JP_SETS: dict[str, tuple[str, str, str]] = {
    # SV 시리즈
    "870":  ("SV1S",  "스칼렛 ex",           "スカーレットex"),
    "871":  ("SV1V",  "바이올렛 ex",          "バイオレットex"),
    "877":  ("SV1a",  "트리플렛 비트",         "強化拡張パック「トリプレットビート」"),
    "879":  ("SV2P",  "스노우 해저드",         "スノーハザード"),
    "880":  ("SV2D",  "클레이버스트",          "クレイバースト"),
    "882":  ("SV2a",  "포켓몬카드 151",        "ポケモンカード151"),
    "894":  ("SV3",   "흑염의 카리스마",        "黒炎の支配者"),
    "897":  ("SV3a",  "레이징 서프",           "レイジングサーフ"),
    "901":  ("SV4K",  "고대의 포효",           "古代の咆哮"),
    "902":  ("SV4M",  "미래의 일격",           "未来の一閃"),
    "905":  ("SV4a",  "샤이니 트레저 ex",       "シャイニートレジャーex"),
    "906":  ("SV4",   "와일드 포스",           "ワイルドフォース"),
    "907":  ("SV4x",  "사이버 저지",           "サイバージャッジ"),
    "913":  ("SV5M",  "크림슨 헤이즈",         "クリムゾンヘイズ"),
    "914":  ("SV5K",  "변환의 가면",           "変幻の仮面"),
    "917":  ("SV5a",  "나이트 원더러",          "強化拡張パック「ナイトワンダラー」"),
    "918":  ("SV6",   "스텔라 미라클",          "ステラミラクル"),
    "922":  ("SV6a",  "낙원 드라고나",          "強化拡張パック「楽園ドラゴーナ」"),
    "923":  ("SV7",   "초전 브레이커",          "超電ブレイカー"),
    "934":  ("SV8",   "테라스탈 페스 ex",       "ハイクラスパック「テラスタルフェスex」"),
    "935":  ("SV8a",  "배틀 파트너즈",          "バトルパートナーズ"),
    "SV-P": ("SVP",   "SV 프로모",              "スカーレット＆バイオレット プロモカード"),
    # MEGA 시리즈 (2025~)
    "940":  ("MG1a",  "열풍의 아레나",          "強化拡張パック「熱風のアリーナ」"),
    "941":  ("MG1b",  "로켓단의 영광",          "ロケット団の栄光"),
    "942":  ("MG2",   "블랙 볼트",              "ブラックボルト"),
    "943":  ("MG2a",  "화이트 플레어",           "ホワイトフレア"),
    "944":  ("MG3",   "메가 브레이브",           "メガブレイブ"),
    "945":  ("MG3a",  "메가 심포니아",           "メガシンフォニア"),
    "949":  ("MG4",   "인페르노 X",              "インフェルノX"),
    "950":  ("MG4a",  "MEGA 드림 ex",           "ハイクラスパック「MEGAドリームex」"),
    "952":  ("MG5",   "무니키스 제로",           "ムニキスゼロ"),
    "953":  ("MG5a",  "닌자 스피너",             "ニンジャスピナー"),
    "954":  ("MG6",   "어비스 아이",             "アビスアイ"),
    "M-P":  ("MGP",   "MEGA 프로모",             "ポケモンカードゲーム MEGA プロモカード"),
}

# ─── 희귀도 파라미터 ────────────────────────────────────────────────────────
RARITY_PARAMS: list[tuple[str, str, int]] = [
    ("sc_rare_sar", "SAR", 8),
    ("sc_rare_hr",  "UR",  7),
    ("sc_rare_sr",  "SR",  6),
    ("sc_rare_ar",  "AR",  5),
]
# UR-ex 카드는 별도 수집 시 rarity_rank=6 적용


def get_image_color(name_jp: str) -> str:
    KW_COLORS = {
        "リザードン": "from-orange-500 via-red-600 to-rose-700",
        "ミュウ":     "from-pink-400 via-fuchsia-500 to-purple-600",
        "ピカチュウ":  "from-yellow-300 via-yellow-400 to-amber-500",
        "ミュウツー":  "from-purple-500 via-violet-600 to-indigo-700",
        "イーブイ":   "from-amber-400 via-orange-400 to-yellow-500",
        "サーナイト":  "from-green-300 via-teal-400 to-emerald-500",
        "ミライドン":  "from-blue-400 via-cyan-500 to-teal-600",
        "コライドン":  "from-red-500 via-orange-600 to-amber-700",
        "ブラッキー":  "from-yellow-400 via-gray-800 to-black",
        "レックウザ":  "from-emerald-500 via-green-600 to-lime-700",
        "ニンフィア":  "from-pink-300 via-rose-400 to-fuchsia-500",
        "イオナ":     "from-lime-400 via-emerald-500 to-teal-600",
        "ネモ":      "from-orange-300 via-amber-400 to-yellow-500",
        "テラパゴス":  "from-amber-300 via-yellow-400 to-lime-500",
        "ルカリオ":   "from-blue-400 via-indigo-500 to-violet-600",
    }
    for kw, color in KW_COLORS.items():
        if kw in name_jp:
            return color
    return "from-slate-600 via-slate-700 to-slate-800"


async def collect_set_rarity(page, pg_val: str, param_name: str, rarity_code: str) -> list[dict]:
    """특정 세트 + 희귀도의 카드 수집 (세션 내 JavaScript fetch)"""
    collected: list[dict] = []

    # SAR 체크박스 활성화로 세션에 희귀도 저장
    await page.evaluate(f'''
        () => {{
            const el = document.querySelector('input[name="{param_name}"]');
            if (el && !el.checked) {{
                el.checked = true;
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
            }}
        }}
    ''')
    await asyncio.sleep(0.5)

    # 세트 pg 값으로 카드 요청
    result = await page.evaluate(f'''
        async () => {{
            const url = `/card-search/resultAPI.php?pg={pg_val}&{param_name}=1`;
            const resp = await fetch(url, {{credentials: 'include'}});
            return await resp.json();
        }}
    ''')

    hit_cnt = result.get("hitCnt", 0)
    max_page = result.get("maxPage", 0)

    if hit_cnt == 0:
        return []

    for card in result.get("cardList", []):
        card["_rarity_code"] = rarity_code
        collected.append(card)

    # 다음 페이지들
    for i in range(2, max_page + 1):
        pg_result = await page.evaluate(f'''
            async (pageNum) => {{
                const url = `/card-search/resultAPI.php?pg={pg_val}&p=${{pageNum}}&{param_name}=1`;
                const resp = await fetch(url, {{credentials: 'include'}});
                return await resp.json();
            }}
        ''', i)
        for card in pg_result.get("cardList", []):
            card["_rarity_code"] = rarity_code
            collected.append(card)
        await asyncio.sleep(0.2)

    return collected


async def fetch_all_jp_cards() -> list[dict]:
    all_cards: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        print("[Playwright] 페이지 초기화...")
        await page.goto(f"{JP_BASE}/card-search/index.php", timeout=30000)
        await asyncio.sleep(4)

        # SAR 체크박스 먼저 활성화 (세션 초기화)
        activated = await page.evaluate('''
            () => {
                const el = document.querySelector('input[name="sc_rare_sar"]');
                if (el) { el.checked = true; el.dispatchEvent(new Event('change', {bubbles: true})); return true; }
                return false;
            }
        ''')
        print(f"SAR 체크박스 활성화: {activated}")
        await asyncio.sleep(1.5)

        total_sets = len(JP_SETS)
        for i, (pg_val, (set_code, name_kr, name_jp)) in enumerate(JP_SETS.items()):
            print(f"\n[{i+1}/{total_sets}] {set_code} ({name_kr}) pg={pg_val}")
            set_cards = []

            for param_name, rarity_code, rarity_rank in RARITY_PARAMS:
                cards = await collect_set_rarity(page, pg_val, param_name, rarity_code)
                if cards:
                    for c in cards:
                        c["_rarity_rank"] = rarity_rank
                        c["_pg_val"] = pg_val
                    set_cards.extend(cards)
                    print(f"  {rarity_code}: {len(cards)}개")
                await asyncio.sleep(0.3)

            all_cards.extend(set_cards)
            print(f"  세트 합계: {len(set_cards)}개")

        await browser.close()

    return all_cards


def upsert_set(sb, pg_val: str) -> int | None:
    if pg_val not in JP_SETS:
        return None
    set_code, name_kr, name_jp = JP_SETS[pg_val]
    result = (
        sb.table("card_sets")
        .upsert(
            {"set_code": set_code, "name_kr": name_kr, "name_jp": name_jp, "name_en": name_kr},
            on_conflict="set_code",
        )
        .execute()
    )
    if result.data:
        return result.data[0]["id"]
    existing = sb.table("card_sets").select("id").eq("set_code", set_code).execute()
    return existing.data[0]["id"] if existing.data else None


def upsert_card(sb, card: dict, db_set_id: int) -> bool:
    name_jp = card.get("cardNameViewText", "").strip()
    image_path = card.get("cardThumbFile", "")
    image_url = JP_BASE + image_path if image_path else ""

    existing = (
        sb.table("cards")
        .select("id")
        .eq("set_id", db_set_id)
        .eq("name_jp", name_jp)
        .execute()
    )
    payload = {
        "set_id":      db_set_id,
        "card_number": "",
        "name_kr":     "",
        "name_jp":     name_jp,
        "name_en":     "",
        "rarity":      card["_rarity_code"],
        "rarity_rank": card["_rarity_rank"],
        "image_url":   image_url,
        "image_color": get_image_color(name_jp),
    }
    if existing.data:
        sb.table("cards").update({"image_url": image_url, "rarity": card["_rarity_code"]}).eq("id", existing.data[0]["id"]).execute()
    else:
        sb.table("cards").insert(payload).execute()
    return True


async def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("[ERROR] .env에 SUPABASE_URL, SUPABASE_SERVICE_KEY가 필요합니다.")
        sys.exit(1)
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    print("=" * 60)
    print("[일본 공식] SV + MEGA 시리즈 고희귀 카드 수집 시작")
    print("=" * 60)

    all_cards = await fetch_all_jp_cards()
    print(f"\n수집된 카드 총 {len(all_cards)}개")

    saved_sets: dict[str, int] = {}
    saved_cards = 0

    for card in all_cards:
        pg_val = card.get("_pg_val", "")
        if not pg_val or pg_val not in JP_SETS:
            continue

        if pg_val not in saved_sets:
            set_id = upsert_set(sb, pg_val)
            if set_id:
                saved_sets[pg_val] = set_id
                _, name_kr, _ = JP_SETS[pg_val]
                print(f"  [세트] pg={pg_val} → {name_kr} (id={set_id})")

        db_set_id = saved_sets.get(pg_val)
        if db_set_id:
            upsert_card(sb, card, db_set_id)
            saved_cards += 1

    print(f"\n[완료] 세트 {len(saved_sets)}개, 카드 {saved_cards}개 DB 저장")


if __name__ == "__main__":
    asyncio.run(main())
