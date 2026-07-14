"""BW4 UR 잘못 넣은 영문 이미지를 검증된 JP Dark Rush 이미지로 교체."""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "web" / "public" / "card-images" / "BW4"
PUBLIC.mkdir(parents=True, exist_ok=True)

# 육안 검증 완료: serebii Dark Rush = JP BW4 UR (가디안/아케오스/캐처)
FIXES = [
    {
        "card_number": "074/069",
        "rarity": "UR",
        "name_kr": "가디안",
        "name_en": "Gardevoir",
        "src": "https://www.serebii.net/card/darkrush/74.jpg",
        "file": "074-069-UR.jpg",
    },
    {
        "card_number": "075/069",
        "rarity": "UR",
        "name_kr": "아케오스",
        "name_en": "Archeops",
        "src": "https://www.serebii.net/card/darkrush/75.jpg",
        "file": "075-069-UR.jpg",
    },
    {
        "card_number": "076/069",
        "rarity": "UR",
        "name_kr": "포켓몬 캐처",
        "name_en": "Pokémon Catcher",
        "src": "https://www.serebii.net/card/darkrush/76.jpg",
        "file": "076-069-UR.jpg",
    },
]

client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
set_id = sb.table("card_sets").select("id").eq("set_code", "BW4").single().execute().data["id"]

for fix in FIXES:
    resp = client.get(fix["src"])
    resp.raise_for_status()
    im = Image.open(io.BytesIO(resp.content)).convert("RGB")
    dest = PUBLIC / fix["file"]
    im.save(dest, quality=92, optimize=True)
    # 로컬 공개 경로 — 배포 전에도 workers가 쓰려면 배포 필요. 우선 절대 URL은 serebii로도 가능하나
    # 사이트 자산은 /card-images/... 사용
    public_url = f"/card-images/BW4/{fix['file']}"
    # DB에는 배포 URL 전체 또는 상대경로. 기존 collectory는 절대 URL.
    # Next Image는 상대 경로 OK. 카드 상세도 상대 OK.
    rows = (
        sb.table("cards")
        .select("id,name_kr,image_url")
        .eq("set_id", set_id)
        .eq("card_number", fix["card_number"])
        .eq("rarity", fix["rarity"])
        .execute()
        .data
        or []
    )
    if not rows:
        print("MISSING ROW", fix["card_number"], "→ insert")
        sb.table("cards").insert(
            {
                "set_id": set_id,
                "card_number": fix["card_number"],
                "rarity": fix["rarity"],
                "rarity_rank": 18,
                "name_kr": fix["name_kr"],
                "name_en": fix["name_en"],
                "name_jp": "",
                "image_url": public_url,
            }
        ).execute()
    else:
        for row in rows:
            print(
                f"fix id={row['id']} {fix['card_number']} "
                f"{row.get('name_kr')} → {fix['name_kr']} | {row.get('image_url')} → {public_url}"
            )
            sb.table("cards").update(
                {
                    "name_kr": fix["name_kr"],
                    "name_en": fix["name_en"],
                    "image_url": public_url,
                }
            ).eq("id", row["id"]).execute()
    print("saved", dest, im.size)

print("done")
