"""Download BW4 card images for visual name/image verification."""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
client = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
out = Path("_img_audit/wrong_check")
out.mkdir(parents=True, exist_ok=True)

sid = sb.table("card_sets").select("id").eq("set_code", "BW4").single().execute().data["id"]
rows = (
    sb.table("cards")
    .select("id,card_number,rarity,name_kr,image_url")
    .eq("set_id", sid)
    .order("card_number")
    .execute()
    .data
    or []
)
print("=== BW4 DB ===")
for r in rows:
    print(r["id"], r["rarity"], r["card_number"], r["name_kr"], r["image_url"])
    try:
        resp = client.get(r["image_url"])
        ct = resp.headers.get("content-type", "")
        if resp.status_code == 200 and "image" in ct:
            im = Image.open(io.BytesIO(resp.content))
            safe = r["card_number"].replace("/", "-")
            path = out / f"BW4_{safe}_{r['rarity']}.png"
            im.save(path)
            print("  saved", im.size, path.name)
        else:
            print("  BAD IMAGE", resp.status_code, ct)
    except Exception as e:
        print("  ERR", e)

print("\n=== serebii reference ===")
for i in (74, 75, 76):
    u = f"https://www.serebii.net/card/darkrush/{i:03d}.jpg"
    resp = client.get(u)
    print(i, resp.status_code, len(resp.content), u)
    if resp.status_code == 200:
        Image.open(io.BytesIO(resp.content)).save(out / f"serebii_{i}.jpg")

# also collectory KR images for RR/SR EX
print("\n=== collectory EX samples ===")
from collectory_map import COLLECTORY_API
from kr_sets import KR_BY_CODE

meta = KR_BY_CODE["BW4"]
raw = client.get(f"{COLLECTORY_API}/sets/{meta.collectory_id}/cards").json().get("cards") or []
for card in raw:
    num = card.get("card_number") or ""
    if num in ("009/069", "070/069", "044/069", "072/069"):
        url = card.get("cdn_image_url") or card.get("image_url")
        print(num, card.get("rarity"), card.get("name_ko"), url)
        if url:
            resp = client.get(url)
            if resp.status_code == 200 and "image" in resp.headers.get("content-type", ""):
                Image.open(io.BytesIO(resp.content)).save(
                    out / f"col_{num.replace('/', '-')}_{card.get('rarity')}.png"
                )
