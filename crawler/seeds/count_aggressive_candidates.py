from __future__ import annotations
import json
from pathlib import Path
P = Path("_audit_out/aggressive_proposals.json")
data = json.loads(P.read_text(encoding="utf-8"))
cnt = 0
for p in data.get("proposals", []):
    c = p.get("candidate")
    if c and ( (c.get("name_kr") or "").strip() or (c.get("image_url") or "").strip() ):
        cnt += 1
print(cnt)
