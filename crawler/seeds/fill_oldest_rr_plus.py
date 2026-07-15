"""
과거 확장팩 N개: 팩에 나오는 RR 이상(및 BW시대 EX=R → RR)을
collectory(+수동 보완) 기준으로 DB에 전부 넣고 완전성 검증.

실행:
  python fill_oldest_rr_plus.py           # 드라이런
  python fill_oldest_rr_plus.py --apply   # DB 반영
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from collectory_map import COLLECTORY_API  # noqa: E402
from kr_sets import KR_SETS  # noqa: E402
from lib.rarity_rank import rank_for_rarity, is_displayable_rarity  # noqa: E402
from seed_from_collectory import (  # noqa: E402
    RARITY_OVERRIDES,
    SEED_SKIP,
    normalize_card_number,
    parse_rarity,
    pick_name_ko,
)

LIMIT = 20 if "--all" not in sys.argv else 9999
APPLY = "--apply" in sys.argv

RR_PLUS = {
    "RR",
    "SR", "AR", "SAR", "UR", "ACE", "BWR", "MUR", "MA", "FUR",
    "SSR", "HR", "CSR", "PR",
}

EX_NAME_RE = re.compile(r"(?:\bEX\b|ＥＸ|(?<![A-Za-z])ex(?![A-Za-z]))")

# collectory에 빠진 시크릿 — 공식 리스트 기준 수동 보완
MANUAL_SUPPLEMENTS: dict[str, list[dict]] = {
    "SM5+": [
        {
            "card_number": "103/094",
            "rarity": "HR",
            "name_kr": "개굴닌자 GX",
            "name_en": "Greninja GX",
            "image_url": "/card-images/SM5plus/103-094-HR.webp",
        },
        {
            "card_number": "104/094",
            "rarity": "HR",
            "name_kr": "지가르데 GX",
            "name_en": "Zygarde GX",
            "image_url": "/card-images/SM5plus/104-094-HR.webp",
        },
        {
            "card_number": "105/094",
            "rarity": "HR",
            "name_kr": "이벨타르 GX",
            "name_en": "Yveltal GX",
            "image_url": "/card-images/SM5plus/105-094-HR.webp",
        },
        {
            "card_number": "106/094",
            "rarity": "HR",
            "name_kr": "제르네아스 GX",
            "name_en": "Xerneas GX",
            "image_url": "/card-images/SM5plus/106-094-HR.webp",
        },
        {
            "card_number": "107/094",
            "rarity": "HR",
            "name_kr": "울트라네크로즈마 GX",
            "name_en": "Ultra Necrozma GX",
            "image_url": "/card-images/SM5plus/107-094-HR.webp",
        },
        {
            "card_number": "108/094",
            "rarity": "UR",
            "name_kr": "에너지 포터",
            "name_en": "Eneporter",
            "image_url": "/card-images/SM5plus/108-094-UR.png",
        },
        {
            "card_number": "109/094",
            "rarity": "UR",
            "name_kr": "미스터리 트레져",
            "name_en": "Mystery Treasure",
            "image_url": "/card-images/SM5plus/109-094-UR.webp",
        },
        {
            "card_number": "110/094",
            "rarity": "UR",
            "name_kr": "유닛 에너지 격투 악 페어리",
            "name_en": "Unit Energy Fighting Darkness Fairy",
            "image_url": "/card-images/SM5plus/110-094-UR.webp",
        },
    ],
    "BW4": [
        {
            "card_number": "074/069",
            "rarity": "UR",
            "name_kr": "가디안",
            "name_en": "Gardevoir",
            "image_url": "/card-images/BW4/074-069-UR.jpg",
        },
        {
            "card_number": "075/069",
            "rarity": "UR",
            "name_kr": "아케오스",
            "name_en": "Archeops",
            "image_url": "/card-images/BW4/075-069-UR.jpg",
        },
        {
            "card_number": "076/069",
            "rarity": "UR",
            "name_kr": "포켓몬 캐처",
            "name_en": "Pokémon Catcher",
            "image_url": "/card-images/BW4/076-069-UR.jpg",
        },
    ],
}


def oldest_sets(n: int):
    sets = [s for s in KR_SETS if s.collectory_id]
    sets.sort(key=lambda s: (s.released_at, s.code))
    return sets[:n]


def is_ex_card(card: dict) -> bool:
    for key in ("name_ko", "name_kr", "name", "name_en", "name_ja"):
        if EX_NAME_RE.search(card.get(key) or ""):
            return True
    return False


def display_rarity(card: dict, set_has_native_rr: bool) -> str | None:
    """표시용 등급. BW 등 RR 심볼 없던 팩의 EX(R)는 RR로 승격."""
    num = normalize_card_number(card.get("card_number") or "")
    set_code = card.get("_set_code") or ""
    if (set_code, num) in SEED_SKIP:
        return None

    rarity = parse_rarity(card)
    if (set_code, num) in RARITY_OVERRIDES:
        rarity = RARITY_OVERRIDES[(set_code, num)]

    if rarity and rarity in RR_PLUS:
        return rarity

    raw = (card.get("rarity") or "").strip().upper()
    # RR 심볼이 없던 세트: 포켓몬 EX(R) → RR
    if not set_has_native_rr and raw == "R" and is_ex_card(card):
        return "RR"
    return None


def expected_catalog(set_code: str, collectory_id: str, client: httpx.Client) -> dict[tuple[str, str], dict]:
    raw = client.get(f"{COLLECTORY_API}/sets/{collectory_id}/cards", timeout=90).json().get("cards") or []
    set_has_rr = any((c.get("rarity") or "").upper() == "RR" for c in raw)

    out: dict[tuple[str, str], dict] = {}
    for card in raw:
        card = {**card, "_set_code": set_code}
        rarity = display_rarity(card, set_has_rr)
        if not rarity:
            continue
        num = normalize_card_number(card.get("card_number") or "")
        if not num:
            continue
        out[(num, rarity)] = card

    for manual in MANUAL_SUPPLEMENTS.get(set_code, []):
        key = (manual["card_number"], manual["rarity"])
        if key not in out:
            out[key] = {
                "card_number": manual["card_number"],
                "rarity": manual["rarity"],
                "name_ko": manual.get("name_kr", ""),
                "name_en": manual.get("name_en", ""),
                "cdn_image_url": manual.get("image_url", ""),
                "image_url": manual.get("image_url", ""),
                "_manual": True,
            }
    return out


def upsert_card(sb, set_id: int, num: str, rarity: str, card: dict, existing_by_num: dict) -> str:
    image_url = (card.get("cdn_image_url") or card.get("image_url") or "").strip()
    name_en = (card.get("name_en") or card.get("name") or "").strip()
    name_jp = (card.get("name_ja") or "").strip()
    payload = {
        "set_id": set_id,
        "card_number": num,
        "rarity": rarity,
        "rarity_rank": rank_for_rarity(rarity),
        "name_kr": pick_name_ko(card, None),
        "name_en": name_en,
        "name_jp": name_jp or name_en,
        "image_url": image_url,
    }

    rows = existing_by_num.get(num) or []
    match = next((r for r in rows if r.get("rarity") == rarity), None)
    if not match and rows:
        # 같은 번호에 다른 등급만 있으면 신규 insert (SR/RR 공존)
        match = None
    if match:
        sb.table("cards").update(payload).eq("id", match["id"]).execute()
        return "updated"
    sb.table("cards").insert(payload).execute()
    return "inserted"


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=90, follow_redirects=True)
    targets = oldest_sets(LIMIT)

    print(f"대상 {LIMIT}개 (오래된순), apply={APPLY}\n")
    grand = Counter()

    for s in targets:
        expected = expected_catalog(s.code, s.collectory_id, client)
        set_rows = sb.table("card_sets").select("id").eq("set_code", s.code).execute().data or []
        if not set_rows:
            print(f"[SKIP] {s.code} DB 세트 없음")
            continue
        set_id = set_rows[0]["id"]

        db_all = (
            sb.table("cards")
            .select("id,card_number,rarity,name_kr,image_url")
            .eq("set_id", set_id)
            .execute()
            .data
            or []
        )
        db_rr = [c for c in db_all if (c.get("rarity") or "") in RR_PLUS]
        db_keys = {(c.get("card_number") or "", c.get("rarity") or "") for c in db_rr}
        existing_by_num: dict[str, list] = defaultdict(list)
        for c in db_all:
            existing_by_num[c.get("card_number") or ""].append(c)

        missing = [k for k in expected if k not in db_keys]
        # DB에만 있는 RR+ (잘못된 잔여) — expected에 없으면 보고만 (삭제하지 않음: 수동 UR 등)
        extra = [c for c in db_rr if (c.get("card_number") or "", c.get("rarity") or "") not in expected]

        dist_exp = Counter(r for _, r in expected)
        dist_db = Counter(c.get("rarity") for c in db_rr)

        print(f"=== {s.code} {s.name_kr} ===")
        print(f"  팩 RR+ 기대: {len(expected)} {dict(dist_exp)}")
        print(f"  DB RR+ 현재: {len(db_rr)} {dict(dist_db)}")
        print(f"  누락: {len(missing)} | DB만 있음: {len(extra)}")

        if missing:
            for num, rar in missing[:20]:
                card = expected[(num, rar)]
                name = card.get("name_ko") or card.get("name_kr") or card.get("name_en") or card.get("name") or ""
                tag = "MANUAL" if card.get("_manual") else "COL"
                print(f"    + [{tag}] {num} {rar} {name}")
            if len(missing) > 20:
                print(f"    ... +{len(missing) - 20}")

        if APPLY and missing:
            # refresh existing map after each insert batch
            for num, rar in missing:
                card = expected[(num, rar)]
                action = upsert_card(sb, set_id, num, rar, card, existing_by_num)
                grand[action] += 1
                # keep local map fresh
                if action == "inserted":
                    existing_by_num[num].append({"id": -1, "card_number": num, "rarity": rar})

            # re-count
            db_all = (
                sb.table("cards")
                .select("id,card_number,rarity")
                .eq("set_id", set_id)
                .execute()
                .data
                or []
            )
            db_rr = [c for c in db_all if (c.get("rarity") or "") in RR_PLUS]
            db_keys = {(c.get("card_number") or "", c.get("rarity") or "") for c in db_rr}
            still = [k for k in expected if k not in db_keys]
            print(f"  → 적용 후 DB {len(db_rr)} / 기대 {len(expected)} / 남은누락 {len(still)}")
            grand["ok_sets" if not still else "partial_sets"] += 1
        else:
            grand["ok_sets" if not missing else "gap_sets"] += 1
        print()

    print("=" * 50)
    print(dict(grand))
    if not APPLY:
        print("드라이런 — 반영: python fill_oldest_rr_plus.py --apply")


if __name__ == "__main__":
    main()
