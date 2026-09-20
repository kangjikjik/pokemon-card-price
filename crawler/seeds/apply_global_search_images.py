"""달다구리 전체 검색에서 실제 이미지가 확인된 카드만 적용한다."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


def main() -> None:
    sb = get_supabase()
    report = json.loads(
        Path("_audit_out/final_23_global_search_image_check.json").read_text(
            encoding="utf-8"
        )
    )
    applied = []
    skipped = []
    for card in report["found"]:
        url = card.get("source_url") or ""
        if "noimage" in url.lower():
            skipped.append(card)
            continue
        rows = (
            sb.table("cards")
            .update({"image_url": url})
            .eq("id", card["card_id"])
            .execute()
            .data
            or []
        )
        applied.append({**card, "updated": bool(rows)})
    output = {"applied": applied, "skipped_noimage": skipped}
    Path("_audit_out/global_search_images_apply.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "applied": sum(item["updated"] for item in applied),
                "skipped_noimage": len(skipped),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
