import httpx

MAP = {
    "SV2a": ("BS2023014", "SV2a"),
    "SV3a": ("", "SV3a"),
    "SV4a": ("BS2024001", ""),
    "SV2D": ("", "SV2D"),
    "SV5a": ("", "SV6a"),
    "SV8a": ("BS2025001", ""),
    "SV7": ("BS2024017", ""),
    "SV1S": ("BS2023006", "SV1S"),
    "SV1V": ("BS2023007", "SV1V"),
    "MG6": ("BS2026004", "M5"),
    "MG4a": ("BS2025015", ""),
}

sets = httpx.get("https://collectory.cc/api/sets", timeout=30).json()["sets"]
lines = []
for code, (ko, ja) in MAP.items():
    matches = [
        s for s in sets
        if (ko and s.get("set_code_ko") == ko)
        or (ja and (s.get("set_code_ja") or "").upper() == ja.upper())
    ]
    matches.sort(key=lambda x: x.get("card_count") or 0, reverse=True)
    best = matches[0] if matches else None
    if best:
        img = best.get("image_url") or ""
        lines.append(f"{code}\t{best.get('id')}\t{img}")
    else:
        lines.append(f"{code}\tNOT_FOUND\t")

Path = __import__("pathlib").Path
Path(__file__).with_name("probe_box_kr_out.txt").write_text("\n".join(lines), encoding="utf-8")
print("written")
