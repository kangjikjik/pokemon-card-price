"""ACE 카드 이미지 다운로드 — ACE SPEC 표기 육안 검증용"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent / "_audit_out"
IMG = Path(__file__).parent / "_img_audit" / "ace"
IMG.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

rows = json.loads((OUT / "ace_db.json").read_text(encoding="utf-8"))
print(f"download {len(rows)} ACE images")
ok = 0
for r in rows:
    url = r.get("image_url") or ""
    code = r["set_code"]
    num = (r["card_number"] or "x").replace("/", "-")
    name = r["name_kr"][:20]
    if not url:
        print(f"  NOIMG {code} {num} {name}")
        continue
    try:
        data = client.get(url).content
        ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
        path = IMG / f"{code}_{num}{ext}"
        path.write_bytes(data)
        ok += 1
        print(f"  OK {path.name} ({len(data)}) {name}")
    except Exception as e:
        print(f"  FAIL {code} {num}: {e}")
print(f"saved {ok}/{len(rows)}")
