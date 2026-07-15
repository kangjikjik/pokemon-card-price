"""
확장팩 시세를 N팩씩 배치로 수집. 상태 파일로 다음 배치 위치를 기억한다.

  python crawl_prices_batch.py --apply              # 다음 배치(기본 3팩)
  python crawl_prices_batch.py --apply --batch 0    # 첫 배치부터
  python crawl_prices_batch.py --apply --set MG4    # 특정 팩만
  python crawl_prices_batch.py --list               # 배치 목록만 출력

일일 자동 실행: crawler/scripts/run_daily_price_batch.ps1
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from lib.rarity_rank import is_displayable_rarity  # noqa: E402
from kr_sets import KR_SETS  # noqa: E402

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

SEEDS_DIR = Path(__file__).resolve().parent
STATE_PATH = SEEDS_DIR / "_batch_state.json"
CRAWLER = SEEDS_DIR / "crawl_set_prices.py"
# 이미 시세 수집 완료한 최신 4팩 — 배치 대상에서 제외
SKIP_SETS = frozenset({"MG5", "MG4a", "MG6", "MG5a"})


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


def sets_needing_prices() -> list[tuple[str, str, int, int]]:
    """(code, name_kr, card_count, priced_count) — 발매일 최신순, SKIP_SETS 제외."""
    out: list[tuple[str, str, int, int]] = []
    for s in KR_SETS:
        if s.code in SKIP_SETS or not s.collectory_id:
            continue
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
        if len(priced) < len(cards):
            out.append((s.code, s.name_kr, len(cards), len(priced)))
    return out


def batch_sets(need: list[tuple[str, str, int, int]], batch_size: int) -> list[list[str]]:
    codes = [c[0] for c in need]
    return [codes[i : i + batch_size] for i in range(0, len(codes), batch_size)]


def run_set(set_code: str, apply: bool, thorough: bool) -> int:
    cmd = [sys.executable, str(CRAWLER), "--set", set_code]
    if apply:
        cmd.append("--apply")
    if thorough:
        cmd.append("--thorough")
    print(f"\n{'=' * 60}\n>>> {set_code} 시작: {' '.join(cmd)}\n{'=' * 60}")
    return subprocess.call(cmd, cwd=str(SEEDS_DIR))


def main() -> None:
    apply = "--apply" in sys.argv
    thorough = "--thorough" in sys.argv
    list_only = "--list" in sys.argv
    batch_size = int(get_arg("--size", "3") or "3")
    single_set = get_arg("--set", "")

    need = sets_needing_prices()
    batches = batch_sets(need, batch_size)

    if list_only:
        skipped = ", ".join(sorted(SKIP_SETS))
        print(f"제외(시세 완료): {skipped}")
        print(f"시세 필요: {len(need)}팩, 배치 크기 {batch_size} → {len(batches)}회")
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
        rc = run_set(code, apply=apply, thorough=thorough)
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

    print("\n배치 완료.")


if __name__ == "__main__":
    main()
