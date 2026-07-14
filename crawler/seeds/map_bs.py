import httpx
from pathlib import Path

sets = httpx.get("https://collectory.cc/api/sets", timeout=30).json()["sets"]
codes = [
    "BS2023014", "BS2023006", "BS2023007", "BS2024001", "BS2024017",
    "BS2025001", "BS2025015", "BS2026004", "BS2023010", "BS2023011", "BS2023012",
]
lines = []
for c in codes:
    m = [s for s in sets if s.get("set_code_ko") == c]
    if m:
        s = m[0]
        u = s.get("image_url") or ""
        lines.append(f"{c}\t{s.get('name_en','')}\t{u}")
Path(__file__).with_name("bs_map.txt").write_text("\n".join(lines), encoding="utf-8")
