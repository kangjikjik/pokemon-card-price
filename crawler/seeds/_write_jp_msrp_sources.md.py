"""Re-apply + write human-readable JP MSRP source list."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

subprocess.check_call([sys.executable, "fill_jp_msrp_verified.py", "--apply"])
rep = json.loads(Path("_audit_out/jp_msrp_sources.json").read_text(encoding="utf-8"))
ok = [r for r in rep if r.get("packJP")]
zero = [r for r in rep if not r.get("packJP")]

lines = [
    "# 일본판 발매가 출처 목록",
    "",
    "## 검증 기준",
    "",
    "- **팩 희망소매가격**: [포켓몬 카드 게임 공식(pokemon-card.com)](https://www.pokemon-card.com) 제품 페이지",
    "- **박스 정가**: [포켓몬센터 온라인](https://www.pokemoncenter-online.com) BOX 상품에서 税込 가격·1BOX=N팩을 확인한 뒤, 같은 규격은 `공식 팩가 × 팩수`",
    "- 공식에 가격이 없으면 **추정치를 넣지 않음 (0)**",
    "",
    "## 포켓몬센터 BOX 직접 확인",
    "",
    "| 세트 | 박스(税込) | 팩수 | URL |",
    "|---|---:|---:|---|",
    "| メガブレイブ | 5400 | 30 | https://www.pokemoncenter-online.com/9900000006211.html |",
    "| ニンジャスピナー | 5400 | 30 | https://www.pokemoncenter-online.com/9900000007898.html |",
    "| ブラックボルト | 5800 | 20 | https://www.pokemoncenter-online.com/9900000006082.html |",
    "",
    "## 규격별 박스 산출",
    "",
    "| 규격 | 예시 | 산출 |",
    "|---|---|---|",
    "| 표준 확장팩 180円×30 | 메가브레이브 등 | 5400 (PC BOX와 일치) |",
    "| MEGA 신가격 200円×30 | 어비스아이 | 6000 |",
    "| 구세대 165円×30 | 소드/실드 초기 | 4950 |",
    "| SM시대 150円×30 | 울트라썬 등 | 4500 |",
    "| 강화확장 260円×30 | 다크판타스마/GO 등 | 7800 |",
    "| 강화확장 290円×20 | 151 / 블랙볼트 | 5800 (PC BOX와 일치) |",
    "| 하이클래스 550円×10 | 샤이니트레저/VSTAR유니버스 | 5500 |",
    "| 하이클래스 500円×10 | GX울트라샤이니/태그올스타즈 | 5000 |",
    "",
    f"## 세트별 출처 ({len(ok)}/{len(rep)} 검증)",
    "",
    "| code | packJP | boxJP | packs | 공식 URL |",
    "|---|---:|---:|---:|---|",
]
for r in ok:
    lines.append(
        f"| {r['code']} | {r['packJP']} | {r['boxJP']} | {r.get('packs', '')} | {r.get('officialUrl', '')} |"
    )
lines += ["", "## 미기입 (공식 가격 없음)", ""]
for r in zero:
    lines.append(f"- **{r['code']}** {r.get('name_kr', '')}: 공식 제품 페이지에 희망소매가격 미표기/삭제 → 미기입")

out = Path("_audit_out/JP_MSRP_SOURCES.md")
out.write_text("\n".join(lines), encoding="utf-8")
print(f"OK={len(ok)} ZERO={len(zero)} -> {out}")
for r in zero:
    print(" zero", r["code"], r.get("name_kr"))
