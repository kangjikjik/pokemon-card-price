"""
박스 시세 배치 — featured 82팩 순환 (KR / JP).

  python crawl_box_prices_batch.py --apply --all
  python crawl_box_prices_batch.py --apply --all --region JP
  python crawl_box_prices_batch.py --apply --set MG6 --region JP
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

from kr_sets import KR_SETS  # noqa: E402
from lib.crawl_incremental import (  # noqa: E402
    exit_if_caught_up,
    forward_incremental_flags,
    get_incremental_days,
    mark_crawl_kst_complete,
    print_incremental_banner,
    read_last_crawl_kst,
)
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()

SEEDS_DIR = Path(__file__).resolve().parent
CRAWLER = SEEDS_DIR / "crawl_box_prices.py"


def _state_path(region: str) -> Path:
    return SEEDS_DIR / ("_box_batch_state_jp.json" if region == "JP" else "_box_batch_state.json")


def get_arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


def load_state(region: str) -> dict:
    path = _state_path(region)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"next_batch": 0, "last_run": None, "last_sets": []}


def save_state(state: dict, region: str) -> None:
    _state_path(region).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def target_sets(region: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for s in KR_SETS:
        if region == "KR" and not s.msrp_box_kr:
            continue
        row = sb.table("card_sets").select("id").eq("set_code", s.code).execute().data
        if row:
            out.append((s.code, s.name_kr))
    return out


def batch_sets(codes: list[str], batch_size: int) -> list[list[str]]:
    return [codes[i : i + batch_size] for i in range(0, len(codes), batch_size)]


def run_set(set_code: str, apply: bool, region: str = "KR") -> int:
    cmd = [sys.executable, str(CRAWLER), "--set", set_code]
    if region.upper() == "JP":
        cmd.extend(["--region", "JP"])
    if apply:
        cmd.append("--apply")
    forward_incremental_flags(cmd)
    cmd.append("--quiet")
    label = "JP" if region.upper() == "JP" else "KR"
    print(f"\n{'=' * 60}\n>>> {set_code} {label} 박스 시세\n{'=' * 60}")
    return subprocess.call(cmd, cwd=str(SEEDS_DIR))


def main() -> None:
    incr = get_incremental_days(sys.argv, sb)
    if incr is not None:
        last = read_last_crawl_kst(sb)
        print_incremental_banner(incr, last_crawl=last)
        exit_if_caught_up(incr, last_crawl=last)

    apply = "--apply" in sys.argv
    list_only = "--list" in sys.argv
    single_set = get_arg("--set", "").upper()
    batch_size = int(get_arg("--size", "5") or "5")
    region = get_arg("--region", "KR").upper()
    if region != "JP":
        region = "KR"

    need = target_sets(region)
    codes = [c for c, _ in need]
    batches = batch_sets(codes, batch_size)

    if list_only:
        label = "JP" if region == "JP" else "KR"
        print(f"{label} 박스 시세 대상: {len(need)}팩, 배치 크기 {batch_size} → {len(batches)}회")
        for i, batch in enumerate(batches):
            detail = [f"{c}({next(n for x, n in need if x == c)})" for c in batch]
            print(f"  batch {i}: {', '.join(detail)}")
        return

    if single_set:
        targets = [single_set]
    elif "--all" in sys.argv:
        targets = codes
    else:
        state = load_state(region)
        batch_idx = int(get_arg("--batch", str(state["next_batch"])))
        if batch_idx >= len(batches):
            batch_idx = 0
        targets = batches[batch_idx] if batches else []
        print(f"배치 {batch_idx}/{max(len(batches) - 1, 0)}: {', '.join(targets) or '(없음)'}")

    if not targets:
        print("박스 시세 수집 대상 없음.")
        return

    kst = timezone(timedelta(hours=9))
    started = datetime.now(kst).isoformat(timespec="seconds")
    failed: list[str] = []

    for code in targets:
        rc = run_set(code, apply=apply, region=region)
        if rc != 0:
            failed.append(code)

    if apply and not single_set and "--all" not in sys.argv:
        state = load_state(region)
        batch_idx = int(get_arg("--batch", str(state["next_batch"])))
        if not failed:
            state["next_batch"] = (batch_idx + 1) % max(len(batches), 1)
        state["last_run"] = started
        state["last_sets"] = targets
        state["failed"] = failed
        save_state(state, region)

    if failed:
        print(f"\n실패: {', '.join(failed)}")
        sys.exit(1)

    if (
        apply
        and "--catch-up" in sys.argv
        and "--all" in sys.argv
        and region == "JP"
        and not failed
    ):
        mark_crawl_kst_complete()
        print("catch-up 완료 → last_crawl_kst 갱신")

    print("\n배치 완료.")


if __name__ == "__main__":
    main()
