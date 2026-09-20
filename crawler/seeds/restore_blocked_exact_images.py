"""메타데이터 완전일치지만 CSP 차단됐던 이미지들을 검증 후 복원한다."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_supabase


def main() -> None:
    report = json.loads(Path("_audit_out/refill_all70_daldagury_safe.json").read_text(encoding="utf-8"))
    candidates = [row for row in report["unresolved"] if row.get("reason") == "blocked_or_non_daldagury_source" and row.get("candidate_url")]
    sb = get_supabase()
    applied = []
    unresolved = []
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "pokemon-card-price/1.0"}) as client:
        for row in candidates:
            url = row["candidate_url"]
            try:
                response = client.get(url)
                response.raise_for_status()
                if not (response.headers.get("content-type") or "").startswith("image/"):
                    raise ValueError("not_image_content_type")
                with Image.open(io.BytesIO(response.content)) as image:
                    image.verify()
                sb.table("cards").update({"image_url": url}).eq("id", row["id"]).execute()
                applied.append({**row, "image_url": url})
            except Exception as exc:
                unresolved.append({**row, "reason": f"invalid_image:{exc}"})
    result = {"applied": applied, "unresolved": unresolved, "applied_count": len(applied)}
    Path("_audit_out/restore_blocked_exact_images.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"applied_count": len(applied), "unresolved_count": len(unresolved), "unresolved": unresolved}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
