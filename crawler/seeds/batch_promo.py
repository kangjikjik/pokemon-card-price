"""프로모(P) 시세 — 확장팩 KR/JP `--all` 배치 성공 직후 실행 (TRADE_CRAWL_CRITERIA.md §17.1).

`crawl_prices_batch.py` / `crawl_prices_batch_jp.py`에서 import.
대상: promo_catalog.PROMO_SET_CODES → crawl_promo_prices.py --set … --region KR|JP
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from promo_catalog import PROMO_SET_CODES

SEEDS_DIR = Path(__file__).resolve().parent
CRAWLER = SEEDS_DIR / "crawl_promo_prices.py"


def run_promo_for_region(
    region: str,
    *,
    apply: bool,
    quiet: bool,
    previous_day_only: bool = False,
) -> list[str]:
    """region: KR | JP. 실패한 set_code 목록 반환."""
    region = region.upper()
    if region not in ("KR", "JP"):
        raise ValueError(f"region must be KR or JP, got {region!r}")

    failed: list[str] = []
    print(f"\n===== Promo cards ({region}, bundled with expansion batch) =====")
    for code in PROMO_SET_CODES:
        cmd = [
            sys.executable,
            str(CRAWLER),
            "--set",
            code,
            "--region",
            region,
        ]
        if apply:
            cmd.append("--apply")
        if quiet:
            cmd.append("--quiet")
        from lib.crawl_incremental import forward_incremental_flags  # noqa: E402
        forward_incremental_flags(cmd)
        print(f">>> promo {code} ({region})")
        if subprocess.call(cmd, cwd=str(SEEDS_DIR)) != 0:
            failed.append(code)
    return failed
