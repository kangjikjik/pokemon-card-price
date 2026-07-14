import httpx

MAP = {"MG6": "611cf371-dafe-42fc-b86d-895aa433e10d", "SV2a": "1d7e469a-95d9-4710-a9c3-09ad381b40cc"}
SKIP = {"U", "C", "SA", "N", "CM", "UM", "PROMO"}


def parse_rarity(card):
    r = (card.get("rarity") or "").strip()
    num = card.get("card_number") or ""
    if r in SKIP and "/" in num:
        suffix = num.split("/")[-1]
        for prefix in ("UR-ex", "UR", "SAR", "SR", "AR", "IR", "ACE", "RR", "MUR"):
            if suffix.upper().endswith(prefix):
                return prefix
    if r in SKIP:
        return None
    if r == "HR":
        return "UR"
    return r


for code, sid in MAP.items():
    cards = httpx.get(f"https://collectory.cc/api/sets/{sid}/cards", timeout=60).json()["cards"]
    from collections import Counter
    c = Counter()
    for card in cards:
        pr = parse_rarity(card)
        if pr:
            c[pr] += 1
    print(code, dict(c))
