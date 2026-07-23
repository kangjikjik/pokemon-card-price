"""
미발매 30주년(COL30) 세트·카드·시세 삭제.

  python purge_cel30.py --apply
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from purge_bulk_promo import delete_set  # noqa: E402

load_dotenv()
APPLY = "--apply" in sys.argv


def main() -> None:
    print(f"{'[APPLY]' if APPLY else '[DRY]'} purge CEL30")
    c, _ = delete_set("CEL30")
    print(f"removed cards={c}")


if __name__ == "__main__":
    main()
