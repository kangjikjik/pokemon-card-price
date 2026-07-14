"""Probe deterministic CDN image URLs for cards missing image_url."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")

JP_CODE = {
    "S2": ["S2", "s2"],
    "S7D": ["S7D", "s7D", "S7d", "s7d"],
    "S7F": ["S8", "s8"],
    "S11": ["S11", "s11"],
    "S12": ["S12", "s12"],
    "SM9": ["SM9a", "sm9a"],
}


def norm_parts(num: str) -> tuple[str, str]:
    left, right = (num or "").split("/", 1)
    return left.zfill(3), right


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    sets = sb.table("card_sets").select("id,set_code").execute().data or []
    set_by_id = {s["id"]: s["set_code"] for s in sets}
    cards = []
    offset = 0
    while True:
        batch = (
            sb.table("cards")
            .select("id,set_id,card_number,rarity,name_kr,name_jp,image_url")
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        cards.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    cards = [c for c in cards if not (c.get("image_url") or "").strip()]

    out = Path(__file__).with_name("_audit_out") / "missing_image_probe"
    out.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    for c in sorted(cards, key=lambda x: (set_by_id[x["set_id"]], x.get("card_number") or "")):
        code = set_by_id[c["set_id"]]
        if code not in JP_CODE:
            continue
        left, right = norm_parts(c.get("card_number") or "")
        rar = c.get("rarity") or ""
        candidates = []
        for jp in JP_CODE[code]:
            candidates.extend([
                f"https://cdn.collectory.cc/cards/jp/{jp}/{left}_{right}{rar}.webp",
                f"https://cdn.collectory.cc/cards/jp/{jp}/{left}_{right}.webp",
                f"https://cdn.collectory.cc/cards/jp/{jp}/{int(left)}_{right}{rar}.webp",
                f"https://cdn.collectory.cc/cards/jp/{jp}/{int(left)}_{right}.webp",
            ])
        found = []
        for url in candidates:
            try:
                r = client.get(url)
            except Exception:
                continue
            if r.status_code == 200 and len(r.content) > 5000:
                found.append(url)
                suffix = ".webp"
                out.joinpath(f"{code}_{left}_{right}_{rar}{suffix}").write_bytes(r.content)
                break
        print(f"{code:6} {c.get('card_number'):8} {rar:4} found={found[:1]} name={c.get('name_kr') or c.get('name_jp')}")


if __name__ == "__main__":
    main()
