"""
스페셜·기념 제품 시드 — CEL25PK(P)만.

  python seed_commemorative.py --apply
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from reseed_cel25pk_official import OFFICIAL_CARDS, main as reseed_official_25pk  # noqa: E402

load_dotenv()
APPLY = "--apply" in sys.argv


def seed_25pk() -> int:
    print("\n[CEL25PK] 25주년 기념 프로모팩 (P)")
    if APPLY:
        reseed_official_25pk()
    else:
        print(f"  [dry] would upsert official cards={len(OFFICIAL_CARDS)}")
    return len(OFFICIAL_CARDS)


def main() -> None:
    print(f"mode={'APPLY' if APPLY else 'DRY-RUN'}")
    seed_25pk()


if __name__ == "__main__":
    main()
