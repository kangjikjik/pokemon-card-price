"""Fix 8 featured trainer SR cards missing name_kr."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

APPLY = "--apply" in sys.argv

# 공식 한국어 (pokemoncard.co.kr / 포켓몬코리아 트레이너 명칭)
BY_ID: dict[int, str] = {
    1668: "어릿광대",       # クラウン — 화이트플레어
    1667: "투희",           # トウコ
    1593: "로켓단의 아테나",  # ロケット団のアテナ
    1599: "로켓단의 아폴로",  # ロケット団のアポロ
    1152: "라이스",         # グルーシャ (공식: Grusha→라이스)
    1153: "페니",           # ピーニャ
    1130: "키하다",         # キハダ
    1135: "클라벨",         # クラベル
}

BY_JP: dict[str, str] = {
    "クラウン": "어릿광대",
    "トウコ": "투희",
    "ロケット団のアテナ": "로켓단의 아테나",
    "ロケット団のアポロ": "로켓단의 아폴로",
    "グルーシャ": "라이스",
    "ピーニャ": "페니",
    "キハダ": "키하다",
    "クラベル": "클라벨",
}


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    fixed = 0
    for cid, kr in BY_ID.items():
        row = sb.table("cards").select("id,name_jp,name_kr").eq("id", cid).single().execute().data
        if not row:
            print(f"SKIP id={cid}: not found")
            continue
        if row.get("name_kr") == kr:
            print(f"OK id={cid} already {kr}")
            continue
        print(f"FIX id={cid} {row.get('name_jp')!r} -> {kr}")
        if APPLY:
            sb.table("cards").update({"name_kr": kr}).eq("id", cid).execute()
        fixed += 1

    for jp, kr in BY_JP.items():
        rows = sb.table("cards").select("id,name_kr").eq("name_jp", jp).execute().data or []
        for row in rows:
            if row.get("name_kr") == kr:
                continue
            print(f"FIX jp={jp!r} id={row['id']} -> {kr}")
            if APPLY:
                sb.table("cards").update({"name_kr": kr}).eq("id", row["id"]).execute()
            fixed += 1

    print(f"\n{'applied' if APPLY else 'dry-run'} fixes: {fixed}")


if __name__ == "__main__":
    main()
