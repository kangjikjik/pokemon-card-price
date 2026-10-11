"""
프로모 시세 수동 배치 (자동 파이프라인에서는 이 파일을 직접 돌리지 않음).

자동 파이프라인: run_daily_price_batch.ps1 → KR/JP 확장팩 배치 끝에 batch_promo.py 로 통합.
이 스크립트는 수동·부분 재수집용.

  python crawl_promo_prices_batch.py --list
  python crawl_promo_prices_batch.py --apply --batch 0
  python crawl_promo_prices_batch.py --apply --all
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from promo_catalog import PROMO_PRICE_CODES, PROMO_SET_CODES  # noqa: E402

load_dotenv()

SEEDS_DIR = Path(__file__).resolve().parent
STATE_PATH = SEEDS_DIR / "_promo_batch_state.json"
CRAWLER = SEEDS_DIR / "crawl_promo_prices.py"
BATCH_SIZE = 3


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"next_batch": 0, "last_run": None}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def batches() -> list[list[str]]:
    codes = list(PROMO_PRICE_CODES)
    return [codes[i : i + BATCH_SIZE] for i in range(0, len(codes), BATCH_SIZE)]


def run_set(code: str, apply: bool) -> int:
    cmd = [sys.executable, str(CRAWLER), "--set", code]
    if apply:
        cmd.append("--apply")
    cmd.append("--quiet")
    print(f">>> {code}: {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(SEEDS_DIR))


def main() -> None:
    apply = "--apply" in sys.argv
    all_sets = "--all" in sys.argv
    list_only = "--list" in sys.argv
    batch_groups = batches()

    if list_only:
        print(f"프로모 시세 배치: {len(PROMO_SET_CODES)}소스, batch={BATCH_SIZE}, {len(batch_groups)}회")
        for i, grp in enumerate(batch_groups):
            print(f"  batch {i}: {', '.join(grp)}")
        return

    if all_sets:
        targets = list(PROMO_SET_CODES)
    else:
        state = load_state()
        idx = int(get_arg("--batch", str(state["next_batch"])))
        if idx >= len(batch_groups):
            idx = 0
        targets = batch_groups[idx] if batch_groups else []
        print(f"batch {idx}/{max(len(batch_groups) - 1, 0)}: {', '.join(targets)}")

    failed: list[str] = []
    for code in targets:
        if run_set(code, apply) != 0:
            failed.append(code)

    if apply and not all_sets and targets:
        state = load_state()
        idx = int(get_arg("--batch", str(state["next_batch"])))
        if not failed:
            state["next_batch"] = (idx + 1) % max(len(batch_groups), 1)
        state["last_run"] = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
        save_state(state)

    if failed:
        print("failed:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
