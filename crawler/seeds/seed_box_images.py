"""확장팩 박스 이미지만 갱신 (collectory + SAR fallback)"""
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from supabase import create_client

from box_images import pick_box_image
from collectory_map import COLLECTORY_API, COLLECTORY_SETS
from seed_from_collectory import fetch_set_cards, fetch_set_meta


def main():
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(headers={"User-Agent": "pokemon-card-price-seed/1.0"})

    for set_code, cfg in COLLECTORY_SETS.items():
        set_row = sb.table("card_sets").select("id").eq("set_code", set_code).single().execute().data
        if not set_row:
            continue
        meta = fetch_set_meta(client, cfg["id"])
        cards = fetch_set_cards(client, cfg["id"])
        url = pick_box_image(set_code, meta.get("image_url") if meta else None, cards)
        if url:
            sb.table("card_sets").update({"image_url": url}).eq("id", set_row["id"]).execute()
            print(f"{set_code}: {url[:75]}...")
        time.sleep(0.2)


if __name__ == "__main__":
    main()
