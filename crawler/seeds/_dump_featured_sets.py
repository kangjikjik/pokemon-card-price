"""Dump featured sets for JP MSRP mapping."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from seeds.kr_sets import KR_SETS  # noqa: E402

out = Path(__file__).with_name("_audit_out") / "featured_sets.tsv"
out.parent.mkdir(parents=True, exist_ok=True)
lines = [f"{s.code}\t{s.name_kr}\t{s.released_at}\t{s.msrp_pack_kr}\t{s.msrp_box_kr}" for s in KR_SETS]
out.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {len(lines)} -> {out}")
