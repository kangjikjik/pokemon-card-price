"""DB box_image_url sync + final pack/ACE verification"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from supabase import create_client

from audit_packs_full import load_bytes
from kr_sets import KR_SETS

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
OUT = Path(__file__).parent / "_audit_out"
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public"


def ring_stats(data: bytes) -> tuple[float, float]:
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    ring = []
    for x in range(w):
        for y in range(min(3, h)):
            ring.append(im.getpixel((x, y)))
        for y in range(max(0, h - 3), h):
            ring.append(im.getpixel((x, y)))
    for y in range(h):
        for x in range(min(3, w)):
            ring.append(im.getpixel((x, y)))
        for x in range(max(0, w - 3), w):
            ring.append(im.getpixel((x, y)))
    white = sum(1 for r, g, b in ring if r >= 235 and g >= 235 and b >= 235) / len(ring)
    dark = sum(1 for r, g, b in ring if r + g + b < 120) / len(ring)
    return white, dark


# sync DB urls from KR_SETS
sets = sb.table("card_sets").select("id,set_code,box_image_url").execute().data or []
by_db = {s["set_code"]: s for s in sets}
synced = 0
for s in KR_SETS:
    row = by_db.get(s.code)
    if not row or not s.box_image_kr:
        continue
    if row.get("box_image_url") != s.box_image_kr:
        sb.table("card_sets").update({"box_image_url": s.box_image_kr}).eq("id", row["id"]).execute()
        synced += 1
        print(f"DB sync {s.code}: {s.box_image_kr}")
print(f"DB synced {synced}")

# pack audit
bad = []
soft = []
ok = 0
for s in KR_SETS:
    data, kind = load_bytes(s.box_image_kr or "") if s.box_image_kr else (b"", "empty")
    if not data:
        bad.append((s.code, "no_data", kind))
        continue
    wr, dr = ring_stats(data)
    if wr >= 0.15 and dr < 0.45:
        bad.append((s.code, f"white={wr:.2f}", s.name_kr))
    elif wr >= 0.08:
        soft.append((s.code, f"white={wr:.2f}", s.name_kr))
    else:
        ok += 1

print(f"\nPACK ring OK={ok} soft={len(soft)} bad={len(bad)} / total={len(KR_SETS)}")
for x in soft:
    print("  SOFT", x)
for x in bad:
    print("  BAD ", x)

# ACE verify
ace = sb.table("cards").select("id,name_kr,card_number,set_id,rarity").eq("rarity", "ACE").execute().data or []
set_ids = list({r["set_id"] for r in ace})
sets2 = sb.table("card_sets").select("id,set_code").in_("id", set_ids).execute().data or []
by_id = {s["id"]: s["set_code"] for s in sets2}
print(f"\nACE count={len(ace)}")
false_ids = {3480, 3485, 3488, 3493, 3501, 3527, 3531}
still = [r for r in ace if r["id"] in false_ids]
print(f"false ACE still present: {len(still)}")
for r in sorted(ace, key=lambda x: (by_id.get(x["set_id"], ""), x.get("card_number") or "")):
    print(f"  {by_id.get(r['set_id'],'?'):6} #{(r.get('card_number') or ''):10} {r.get('name_kr')}")

# visual re-check remaining ACE against ace_visual if present
vis_path = OUT / "ace_visual.json"
if vis_path.exists():
    vis = json.loads(vis_path.read_text(encoding="utf-8"))
    remaining_ids = {r["id"] for r in ace}
    remaining_false = [v for v in vis if not v.get("visual_ace") and v["id"] in remaining_ids]
    remaining_ok = [v for v in vis if v.get("visual_ace") and v["id"] in remaining_ids]
    print(f"\nvisual among remaining: OK={len(remaining_ok)} FALSE={len(remaining_false)}")
