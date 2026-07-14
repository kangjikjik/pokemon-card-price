"""전체 45 갭 세트 코드·collectory 메타 생성"""
from __future__ import annotations

import httpx
from analyze_timeline_gaps import eligible
from gap_sets import CODE_BY_NAME

rows: list[dict] = []
codes_used: dict[str, str] = {}
for m in eligible:
    name = m.get("name_ko") or ""
    if name not in CODE_BY_NAME:
        print(f"UNMAPPED: {name} | {m.get('release_date_ko')} | {m['id']}")
        continue
    code, display = CODE_BY_NAME[name]
    if code in codes_used:
        print(f"DUP CODE {code}: {codes_used[code]} vs {name}")
    codes_used[code] = name
    rows.append({
        "code": code,
        "name_kr": display,
        "released_at": m.get("release_date_ko") or "",
        "box_image_kr": m.get("image_url") or "",
        "bs_code": m.get("set_code_ko") or "",
        "collectory_id": m["id"],
        "card_count": m["card_count"],
    })

rows.sort(key=lambda r: r["released_at"], reverse=True)
print(f"\ntotal mapped: {len(rows)}")
for r in rows:
    print(
        f"{r['code']:6} {r['released_at']:12} cards={r['card_count']:3} "
        f"{r['name_kr'][:28]:28} {r['bs_code']}"
    )
