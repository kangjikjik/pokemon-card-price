"""XY3 UR 누락 + EBB1 EX(N)→RR 및 제크로무 UR 보완. 이미지 육안 검증된 소스만 사용."""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

from collectory_map import COLLECTORY_API
from kr_sets import KR_BY_CODE
from lib.rarity_rank import rank_for_rarity
from seed_from_collectory import (
    is_ex_card,
    normalize_card_number,
    pick_name_ko,
    resolve_rarity,
)

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "web" / "public" / "card-images"
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
APPLY = "--apply" in sys.argv


def save_image(url: str, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = client.get(url)
    resp.raise_for_status()
    im = Image.open(io.BytesIO(resp.content)).convert("RGB")
    im.save(dest, quality=92, optimize=True)
    rel = "/" + dest.relative_to(ROOT / "web" / "public").as_posix()
    print(f"  image {rel} {im.size} from {url}")
    return rel


def upsert(set_id: int, num: str, rarity: str, name_kr: str, name_en: str, image_url: str) -> str:
    rows = (
        sb.table("cards")
        .select("id,name_kr,image_url")
        .eq("set_id", set_id)
        .eq("card_number", num)
        .eq("rarity", rarity)
        .execute()
        .data
        or []
    )
    payload = {
        "set_id": set_id,
        "card_number": num,
        "rarity": rarity,
        "rarity_rank": rank_for_rarity(rarity),
        "name_kr": name_kr,
        "name_en": name_en,
        "name_jp": "",
        "image_url": image_url,
    }
    if rows:
        if APPLY:
            sb.table("cards").update(payload).eq("id", rows[0]["id"]).execute()
        return f"update id={rows[0]['id']}"
    if APPLY:
        sb.table("cards").insert(payload).execute()
    return "insert"


def fix_xy3() -> None:
    print("=== XY3 라이징피스트 UR 2장 (공식 RR6+SR7+UR2) ===")
    set_id = sb.table("card_sets").select("id").eq("set_code", "XY3").single().execute().data["id"]
    manuals = [
        ("104/096", "UR", "M헤라크로스 EX", "M Heracross EX", "https://www.serebii.net/card/risingfist/104.jpg", "104-096-UR.jpg"),
        ("105/096", "UR", "M루카리오 EX", "M Lucario EX", "https://www.serebii.net/card/risingfist/105.jpg", "105-096-UR.jpg"),
    ]
    for num, rar, name_kr, name_en, src, fname in manuals:
        rel = save_image(src, PUBLIC / "XY3" / fname)
        action = upsert(set_id, num, rar, name_kr, name_en, rel)
        print(f"  {action} {num} {rar} {name_kr}")


def fix_ebb1() -> None:
    print("=== EBB1 EX배틀부스트 — N표기 EX→RR + 제크로무 UR ===")
    meta = KR_BY_CODE["EBB1"]
    set_id = sb.table("card_sets").select("id").eq("set_code", "EBB1").single().execute().data["id"]
    raw = client.get(f"{COLLECTORY_API}/sets/{meta.collectory_id}/cards").json().get("cards") or []
    has_rr = any((c.get("rarity") or "").upper() == "RR" for c in raw)

    # 1) EX(N) → RR
    inserted = 0
    for card in raw:
        rar = resolve_rarity(card, has_rr)
        # force N+EX → RR even if resolve not yet updated
        raw_r = (card.get("rarity") or "").strip().upper()
        if not rar and raw_r == "N" and is_ex_card(card):
            rar = "RR"
        if rar != "RR":
            continue
        num = normalize_card_number(card.get("card_number") or "")
        if not num:
            continue
        image_url = (card.get("cdn_image_url") or card.get("image_url") or "").strip()
        name_kr = pick_name_ko(card, None)
        name_en = (card.get("name_en") or card.get("name") or "").strip()
        action = upsert(set_id, num, "RR", name_kr, name_en, image_url)
        print(f"  {action} {num} RR {name_kr}")
        inserted += 1
    print(f"  EX→RR candidates: {inserted}")

    # 2) UR 제크로무 095 (collectory에 없음)
    rel = save_image(
        "https://www.serebii.net/card/exbattleboost/95.jpg",
        PUBLIC / "EBB1" / "095-093-UR.jpg",
    )
    action = upsert(set_id, "095/093", "UR", "제크로무 EX", "Zekrom EX", rel)
    print(f"  {action} 095/093 UR 제크로무 EX")

    # 3) ensure 094 uses collectory KR/JP image if present
    for card in raw:
        if normalize_card_number(card.get("card_number") or "") == "094/093":
            url = (card.get("cdn_image_url") or card.get("image_url") or "").strip()
            if url:
                action = upsert(set_id, "094/093", "UR", pick_name_ko(card, "레시라무 EX"), "Reshiram EX", url)
                print(f"  {action} 094/093 UR refresh image")


def main() -> None:
    print(f"apply={APPLY}")
    fix_xy3()
    fix_ebb1()
    if not APPLY:
        print("\n드라이런 — 반영: python fix_xy3_ebb1_gaps.py --apply")


if __name__ == "__main__":
    main()
