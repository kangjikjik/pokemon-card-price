"""
사용자 요청에 따른 프로모 카드 대정리.
- 삭제: Gym 팩(PRM-GYM*), Pokemon Day(PRM-PD26), 확장팩 내 P 등급 카드
- 유지: CEL(25주년 기념 컬렉션), CEL25PK(25주년 기념 프로모팩), PRM-MISC(기타 프로모)
- 추가: PRM-MISC에 '잉어킹' 프로모 카드 추가
"""
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from utils.db import get_supabase

load_dotenv()
sb = get_supabase()

def main():
    print("=== 1. 불필요한 프로모 세트 삭제 ===")
    sets_to_delete = [
        "PRM-GYM01", "PRM-GYM02", "PRM-GYM03", "PRM-GYM04", "PRM-GYM05", "PRM-GYM06",
        "PRM-PD26"
    ]
    
    for code in sets_to_delete:
        res = sb.table("card_sets").select("id").eq("set_code", code).execute().data
        if res:
            sid = res[0]["id"]
            # Delete prices and cards
            cards = sb.table("cards").select("id").eq("set_id", sid).execute().data
            if cards:
                cids = [c["id"] for c in cards]
                for i in range(0, len(cids), 100):
                    chunk = cids[i:i+100]
                    sb.table("prices_kr").delete().in_("card_id", chunk).execute()
                    sb.table("prices_jp").delete().in_("card_id", chunk).execute()
                sb.table("cards").delete().in_("id", cids).execute()
            # Delete set
            sb.table("prices_box").delete().eq("set_id", sid).execute()
            sb.table("card_sets").delete().eq("id", sid).execute()
            print(f"Deleted set {code} and its cards.")

    print("=== 2. 확장팩에 섞여 들어간 P 등급 카드 삭제 ===")
    # CEL25PK와 PRM-MISC가 아닌 세트의 P 등급 카드 삭제
    keep_sets = sb.table("card_sets").select("id").in_("set_code", ["CEL25PK", "PRM-MISC"]).execute().data
    keep_sids = [s["id"] for s in keep_sets]
    
    all_p_cards = sb.table("cards").select("id, set_id").eq("rarity", "P").execute().data
    to_delete_cids = [c["id"] for c in all_p_cards if c["set_id"] not in keep_sids]
    
    if to_delete_cids:
        for i in range(0, len(to_delete_cids), 100):
            chunk = to_delete_cids[i:i+100]
            sb.table("prices_kr").delete().in_("card_id", chunk).execute()
            sb.table("prices_jp").delete().in_("card_id", chunk).execute()
            sb.table("cards").delete().in_("id", chunk).execute()
        print(f"Deleted {len(to_delete_cids)} embedded P rarity cards.")

    print("=== 3. PRM-MISC에 잉어킹 프로모 추가 ===")
    # PRM-MISC 세트 확인 및 생성
    misc_res = sb.table("card_sets").select("id").eq("set_code", "PRM-MISC").execute().data
    if not misc_res:
        ins = sb.table("card_sets").insert({
            "set_code": "PRM-MISC",
            "name_kr": "기타 프로모팩",
            "name_en": "Misc Promos",
            "image_url": ""
        }).execute().data
        misc_sid = ins[0]["id"]
    else:
        misc_sid = misc_res[0]["id"]
        sb.table("card_sets").update({"name_kr": "기타 프로모팩"}).eq("id", misc_sid).execute()

    # 잉어킹 카드 추가 (중복 확인)
    magikarp_res = sb.table("cards").select("id").eq("set_id", misc_sid).eq("name_kr", "잉어킹").execute().data
    if not magikarp_res:
        sb.table("cards").insert({
            "set_id": misc_sid,
            "name_kr": "잉어킹",
            "name_en": "Magikarp",
            "name_jp": "コイキング",
            "rarity": "P",
            "rarity_rank": 1, # P rank
            "card_number": "PROMO",
            "image_url": "https://cdn.collectory.cc/cards/kr/promo/magikarp.png" # Placeholder/Guess, can be updated later
        }).execute()
        print("Inserted Magikarp promo card into PRM-MISC.")
    else:
        print("Magikarp promo card already exists in PRM-MISC.")

if __name__ == "__main__":
    main()
