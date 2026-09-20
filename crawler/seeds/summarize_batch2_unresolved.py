"""두 번째 35팩 미처리 카드의 팩별 집계."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    report = json.loads(Path("_audit_out/daldagury_batch2_35_verified_apply.json").read_text(encoding="utf-8"))
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in report["unresolved"]:
        grouped[row["reason"]][row["set_code"]].append(row.get("card_number") or "")
    output = {
        reason: {
            code: {"count": len(numbers), "cards": sorted(numbers)}
            for code, numbers in sorted(by_set.items())
        }
        for reason, by_set in sorted(grouped.items())
    }
    Path("crawler/seeds/_batch_logs/batch2_unresolved_by_pack.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
