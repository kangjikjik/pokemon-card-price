"""
확장팩(KR) 시세를 N팩씩 배치로 수집 — 번개장터 전용.
상태 파일로 다음 배치 위치를 기억한다.

  python crawl_prices_batch.py --apply --daily      # 전 팩 순환(일일 권장)
  python crawl_prices_batch.py --apply              # RECrawl_FROM 이후 재수집 모드
  python crawl_prices_batch.py --apply --batch 0
  python crawl_prices_batch.py --apply --set MG4
  python crawl_prices_batch.py --list --daily

일일 자동 실행: crawler/scripts/run_daily_price_batch.ps1 / GitHub Actions
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

from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from kr_sets import KR_SETS  # noqa: E402
from utils.db import get_supabase  # noqa: E402

load_dotenv()
sb = get_supabase()

SEEDS_DIR = Path(__file__).resolve().parent
STATE_PATH = SEEDS_DIR / "_batch_state.json"
CRAWLER = SEEDS_DIR / "crawl_set_prices.py"
# 이미 개선 정책으로 시세 수집 완료한 팩 — 배치 대상에서 제외
SKIP_SETS = frozenset({"MG6", "MG5a"})
# 이 팩(포함)부터 발매 최신순 전체 재수집 (기존 시세 있어도 덮어씀)
RECrawl_FROM = "MG5"


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


def sets_needing_prices(*, daily: bool = False) -> list[tuple[str, str, int, int]]:
    """(code, name_kr, card_count, priced_count).

    daily=True: featured 전체 순환.
    daily=False: RECrawl_FROM 이후, SKIP_SETS 제외(일회성 재수집).
    """
    out: list[tuple[str, str, int, int]] = []
    started = daily
    for s in KR_SETS:
        if not daily and s.code in SKIP_SETS:
            continue
        if not started:
            if s.code == RECrawl_FROM:
                started = True
            else:
                continue
        # 번개장터 전용 — collectory_id 유무와 무관하게 모든 세트 수집
        row = sb.table("card_sets").select("id").eq("set_code", s.code).execute().data
        if not row:
            continue
        sid = row[0]["id"]
        cards = (
            sb.table("cards")
            .select("id,rarity")
            .eq("set_id", sid)
            .execute()
            .data
            or []
        )
        cards = [c for c in cards if is_displayable_rarity(c.get("rarity"))]
        if not cards:
            continue
        priced = (
            sb.table("prices_kr")
            .select("card_id")
            .in_("card_id", [c["id"] for c in cards])
            .gt("price_krw", 0)
            .execute()
            .data
            or []
        )
        out.append((s.code, s.name_kr, len(cards), len(priced)))
    return out


def batch_sets(need: list[tuple[str, str, int, int]], batch_size: int) -> list[list[str]]:
    codes = [c[0] for c in need]
    return [codes[i : i + batch_size] for i in range(0, len(codes), batch_size)]


def run_set(set_code: str, apply: bool, thorough: bool, quiet: bool = True) -> int:
    cmd = [sys.executable, str(CRAWLER), "--set", set_code]
    if apply:
        cmd.append("--apply")
    if thorough:
        cmd.append("--thorough")
    if quiet:
        cmd.append("--quiet")
    if "--previous-day" in sys.argv:
        cmd.append("--previous-day")
    print(f"\n{'=' * 60}\n>>> {set_code} 시작: {' '.join(cmd)}\n{'=' * 60}")
    return subprocess.call(cmd, cwd=str(SEEDS_DIR))


def main() -> None:
    apply = "--apply" in sys.argv
    thorough = "--thorough" in sys.argv
    quiet = "--verbose" not in sys.argv
    list_only = "--list" in sys.argv
    daily = "--daily" in sys.argv
    batch_size = int(get_arg("--size", "3") or "3")
    single_set = get_arg("--set", "")

    need = sets_needing_prices(daily=daily)
    batches = batch_sets(need, batch_size)

    if list_only:
        if daily:
            print("모드: 일일 순환 (featured 전체)")
        else:
            skipped = ", ".join(sorted(SKIP_SETS))
            print(f"모드: 재수집 (제외 {skipped}, from {RECrawl_FROM})")
        print(f"시세 대상: {len(need)}팩, 배치 크기 {batch_size} → {len(batches)}회")
        for i, batch in enumerate(batches):
            detail = [f"{c}({next(n for x, n, _, _ in need if x == c)})" for c in batch]
            print(f"  batch {i}: {', '.join(detail)}")
        return

    if single_set:
        targets = [single_set.upper()]
    elif "--all" in sys.argv:
        targets = [c for c, _, _, _ in need]
    else:
        state = load_state()
        batch_idx = int(get_arg("--batch", str(state["next_batch"])))
        if batch_idx >= len(batches):
            print(f"배치 {batch_idx} 없음 — 전체 {len(batches)}배치 완료. next_batch=0 으로 리셋.")
            batch_idx = 0
        targets = batches[batch_idx] if batches else []
        print(f"배치 {batch_idx}/{max(len(batches) - 1, 0)}: {', '.join(targets) or '(없음)'}")

    if not targets:
        print("시세 수집 대상 팩 없음.")
        return

    kst = timezone(timedelta(hours=9))
    started = datetime.now(kst).isoformat(timespec="seconds")
    failed: list[str] = []

    for code in targets:
        rc = run_set(code, apply=apply, thorough=thorough, quiet=quiet)
        if rc != 0:
            failed.append(code)

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

    if "--all" in sys.argv:
        from batch_promo import run_promo_for_region

        promo_failed = run_promo_for_region(
            "KR",
            apply=apply,
            quiet=quiet,
            previous_day_only="--previous-day" in sys.argv,
        )
        if promo_failed:
            print(f"\n프로모 KR 실패: {', '.join(promo_failed)}")
            sys.exit(1)

    print("\n배치 완료.")


if __name__ == "__main__":
    main()
