"""collectory 세트 카드 수·레어도 분포 미리보기"""
import httpx

MAP = {
    "SV2a": "1d7e469a-95d9-4710-a9c3-09ad381b40cc",
    "SV3a": "ce26060e-4031-4a90-a3db-dbf7a05baed1",
    "SV4a": "43856548-fd3a-4ef2-bf29-56a7f1f2ca47",
    "SV2D": "b55b3827-f1fd-442f-8617-c608d44628d9",
    "SV5a": "bbee3837-55ea-4980-8ee1-e8e0cc545163",
    "SV8a": "931578b6-e8a8-4159-88a1-3c8a2ddb62b4",
    "SV7": "44ed33eb-c792-421f-8525-4510c91c109d",
    "SV1S": "31608bab-a5f6-415a-b7ed-7c02173e7616",
    "SV1V": "22653f4f-f3b7-496c-b25e-2f48566c0e00",
    "MG6": "611cf371-dafe-42fc-b86d-895aa433e10d",
    "MG4a": "dd132c1d-b070-4e07-9674-1fd469ee49fb",
}

SKIP = {"U", "C", "SA", "N", "CM", "UM", "PROMO"}


def parse_rarity(card):
    r = (card.get("rarity") or "").strip()
    num = card.get("card_number") or ""
    if r in SKIP and "/" in num:
        suffix = num.split("/")[-1]
        for prefix in ("RR", "SR", "AR", "SAR", "UR", "ACE", "IR", "MUR"):
            if suffix.upper().endswith(prefix):
                return prefix
        if len(suffix) > 0 and suffix[-1] in "CUR" and suffix[:-1].isdigit():
            return suffix[-1]
        if suffix.endswith("M") and len(suffix) > 1:
            return None  # master variant
    if r in SKIP:
        return None
    if r == "HR":
        return "UR"
    return r


def main():
    for code, sid in MAP.items():
        r = httpx.get(f"https://collectory.cc/api/sets/{sid}/cards", timeout=60)
        cards = r.json().get("cards", [])
        kept = []
        for c in cards:
            rarity = parse_rarity(c)
            if not rarity:
                continue
            num = c.get("card_number", "")
            if num.endswith("M") or "CM" in num.split("/")[-1]:
                continue
            kept.append(c)
        print(f"{code}: total={len(cards)} kept={len(kept)}")


if __name__ == "__main__":
    main()
