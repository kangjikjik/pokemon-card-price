"""Write KR MSRP audit markdown from kr_msrp_audit.json."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

subprocess.check_call([sys.executable, "audit_kr_msrp.py", "--json"])
data = json.loads(Path("_audit_out/kr_msrp_audit.json").read_text(encoding="utf-8"))
rows = data.get("rows") or []
summary = data.get("summary") or {}
ok = [r for r in rows if r.get("status") == "OK"]
bad = [r for r in rows if r.get("status") != "OK"]

lines = [
    "# 한국판 발매가 출처 목록",
    "",
    "## 검증 기준",
    "",
    "- **팩/박스 희망소매가격**: [포켓몬카드 공식(pokemoncard.co.kr)](https://pokemoncard.co.kr) 제품 페이지",
    "- 각 세트 `pokemoncard_page` 번호와 `kr_sets.py` / `set-msrp.ts`의 packKR·boxKR 대조",
    "",
    f"## 세트별 출처 ({summary.get('ok', len(ok))}/{summary.get('sets', len(rows))} 검증)",
    "",
    "| code | packKR | boxKR | page | URL |",
    "|---|---:|---:|---:|---|",
]
for r in ok:
    lines.append(
        f"| {r['code']} | {r.get('expected_pack', r.get('packKR', 0))} | "
        f"{r.get('expected_box', r.get('boxKR', 0))} | {r.get('page', '')} | {r.get('url', '')} |"
    )
if bad:
    lines += ["", "## 미검증", ""]
    for r in bad:
        lines.append(f"- **{r['code']}** {r.get('name_kr', '')}: {r.get('status', '')}")

out = Path("_audit_out/KR_MSRP_SOURCES.md")
out.write_text("\n".join(lines), encoding="utf-8")
print(f"OK={len(ok)} BAD={len(bad)} -> {out}")
