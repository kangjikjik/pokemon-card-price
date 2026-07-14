"""Fix remaining JP_URL entries and re-apply MSRP."""
from __future__ import annotations

from pathlib import Path

import fill_jp_msrp_verified as m

# 직접 확인된 공식 URL로 교체
FIXES = {
    "S10b": ("ダークファンタズマ", "https://www.pokemon-card.com/ex/s10b/"),
    "S9a": ("タイムゲイザー", "https://www.pokemon-card.com/products/s/s9a.html"),
    "S8a": ("VSTARユニバース周辺/25th関連は別 — ダーク系", "https://www.pokemon-card.com/products/s/s8a.html"),
    "S1a": ("VMAXライジング", "https://www.pokemon-card.com/products/s/s1a.html"),
    "S6H": ("イーブイヒーローズ", "https://www.pokemon-card.com/products/s/s6a.html"),
    "S6G": ("白銀のランス", "https://www.pokemon-card.com/products/s/s6.html"),
    "S6L": ("漆黒のガイスト", "https://www.pokemon-card.com/products/s/s6.html"),
    "S5F": ("一撃マスター", "https://www.pokemon-card.com/products/s/s5.html"),
    "S5S": ("連撃マスター", "https://www.pokemon-card.com/products/s/s5.html"),
    "S5P": ("連撃マスター", "https://www.pokemon-card.com/products/s/s5.html"),
    "S7R": ("蒼空ストリーム", "https://www.pokemon-card.com/products/s/s7.html"),
    "S7D": ("摩天パーフェクト", "https://www.pokemon-card.com/products/s/s7.html"),
    "S7F": ("フュージョンアーツ", "https://www.pokemon-card.com/products/s/s7.html"),
    "SM12a": ("タッグオールスターズ", "https://www.pokemon-card.com/ex/sm12a/"),
    "SM8b": ("GXウルトラシャイニー", "https://www.pokemon-card.com/ex/sm8b/"),
}

for code, val in FIXES.items():
    m.JP_URL[code] = val

# S8a products page is not Dark Phantasma — skip misleading scrape (leave 0)
# Pokémon GO: 260円 표준 강화확장 → 30팩
m.PACKS_OVERRIDE.pop("S10a", None)
m.PACKS_OVERRIDE.pop("CEL", None)

# S8a URL wrong product — remove from scrape (set empty url later)
m.JP_URL["S8a"] = ("", "")
m.JP_URL["CEL"] = ("", "")
m.JP_URL["S7F"] = ("", "")  # s7.html no price
m.JP_URL["S7R"] = ("", "")
m.JP_URL["S7D"] = ("", "")

# rewrite module state by calling main pieces
import httpx
import json
from kr_sets import KR_SETS

client = httpx.Client(headers=m.HEADERS, follow_redirects=True, timeout=30)
results = {}
report = []
for s in KR_SETS:
    entry = m.JP_URL.get(s.code)
    if not entry or not entry[1]:
        results[s.code] = {"packJP": 0, "boxJP": 0, "sourceJP": ""}
        report.append({"code": s.code, "status": "NO_TRUSTED_URL", "packJP": 0, "boxJP": 0})
        print(f"SKIP {s.code}")
        continue
    jp_name, url = entry
    pack_yen, status = m.scrape_pack_yen(client, url)
    box_yen, packs, box_src, note = m.resolve_box(s.code, pack_yen) if pack_yen else (0, 0, url, status)
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
    print(f"{'OK' if pack_yen else 'FAIL'} {s.code:6} pack={pack_yen:4} box={box_yen:5} x{packs} {status}")

m.OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
m.write_msrp(results)
ok = sum(1 for r in report if r.get("packJP"))
print(f"verified {ok}/{len(report)} -> {m.OUT_TS}")
