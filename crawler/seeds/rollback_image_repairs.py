"""잘못 적용된 공식 이미지 보정 실행을 보고서 기준으로 원복한다."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.db import get_supabase


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="append", required=True)
    args = parser.parse_args()

    sb = get_supabase()
    restored = 0
    seen: set[int] = set()
    # 최신 실행부터 원복한다.
    for report_path in args.report:
        body = json.loads(Path(report_path).read_text(encoding="utf-8"))
        for change in body.get("changes", []):
            card_id = int(change["card_id"])
            if card_id in seen:
                continue
            payload: dict[str, str] = {}
            if change.get("old_name") != change.get("new_name"):
                payload["name_kr"] = change.get("old_name") or ""
            if change.get("old_image_url") != change.get("new_image_url"):
                payload["image_url"] = change.get("old_image_url") or ""
            if payload:
                sb.table("cards").update(payload).eq("id", card_id).execute()
                restored += 1
            seen.add(card_id)
    print(f"원복 완료: {restored}장")


if __name__ == "__main__":
    main()
