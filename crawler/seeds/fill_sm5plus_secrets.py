"""금단의 빛(SM5+) 누락 HR5+UR3 보완 — 이미지 육안 검증 후 로컬 저장·DB 삽입."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.rarity_rank import rank_for_rarity

APPLY = "--apply" in sys.argv
ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "web" / "public" / "card-images" / "SM5plus"
AUDIT = Path(__file__).with_name("_audit_out") / "sm5plus_imgs"

# pokellector JP SM6 scans — 번호·등급 인쇄 기준 (나무위키 108/109 표기 순서와 다름)
CARDS = [
    {
        "card_number": "103/094",
        "rarity": "HR",
        "name_kr": "개굴닌자 GX",
        "name_en": "Greninja GX",
        "src": "https://cdn.collectory.cc/cards/jp/SM6/103_094HR.webp",
        "file": "103-094-HR.webp",
    },
    {
        "card_number": "104/094",
        "rarity": "HR",
        "name_kr": "지가르데 GX",
        "name_en": "Zygarde GX",
        "src": "https://cdn.collectory.cc/cards/jp/SM6/104_094HR.webp",
        "file": "104-094-HR.webp",
    },
    {
        "card_number": "105/094",
        "rarity": "HR",
        "name_kr": "이벨타르 GX",
        "name_en": "Yveltal GX",
        "src": "https://cdn.collectory.cc/cards/jp/SM6/105_094HR.webp",
        "file": "105-094-HR.webp",
    },
    {
        "card_number": "106/094",
        "rarity": "HR",
        "name_kr": "제르네아스 GX",
        "name_en": "Xerneas GX",
        "src": "https://cdn.collectory.cc/cards/jp/SM6/106_094HR.webp",
        "file": "106-094-HR.webp",
    },
    {
        "card_number": "107/094",
        "rarity": "HR",
        "name_kr": "울트라네크로즈마 GX",
        "name_en": "Ultra Necrozma GX",
        "src": "https://cdn.collectory.cc/cards/jp/SM6/107_094HR.webp",
        "file": "107-094-HR.webp",
    },
    {
        "card_number": "108/094",
        "rarity": "UR",
        "name_kr": "에너지 포터",
        "name_en": "Eneporter",
        # collectory SM6/108 은 울트라포스(sm5+) 잘못 매핑 — pokellector 스캔 사용
        "src": "https://den-cards.pokellector.com/235/Eneporter.SM6.108.20555.png",
        "file": "108-094-UR.png",
    },
    {
        "card_number": "109/094",
        "rarity": "UR",
        "name_kr": "미스터리 트레져",
        "name_en": "Mystery Treasure",
        "src": "https://cdn.collectory.cc/cards/jp/SM6/109_094UR.webp",
        "file": "109-094-UR.webp",
    },
    {
        "card_number": "110/094",
        "rarity": "UR",
        "name_kr": "유닛 에너지 격투 악 페어리",
        "name_en": "Unit Energy Fighting Darkness Fairy",
        "src": "https://cdn.collectory.cc/cards/jp/SM6/110_094UR.webp",
        "file": "110-094-UR.webp",
    },
]


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

    for card in CARDS:
        dest = PUBLIC / card["file"]
        if not dest.exists() or dest.stat().st_size < 5000:
            print(f"download {card['card_number']} {card['rarity']} …")
            r = client.get(card["src"])
            r.raise_for_status()
            if len(r.content) < 8000:
                raise SystemExit(f"too small: {card['src']} ({len(r.content)})")
            dest.write_bytes(r.content)
            shutil.copy(dest, AUDIT / card["file"])
        print(f"  OK {dest.name} {dest.stat().st_size}B -> {card['name_kr']}")

    if not APPLY:
        print("\n드라이런 — 반영: python fill_sm5plus_secrets.py --apply")
        return

    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    rows = sb.table("card_sets").select("id").eq("set_code", "SM5+").execute().data or []
    if not rows:
        raise SystemExit("SM5+ set missing")
    set_id = rows[0]["id"]

    for card in CARDS:
        image_url = f"/card-images/SM5plus/{card['file']}"
        payload = {
            "set_id": set_id,
            "card_number": card["card_number"],
            "rarity": card["rarity"],
            "rarity_rank": rank_for_rarity(card["rarity"]),
            "name_kr": card["name_kr"],
            "name_en": card["name_en"],
            "name_jp": card["name_en"],
            "image_url": image_url,
        }
        existing = (
            sb.table("cards")
            .select("id")
            .eq("set_id", set_id)
            .eq("card_number", card["card_number"])
            .eq("rarity", card["rarity"])
            .execute()
            .data
            or []
        )
        if existing:
            sb.table("cards").update(payload).eq("id", existing[0]["id"]).execute()
            print(f"  update {card['card_number']} {card['rarity']}")
        else:
            sb.table("cards").insert(payload).execute()
            print(f"  insert {card['card_number']} {card['rarity']}")

    print("done SM5+ secrets")


if __name__ == "__main__":
    main()
