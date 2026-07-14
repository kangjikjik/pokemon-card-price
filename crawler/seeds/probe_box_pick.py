import httpx

sets = httpx.get("https://collectory.cc/api/sets", timeout=30).json()["sets"]
targets = ["SV2a", "SV3a", "SV2D", "SV5a", "SV1S", "SV1V", "MG6"]
for code in targets:
    rows = [s for s in sets if code.upper() in (s.get("set_code_ja") or "").upper() or code in (s.get("set_code_ko") or "")]
    rows.sort(key=lambda x: x.get("card_count") or 0, reverse=True)
    print(f"\n=== {code} ===")
    for s in rows[:4]:
        img = s.get("image_url") or ""
        tag = "KR" if "pokemonkorea" in img else ("BOX" if "/sets/" in img and "cards/sets" not in img else "LOGO")
        print(f"  {tag} {s.get('set_code_ja')} {s.get('set_code_ko')} cnt={s.get('card_count')} {img[:85]}")
