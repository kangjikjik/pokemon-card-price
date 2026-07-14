"""Audit MG6 (어비스아이) cards vs official pack composition."""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# Official MG6: base 001-081 + secret 082-118 = 118 cards
# seed_abyss_eye.py SECRET_CARDS numbers
OFFICIAL_SECRET = {
    82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93,
    94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111,
    112, 113, 114, 115, 116, 117, 118,
}
OFFICIAL_BASE = set(range(1, 82))  # 001-081
OFFICIAL_ALL = OFFICIAL_BASE | OFFICIAL_SECRET

s = sb.table("card_sets").select("id,set_code,name_kr").eq("set_code", "MG6").single().execute()
cards = (
    sb.table("cards")
    .select("id,card_number,name_kr,name_jp,rarity,image_url")
    .eq("set_id", s.data["id"])
    .execute()
    .data
    or []
)

print(f"=== MG6 어비스아이 DB 현황: {len(cards)}장 ===\n")

db_nums = {}
for c in cards:
    num_str = c["card_number"].split("/")[0]
    num = int(num_str)
    db_nums[num] = c

# Missing from DB
missing = sorted(OFFICIAL_ALL - set(db_nums.keys()))
extra = sorted(set(db_nums.keys()) - OFFICIAL_ALL)

print(f"공식 세트 총 {len(OFFICIAL_ALL)}장 (기본 81 + 시크릿 37)")
print(f"DB 보유: {len(cards)}장")
print(f"누락: {len(missing)}장")
print(f"초과(팩 외 번호): {len(extra)}장\n")

if missing:
    print("--- 누락 카드 (팩에 있지만 DB에 없음) ---")
    for n in missing[:30]:
        print(f"  {n:03d}/081")
    if len(missing) > 30:
        print(f"  ... 외 {len(missing)-30}장")

if extra:
    print("\n--- 팩 외 카드 (DB에 있지만 공식 번호 범위 밖) ---")
    for n in extra:
        c = db_nums[n]
        print(f"  {c['card_number']} {c['rarity']} {c['name_kr']} ({c['name_jp']})")

# Cards in DB but only secret-range without base? Check gaps in 1-81
base_in_db = sorted(n for n in db_nums if n <= 81)
secret_in_db = sorted(n for n in db_nums if n >= 82)

print(f"\n--- DB 구성 ---")
print(f"기본(001-081) 중 보유: {len(base_in_db)}장")
print(f"시크릿(082-118) 중 보유: {len(secret_in_db)}장")
print(f"레어도 분포: {dict(Counter(c['rarity'] for c in cards))}")

# List all DB cards grouped
print("\n--- DB 전체 목록 ---")
for n in sorted(db_nums.keys()):
    c = db_nums[n]
    in_pack = "OK" if n in OFFICIAL_ALL else "EXTRA"
    zone = "secret" if n >= 82 else "base"
    print(f"  [{in_pack}] {c['card_number']} {c['rarity']:4} {c['name_kr'] or '(한글명없음)'}  ({zone})")
