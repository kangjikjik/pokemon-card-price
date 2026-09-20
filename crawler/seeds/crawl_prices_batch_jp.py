"""
일본판 시세 배치 — 번개장터 전용 (Collectory JP · 유유테이 제거).

  python crawl_prices_batch_jp.py --apply --all
  python crawl_prices_batch_jp.py --apply --set MG6

일일 자동: crawler/scripts/run_daily_price_batch.ps1 / GitHub Actions
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from kr_sets import KR_SETS  # noqa: E402

SEEDS_DIR = Path(__file__).resolve().parent
STATE_PATH = SEEDS_DIR / "_batch_state_jp.json"
CRAWLER = SEEDS_DIR / "crawl_set_prices_jp.py"


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"next_batch": 0, "last_run": None, "last_sets": []}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def target_codes() -> list[str]:
    """모든 featured 팩 (발매 최신순) — 번개장터 전용이므로 유유테이 vers 무관."""
    return [s.code for s in KR_SETS]


def batch_sets(codes: list[str], batch_size: int) -> list[list[str]]:
    return [codes[i : i + batch_size] for i in range(0, len(codes), batch_size)]


def run_set(set_code: str, apply: bool, quiet: bool = True) -> int:
    cmd = [sys.executable, str(CRAWLER), "--set", set_code]
    if apply:
        cmd.append("--apply")
    if quiet:
        cmd.append("--quiet")
    if "--previous-day" in sys.argv:
        cmd.append("--previous-day")
    print(f"\n{'=' * 60}\n>>> JP {set_code}\n{'=' * 60}")
    return subprocess.call(cmd, cwd=str(SEEDS_DIR))


def main() -> None:
    apply = "--apply" in sys.argv
    quiet = "--verbose" not in sys.argv
    list_only = "--list" in sys.argv
    batch_size = int(get_arg("--size", "5") or "5")
    pause_seconds = int(get_arg("--pause", "0") or "0")
    single_set = get_arg("--set", "")
    run_all = "--all" in sys.argv

    codes = target_codes()
    batches = batch_sets(codes, batch_size)

    if list_only:
        print(f"JP 대상: {len(codes)}팩, 배치 크기 {batch_size} → {len(batches)}회")
        for i, batch in enumerate(batches):
            print(f"  batch {i}: {', '.join(batch)}")
        return

    if single_set:
        targets = [single_set]
    elif run_all:
        targets = codes
    else:
        state = load_state()
        batch_idx = int(get_arg("--batch", str(state["next_batch"])))
        if batch_idx >= len(batches):
            print(f"배치 {batch_idx} 없음 — 리셋 → 0")
            batch_idx = 0
        targets = batches[batch_idx] if batches else []
        print(f"JP 배치 {batch_idx}/{max(len(batches) - 1, 0)}: {', '.join(targets) or '(없음)'}")

    if not targets:
        print("JP 시세 대상 없음.")
        return

    kst = timezone(timedelta(hours=9))
    started = datetime.now(kst).isoformat(timespec="seconds")
    failed: list[str] = []

    for index, code in enumerate(targets):
        rc = run_set(code, apply=apply, quiet=quiet)
        if rc != 0:
            failed.append(code)
            if run_all:
                print(f"\n[경고] JP {code} 실패 — 다음 세트 계속 진행")
            else:
                break
        if run_all and pause_seconds > 0 and (index + 1) % batch_size == 0 and index + 1 < len(targets):
            print(f"\n배치 휴식: {batch_size}팩 완료, {pause_seconds}초")
            time.sleep(pause_seconds)

    if apply and not single_set and "--all" not in sys.argv:
        state = load_state()
        batch_idx = int(get_arg("--batch", str(state["next_batch"])))
        if not failed:
            state["next_batch"] = (batch_idx + 1) % max(len(batches), 1)
        state["last_run"] = started
        state["last_sets"] = targets
        state["failed"] = failed
        save_state(state)
        print(f"\n상태 저장 → next_batch={state['next_batch']} ({STATE_PATH.name})")

    if failed:
        print(f"\n실패: {', '.join(failed)}")
        sys.exit(1)

    if run_all:
        from batch_promo import run_promo_for_region

        promo_failed = run_promo_for_region("JP", apply=apply, quiet=quiet)
        if promo_failed:
            print(f"\n프로모 JP 실패: {', '.join(promo_failed)}")
            sys.exit(1)

    print("\nJP 배치 완료.")


if __name__ == "__main__":
    main()
