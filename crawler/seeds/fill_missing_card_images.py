"""Fill missing card image_url from collectory expected RR+ catalog when exact set/number/rarity matches."""
from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from fill_oldest_rr_plus import expected_catalog  # noqa: E402
from kr_sets import KR_BY_CODE, KR_SETS  # noqa: E402

APPLY = "--apply" in sys.argv


def norm_num(num: str) -> str:
    if "/" not in (num or ""):
        return num or ""
    left, right = num.split("/", 1)
    try:
        return f"{int(left):03d}/{right}"
    except ValueError:
        return num


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    set_rows = sb.table("card_sets").select("id,set_code").execute().data or []
    set_by_id = {r["id"]: r["set_code"] for r in set_rows}
    featured_ids = [r["id"] for r in set_rows if r["set_code"] in {s.code for s in KR_SETS}]
    cards = []
    offset = 0
    while True:
        batch = (
            sb.table("cards")
            .select("id,set_id,card_number,rarity,name_kr,name_jp,name_en,image_url")
            .in_("set_id", featured_ids)
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        cards.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    missing = [c for c in cards if not (c.get("image_url") or "").strip()]
    client = httpx.Client(timeout=90, follow_redirects=True)
    catalogs: dict[str, dict[tuple[str, str], dict]] = {}
    fixed = 0
    unresolved = []
    print(f"missing={len(missing)} apply={APPLY}")
    for c in sorted(missing, key=lambda x: (set_by_id[x["set_id"]], x.get("card_number") or "")):
        code = set_by_id[c["set_id"]]
        s = KR_BY_CODE.get(code)
        if not s or not s.collectory_id:
            unresolved.append((c, "no_collectory"))
            continue
        if code not in catalogs:
            catalogs[code] = expected_catalog(code, s.collectory_id, client)
        catalog = catalogs[code]
        key = (norm_num(c.get("card_number") or ""), c.get("rarity") or "")
        # expected_catalog may use non-padded for MG; build normalized lookup.
        normalized = {(norm_num(num), rar): card for (num, rar), card in catalog.items()}
        cand = normalized.get(key)
        img = ""
        if cand:
            img = (cand.get("cdn_image_url") or cand.get("image_url") or "").strip()
        if not img:
            unresolved.append((c, "no_candidate_image"))
            print(f"NOIMG {code:6} {c.get('card_number'):8} {c.get('rarity'):4} {c.get('name_kr') or c.get('name_jp')}")
            continue
        print(f"FIX   {code:6} {c.get('card_number'):8} {c.get('rarity'):4} -> {img}")
        if APPLY:
            sb.table("cards").update({"image_url": img}).eq("id", c["id"]).execute()
        fixed += 1

    print(f"\nfixed_candidates={fixed} unresolved={len(unresolved)}")
    for c, why in unresolved:
        print(f"  {why}: {set_by_id[c['set_id']]} {c.get('card_number')} {c.get('rarity')} {c.get('name_kr') or c.get('name_jp')}")


if __name__ == "__main__":
    main()
