"""PRM-MISC 세트 대표 이미지를 잉어킹 프로모 카드로 설정."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from utils.db import get_supabase

load_dotenv()
sb = get_supabase()

MAGIKARP_IMAGE = "https://cdn.collectory.cc/cards/kr/M-P/040_M-P.webp"


def main() -> None:
    rows = sb.table("card_sets").select("id").eq("set_code", "PRM-MISC").execute().data or []
    if not rows:
        raise RuntimeError("PRM-MISC set not found")
    sb.table("card_sets").update({"image_url": MAGIKARP_IMAGE}).eq("id", rows[0]["id"]).execute()
    print(f"Updated PRM-MISC image_url -> {MAGIKARP_IMAGE}")


if __name__ == "__main__":
    main()
