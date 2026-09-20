"""공식 포켓몬코리아 상세페이지에서 확인된 이미지 URL만 적용한다."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


def main() -> None:
    sb = get_supabase()
    checked = json.loads(
        Path("_audit_out/all_80_official_image_check.json").read_text(
            encoding="utf-8"
        )
    )
    applied = []
    for card in checked:
        url = card.get("official_image_url") or ""
        if card.get("status") != "matched" or not url:
            continue
        rows = (
            sb.table("cards")
            .update({"image_url": url})
            .eq("id", card["card_id"])
            .execute()
            .data
            or []
        )
        if rows:
            applied.append(
                {
                    "set_name": card["set_name"],
                    "card_id": card["card_id"],
                    "card_number": card["card_number"],
                    "image_url": url,
                }
            )
    Path("_audit_out/official_confirmed_images_apply.json").write_text(
        json.dumps(applied, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"applied": len(applied)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
