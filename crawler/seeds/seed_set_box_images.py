"""확장팩 박스 이미지 URL을 card_sets.image_url에 저장"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client

TARGET_SETS = [
    "SV2a", "SV4a", "SV3a", "SV2D", "SV8a",
    "SV5a", "SV1S", "SV1V", "MG6", "MG4a", "SV7",
]

# 포켓몬카드 공식 사이트 박스/OGP 이미지
STATIC_BOX: dict[str, str] = {
    "SV2a": "https://www.pokemon-card.com/ex/sv2a/assets/images/ogp.png",
    "SV3a": "https://www.pokemon-card.com/products/2023/images/SV3a_carousel.jpg",
    "SV4a": "https://www.pokemon-card.com/ex/sv4a/assets/images/ogp.png",
    "SV5a": "https://www.pokemon-card.com/products/2024/images/SV5a_2.jpg",
    "SV7": "https://www.pokemon-card.com/ex/sv7/assets/images/ogp.png",
    "SV8a": "https://www.pokemon-card.com/ex/sv8a/assets/images/ogp.png",
    "SV1S": "https://www.pokemon-card.com/ex/sv1/assets/images/product3-image-1.png",
    "SV1V": "https://www.pokemon-card.com/ex/sv1/assets/images/ogp.png",
    "SV2D": "https://www.pokemon-card.com/products/2023/images/332c160f3dd3cec7fc3a45dba1c7023d08aac8a7.png",
    "MG6": "https://www.pokemon-card.com/ex/m5/assets/images/ogp.png",
    "MG4a": "https://www.pokemon-card.com/ex/m2a/assets/images/ogp.png",
}


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    sets = sb.table("card_sets").select("id,set_code,image_url").in_("set_code", TARGET_SETS).execute().data or []

    updated = 0
    for s in sets:
        code = s["set_code"]
        url = STATIC_BOX.get(code)
        if not url:
            print(f"  {code}: no static box URL")
            continue
        if url != s.get("image_url"):
            sb.table("card_sets").update({"image_url": url}).eq("id", s["id"]).execute()
            updated += 1
            print(f"  {code}: {url[:72]}...")
        else:
            print(f"  {code}: already set")

    print(f"\n[완료] {updated}개 세트 박스 이미지 업데이트")


if __name__ == "__main__":
    main()
