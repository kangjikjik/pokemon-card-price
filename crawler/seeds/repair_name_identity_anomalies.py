"""달다구리 이름 대조에서 확인된 카드 정체성 오류를 보정한다."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


def medium(url: str) -> str:
    return url.replace("_thumb.webp", "_medium.webp")


def daldagury_card(set_id: int, number: str) -> dict:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        rows = client.get(
            f"https://api.daldagury.com/tcg/sets/{set_id}/cards?limit=500"
        ).json()["resultData"]["data"]
    return next(row for row in rows if row.get("numberInSet") == number)


def update(sb, card_id: int, values: dict) -> dict:
    rows = sb.table("cards").update(values).eq("id", card_id).execute().data or []
    return rows[0] if rows else {"id": card_id, **values}


def delete_card(sb, card_id: int) -> None:
    for table in ("prices_kr", "prices_jp"):
        sb.table(table).delete().eq("card_id", card_id).execute()
    sb.table("cards").delete().eq("id", card_id).execute()


def main() -> None:
    sb = get_supabase()
    changed = []

    # MG5a: two trainer names were exchanged.
    changed.append(update(sb, 3175, {"name_kr": "지프"}))
    changed.append(update(sb, 3177, {"name_kr": "마티에르"}))

    # SV2P: the previous failed encoding left corrupted Korean names.
    changed.append(update(sb, 1152, {"name_kr": "그루샤"}))
    changed.append(update(sb, 1153, {"name_kr": "피나"}))

    # SV1a already contains the correct 099 and 100 rows. Remove the
    # accidentally duplicated 099 row, retaining the existing canonical row.
    delete_card(sb, 1130)

    # S10b: image/Japanese identity is Elade V, not Paras.
    changed.append(update(sb, 7013, {"name_kr": "엘레이드 V"}))

    report = {
        "updated_card_ids": [row.get("id") for row in changed],
        "deleted_card_id": 1130,
        "deleted_reason": "SV1a 099/073 duplicate of canonical card id 4255",
    }
    Path("_audit_out/name_identity_repair.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
