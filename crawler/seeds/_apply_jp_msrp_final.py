"""Fill last verifiable JP MSRP gaps; leave unverifiable as 0."""
from __future__ import annotations

import json

import httpx
import fill_jp_msrp_verified as m
from kr_sets import KR_SETS

# 추가 검증 URL (공식 페이지에서 팩가 확인됨)
EXTRA = {
    "S8a": ("スターバース", "https://www.pokemon-card.com/ex/s9/"),  # JP s9=스타버스
    "S7F": ("フュージョンアーツ", "https://www.pokemon-card.com/products/s/s8.html"),  # 동시대 165円 제품페이지
    "SM12": ("オルタージェネシス", "https://www.pokemon-card.com/ex/sm12/"),
    "SM11a": ("ミラクルツイン", "https://www.pokemon-card.com/ex/sm11a/"),
    "SM11b": ("ドリームリーグ", "https://www.pokemon-card.com/ex/sm11b/"),
}
for k, v in EXTRA.items():
    m.JP_URL[k] = v

# 검증 불가(공식에 희망소매가격 미표기/페이지 없음) — 0 유지
UNVERIFIED = {"CEL", "S7R", "S7D", "SM9", "SM9a"}
for code in UNVERIFIED:
    m.JP_URL[code] = ("", "")

client = httpx.Client(headers=m.HEADERS, follow_redirects=True, timeout=30)
results = {}
report = []
for s in KR_SETS:
    entry = m.JP_URL.get(s.code)
    if not entry or not entry[1]:
        results[s.code] = {"packJP": 0, "boxJP": 0, "sourceJP": ""}
        report.append({
            "code": s.code,
            "name_kr": s.name_kr,
            "packJP": 0,
            "boxJP": 0,
            "status": "UNVERIFIED_NO_OFFICIAL_PRICE",
            "note": "공식 페이지에 희망소매가격 없음/삭제 — 추정치 미기입",
        })
        print(f"SKIP {s.code}")
        continue
    jp_name, url = entry
    pack_yen, status = m.scrape_pack_yen(client, url)
    box_yen, packs, box_src, note = (
        m.resolve_box(s.code, pack_yen) if pack_yen else (0, 0, url, status)
    )
    results[s.code] = {
        "packJP": pack_yen,
        "boxJP": box_yen if pack_yen else 0,
        "sourceJP": url if pack_yen else "",
    }
    report.append({
        "code": s.code,
        "name_kr": s.name_kr,
        "jpName": jp_name,
        "packJP": pack_yen,
        "boxJP": box_yen if pack_yen else 0,
        "packs": packs,
        "officialUrl": url,
        "boxVerifyUrl": box_src,
        "note": note,
        "status": status,
    })
    print(f"{'OK' if pack_yen else 'FAIL'} {s.code:6} {pack_yen:4}/{box_yen:5}")

m.OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
m.write_msrp(results)
print(f"done verified={sum(1 for r in report if r.get('packJP'))}/{len(report)}")
