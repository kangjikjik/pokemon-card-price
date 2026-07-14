"""
어비스아이(MG6) 전체 카드 수집
- 기본 81장: 일본 공식 API (정확한 레어도)
- 시크릿: 유유테이 이미지 (AR/SR/SAR/MUR)
  ※ sc_rare_rac 는 R(레어) 필터임 — ACE SPEC 이 아님. ACE 오시드 금지.
실행: python -m seeds.seed_abyss_eye
"""
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from supabase import create_client

load_dotenv()
JP_BASE = "https://www.pokemon-card.com"
YUYU_FRONT = "https://card.yuyu-tei.jp/poc/front/m05/{page_id}.jpg"
PG = "954"
SET_CODE, NAME_KR, NAME_JP = "MG6", "어비스 아이", "アビスアイ"

RARITY_RANK = {
    "MUR": 9, "SAR": 8, "SR": 7, "AR": 6, "ACE": 5,
    "RR": 4, "R": 3, "U": 2, "C": 1,
}

# 기본 81장 레어도 (카드번호 → 레어도)
BASE_RARITY: dict[int, str] = {
    4: "RR", 15: "RR", 26: "RR", 36: "RR", 43: "RR", 46: "RR", 53: "RR", 63: "RR",
    11: "R", 19: "R", 33: "R", 80: "R", 81: "R",
    6: "U", 7: "U", 13: "U", 16: "U", 21: "U", 23: "U", 25: "U", 27: "U", 29: "U",
    32: "U", 35: "U", 37: "U", 38: "U", 39: "U", 41: "U", 45: "U", 48: "U", 50: "U",
    52: "U", 54: "U", 56: "U", 57: "U", 58: "U", 60: "U", 62: "U", 66: "U", 68: "U",
    70: "U", 73: "U", 75: "U", 76: "U", 77: "U", 78: "U", 79: "U",
}

# 시크릿 카드: (카드번호, 레어도, 일본어명)
# 이미지 URL = front/m05/{10000+카드번호}.jpg (유유테이 페이지 ID와 동일)
SECRET_CARDS = [
  (82,  "AR",  "カリキリ"),
  (83,  "AR",  "グレンアルマ"),
  (84,  "AR",  "トサキント"),
  (85,  "AR",  "アシレーヌ"),
  (86,  "AR",  "ライボルト"),
  (87,  "AR",  "ヤドラン"),
  (88,  "AR",  "ダダリン"),
  (89,  "AR",  "フォクスライ"),
  (90,  "AR",  "ザルード"),
  (91,  "AR",  "トリデプス"),
  (92,  "AR",  "ドデカバシ"),
  (93,  "AR",  "シルヴァディ"),
  (94,  "SR",  "ラランテスex"),
  (95,  "SR",  "ホエルオーex"),
  (96,  "SR",  "メガゼラオラex"),
  (97,  "SR",  "メガシャンデラex"),
  (98,  "SR",  "ラムパルドex"),
  (99,  "SR",  "メガダークライex"),
  (100, "SR",  "モルペコex"),
  (101, "SR",  "メガドリュウズex"),
  (102, "SR",  "アイアンディフェンダー"),
  (103, "SR",  "エネルギーつけかえ"),
  (104, "SR",  "クラッシュハンマー"),
  (105, "SR",  "ダークベル"),
  (106, "SR",  "ごうかいボム"),
  (107, "SR",  "ブレイブバングル"),
  (108, "SR",  "カスミの元気"),
  (109, "SR",  "グラジオの決戦"),
  (110, "SR",  "サビ組のしたっぱ"),
  (111, "SR",  "ムク"),
  (112, "SAR", "メガゼラオラex"),
  (113, "SAR", "メガシャンデラex"),
  (114, "SAR", "メガダークライex"),
  (115, "SAR", "モルペコex"),
  (116, "SAR", "グラジオの決戦"),
  (117, "SAR", "ムク"),
  (118, "MUR", "メガダークライex"),
]

JP_KR_EXTRA = {
    "グラジオの決戦": "그라지오의 결전", "ムク": "무쿠",
    "カスミの元気": "이슬의 활기", "サビ組のしたっぱ": "녹슨조의 심부름꾼",
    "アイアンディフェンダー": "아이언 디펜더", "エネルギーつけかえ": "에너지 전환",
    "クラッシュハンマー": "클래시 해머", "ダークベル": "다크 펜던트",
    "ごうかいボム": "강화 폭탄", "ブレイブバングル": "브레이브 뱅글",
    "ボルト雷エネルギー": "볼트번개 에너지", "シャドー悪エネルギー": "섀도악 에너지",
    "化石採掘場": "화석 채굴장", "古びたずがいの化石": "낡은 등껍질 화석",
    "古びたたての化石": "낡은 발톱 화석", "リトライバッジ": "재도전 뱃지",
    "タイプ：ヌル": "타입:널",
}


def load_jp_kr_cache() -> dict[str, str]:
    cache = Path(__file__).parent / "jp_kr_pokemon_cache.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    return {}


def translate_jp(name_jp: str, jp_kr: dict[str, str]) -> str:
    if not name_jp:
        return ""
    if name_jp in JP_KR_EXTRA:
        return JP_KR_EXTRA[name_jp]

    result = name_jp
    if result.startswith("メガ"):
        result = "메가" + result[2:]

    suffix = ""
    for suf in ["ex", "EX"]:
        if result.endswith(suf):
            suffix = " ex"
            result = result[: -len(suf)]
            break

    for jp in sorted(jp_kr.keys(), key=len, reverse=True):
        if jp in result:
            result = result.replace(jp, jp_kr[jp], 1)
            return result + suffix

    if result in jp_kr:
        return jp_kr[result] + suffix
    return ""


async def fetch_base_cards(page) -> list[dict]:
    cards = []
    for pg in range(1, 5):
        data = await page.evaluate(f'''
            async () => {{
                const resp = await fetch(
                    "/card-search/resultAPI.php?pg={PG}&page={pg}",
                    {{credentials:"include"}}
                );
                return await resp.json();
            }}
        ''')
        batch = data.get("cardList", [])
        if not batch:
            break
        cards.extend(batch)
        if pg >= data.get("maxPage", 1):
            break
        await asyncio.sleep(0.3)
    return cards


async def main():
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    jp_kr = load_jp_kr_cache()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"{JP_BASE}/card-search/index.php?pg={PG}", timeout=30000)
        await asyncio.sleep(3)

        print(f"[{NAME_KR}] 수집 시작...")
        base = await fetch_base_cards(page)
        await browser.close()

    # sc_rare_rac 는 R(레어) 필터 — ACE SPEC 이 아님. ACE 별도 시드 금지.
    print(f"  기본: {len(base)}장, 시크릿: {len(SECRET_CARDS)}장")

    r = sb.table("card_sets").upsert(
        {"set_code": SET_CODE, "name_kr": NAME_KR, "name_jp": NAME_JP, "name_en": "Abyss Eye"},
        on_conflict="set_code",
    ).execute()
    set_id = r.data[0]["id"]

    sb.table("cards").delete().eq("set_id", set_id).execute()

    saved = 0

    # 기본 81장
    for card in base:
        name_jp = card.get("cardNameViewText", "")
        card_num = int(card["cardID"]) - 50219
        rarity = BASE_RARITY.get(card_num, "C")

        img = JP_BASE + card.get("cardThumbFile", "") if card.get("cardThumbFile") else ""
        name_kr = translate_jp(name_jp, jp_kr)

        sb.table("cards").insert({
            "set_id": set_id,
            "name_jp": name_jp,
            "name_kr": name_kr,
            "name_en": "",
            "rarity": rarity,
            "rarity_rank": RARITY_RANK.get(rarity, 1),
            "image_url": img,
            "card_number": f"{card_num:03d}/081",
            "image_color": "from-slate-600 via-slate-700 to-slate-800",
        }).execute()
        saved += 1

    # 시크릿 카드 (유유테이 front 이미지 — page_id = 10000 + 카드번호)
    for num, rarity, name_jp in SECRET_CARDS:
        page_id = 10000 + num
        name_kr = translate_jp(name_jp, jp_kr)
        sb.table("cards").insert({
            "set_id": set_id,
            "name_jp": name_jp,
            "name_kr": name_kr,
            "name_en": "",
            "rarity": rarity,
            "rarity_rank": RARITY_RANK.get(rarity, 1),
            "image_url": YUYU_FRONT.format(page_id=page_id),
            "card_number": f"{num:03d}/081",
            "image_color": "from-amber-600 via-orange-700 to-red-800",
        }).execute()
        saved += 1

    from collections import Counter
    all_cards = sb.table("cards").select("rarity").eq("set_id", set_id).execute()
    counts = Counter(c["rarity"] for c in (all_cards.data or []))

    print(f"\n[완료] {saved}장 저장")
    for r_name, n in counts.most_common():
        print(f"  {r_name}: {n}장")


if __name__ == "__main__":
    asyncio.run(main())
