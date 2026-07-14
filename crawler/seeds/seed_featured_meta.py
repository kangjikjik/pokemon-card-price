"""55개 featured 세트 — 한국 발매일·한글명·한국 박스 이미지 일괄 갱신"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from supabase import create_client

from kr_sets import FEATURED_SET_CODES, KR_BY_CODE


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

    for code in FEATURED_SET_CODES:
        meta = KR_BY_CODE.get(code)
        if not meta:
            print(f"{code}: kr_sets 없음 — skip")
            continue

        row = (
            sb.table("card_sets")
            .select("id")
            .eq("set_code", code)
            .maybe_single()
            .execute()
            .data
        )
        if not row:
            print(f"{code}: DB 없음 — skip")
            continue

        patch = {
            "released_at": meta.released_at,
            "name_kr": meta.name_kr,
            "name_en": meta.name_kr,
        }
        if meta.box_image_kr:
            patch["image_url"] = meta.box_image_kr

        sb.table("card_sets").update(patch).eq("id", row["id"]).execute()
        print(f"{code}: {meta.name_kr} | {meta.released_at}")


if __name__ == "__main__":
    main()
