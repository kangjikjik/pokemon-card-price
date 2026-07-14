"""잔존 일본어/오역 카드명 수동 수정"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
from supabase import create_client
from seeds.update_kr_from_jp import TRAINER_JP_KR

MANUAL = {
    **TRAINER_JP_KR,
    "Teal Mask Ogerpon ex": "청록의 가면 오거폰 ex",
    "Cornerstone Mask Ogerpon ex": "주춧돌의 가면 오거폰 ex",
    "Hearthflame Mask Ogerpon ex": "화덕의 가면 오거폰 ex",
    "Wellspring Mask Ogerpon ex": "우물의 가면 오거폰 ex",
}

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# jp 키로 직접 수정
for jp, kr in MANUAL.items():
    if not jp or not kr:
        continue
    rows = sb.table("cards").select("id").eq("name_jp", jp).execute().data or []
    for row in rows:
        sb.table("cards").update({"name_kr": kr}).eq("id", row["id"]).execute()

# id 직접 수정 (카타카나 잔존)
direct = {
    1485: "미캔의 눈빛",
    1811: "히비키의 마그마단더",
}
for cid, kr in direct.items():
    sb.table("cards").update({"name_kr": kr}).eq("id", cid).execute()

print("done")
