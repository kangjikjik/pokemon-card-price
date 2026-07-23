"""
스페셜·기념 제품 시드 — CEL25PK(P)만.

  python seed_commemorative.py --apply
"""
from __future__ import annotations

import os
import sys
import time

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from promo_catalog import COMMEMORATIVE_25PK  # noqa: E402
from seed_promo_cards import ensure_promo_set, fetch_cards, is_promo_raw, upsert_card  # noqa: E402

load_dotenv()
APPLY = "--apply" in sys.argv


def seed_25pk(client: httpx.Client) -> int:
    src = COMMEMORATIVE_25PK
    print(f"\n[{src.code}] {src.name_kr} (P)")
    from promo_catalog import PromoSource

    ps = PromoSource(
        src.code,
        src.collectory_id,
        src.name_kr,
        src.released_at,
        src.image_url,
    )
    set_id = ensure_promo_set(ps) or -1
    raw = fetch_cards(client, src.collectory_id)
    promos = [c for c in raw if is_promo_raw(c)]
    n = 0
    for card in promos:
        if upsert_card(set_id, card) in ("insert", "update"):
            n += 1
    print(f"  P cards={n}")
    return n


def main() -> None:
    print(f"mode={'APPLY' if APPLY else 'DRY-RUN'}")
    client = httpx.Client(headers={"User-Agent": "pokemon-card-price/1.0"})
    seed_25pk(client)


if __name__ == "__main__":
    main()
