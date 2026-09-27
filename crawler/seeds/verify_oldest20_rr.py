"""과거 확장팩 20개 — RR 이상 등급이 DB에 맞게 들어갔는지 collectory와 교차 검증·수정."""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from collectory_map import COLLECTORY_API  # noqa: E402
from kr_sets import KR_SETS, KR_BY_CODE  # noqa: E402
from lib.rarity_rank import rank_for_rarity  # noqa: E402
from seed_from_collectory import (  # noqa: E402
    RARITY_OVERRIDES,
    SEED_SKIP,
    normalize_card_number,
    parse_rarity,
)

# RR(14) 이상 + 과거 하이엔드 등급
RR_PLUS = {
    "RR", "SR", "AR", "SAR", "UR", "ACE", "BWR", "MUR", "MA", "FUR",
    "SSR", "HR", "CSR", "CHR", "RRR", "A", "K", "S", "PR", "TR", "H", "CC", "P",
}

LIMIT_SETS = 20
APPLY = "--apply" in sys.argv


def oldest_sets(n: int) -> list:
    sets = [s for s in KR_SETS if s.collectory_id]
    sets.sort(key=lambda s: (s.released_at, s.code))
    return sets[:n]


def delete_card(sb, card_id: int) -> None:
    sb.table("prices_kr").delete().eq("card_id", card_id).execute()
    sb.table("prices_jp").delete().eq("card_id", card_id).execute()
    sb.table("cards").delete().eq("id", card_id).execute()


def expected_rr_plus(set_code: str, collectory_id: str, client: httpx.Client) -> dict[tuple[str, str], dict]:
    """(normalized_number, rarity) → raw collectory card"""
    cards = client.get(f"{COLLECTORY_API}/sets/{collectory_id}/cards", timeout=90).json().get("cards") or []
    out: dict[tuple[str, str], dict] = {}
    for card in cards:
        rarity = parse_rarity(card)
        if not rarity or rarity not in RR_PLUS:
            continue
        num = normalize_card_number(card.get("card_number") or "")
        if not num:
            continue
        if (set_code, num) in SEED_SKIP:
            continue
        if (set_code, num) in RARITY_OVERRIDES:
            rarity = RARITY_OVERRIDES[(set_code, num)]
            if rarity not in RR_PLUS:
                continue
        out[(num, rarity)] = card
    return out


def main() -> None:
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
    client = httpx.Client(timeout=90, follow_redirects=True)
    targets = oldest_sets(LIMIT_SETS)

    print(f"검증 대상 (오래된순 {LIMIT_SETS}개, apply={APPLY}):")
    for s in targets:
        print(f"  {s.released_at} {s.code} {s.name_kr}")
    print()

    total_wrong = 0
    total_missing = 0
    total_extra = 0
    total_fixed = 0
    total_deleted = 0
    summary_rows = []

    for s in targets:
        set_row = sb.table("card_sets").select("id").eq("set_code", s.code).execute().data
        if not set_row:
            print(f"[SKIP] {s.code}: DB에 세트 없음")
            continue
        set_id = set_row[0]["id"]
        expected = expected_rr_plus(s.code, s.collectory_id, client)

        db_cards = (
            sb.table("cards")
            .select("id,card_number,rarity,name_kr,image_url,rarity_rank")
            .eq("set_id", set_id)
            .execute()
            .data
            or []
        )
        db_rr = [c for c in db_cards if (c.get("rarity") or "") in RR_PLUS]

        expected_by_num: dict[str, set[str]] = defaultdict(set)
        for num, rar in expected:
            expected_by_num[num].add(rar)

        db_by_key = {(c.get("card_number") or "", c.get("rarity") or ""): c for c in db_rr}
        db_by_num: dict[str, list] = defaultdict(list)
        for c in db_rr:
            db_by_num[c.get("card_number") or ""].append(c)

        wrong: list[tuple] = []
        missing: list[tuple[str, str]] = []
        extra: list = []

        # wrong rarity: same number exists but different rarity, and expected has another
        for num, cards in db_by_num.items():
            if not num:
                continue
            exp_rars = expected_by_num.get(num, set())
            for c in cards:
                rar = c.get("rarity") or ""
                if rar in exp_rars:
                    continue
                # number not expected at all as RR+ → extra
                if not exp_rars:
                    extra.append(c)
                    continue
                # pick best expected rarity if only one, else leave as wrong
                if len(exp_rars) == 1:
                    wrong.append((c, next(iter(exp_rars))))
                else:
                    # if current not in expected, try match by preferred collectory
                    wrong.append((c, sorted(exp_rars)[0]))

        for key in expected:
            if key not in db_by_key:
                # maybe wrong rarity already counted
                num, rar = key
                if any(c.get("card_number") == num for c in db_rr):
                    continue
                missing.append(key)

        for key, c in db_by_key.items():
            if key not in expected and c not in extra and not any(c is w[0] for w in wrong):
                extra.append(c)

        # report
        print(f"=== {s.code} {s.name_kr} ===")
        print(f"  expected RR+: {len(expected)} | DB RR+: {len(db_rr)}")
        if wrong:
            print(f"  WRONG rarity ({len(wrong)}):")
            for c, exp in wrong[:15]:
                print(f"    id={c['id']} {c.get('card_number')} {c.get('name_kr')} DB={c.get('rarity')} → {exp}")
            if len(wrong) > 15:
                print(f"    ... +{len(wrong)-15}")
        if missing:
            print(f"  MISSING ({len(missing)}):")
            for num, rar in missing[:15]:
                card = expected[(num, rar)]
                name = card.get("name_ko") or card.get("name_kr") or card.get("name_en") or ""
                print(f"    {num} {rar} {name}")
            if len(missing) > 15:
                print(f"    ... +{len(missing)-15}")
        if extra:
            print(f"  EXTRA ({len(extra)}):")
            for c in extra[:15]:
                print(f"    id={c['id']} {c.get('card_number')} {c.get('rarity')} {c.get('name_kr')}")
            if len(extra) > 15:
                print(f"    ... +{len(extra)-15}")
        if not wrong and not missing and not extra:
            print("  OK")

        dist = Counter(c.get("rarity") for c in db_rr)
        print(f"  DB dist: {dict(dist)}")
        print()

        total_wrong += len(wrong)
        total_missing += len(missing)
        total_extra += len(extra)
        summary_rows.append((s.code, s.name_kr, len(expected), len(db_rr), len(wrong), len(missing), len(extra)))

        if not APPLY:
            continue

        for c, exp in wrong:
            rank = rank_for_rarity(exp)
            sb.table("cards").update({"rarity": exp, "rarity_rank": rank}).eq("id", c["id"]).execute()
            total_fixed += 1

        for c in extra:
            delete_card(sb, c["id"])
            total_deleted += 1

        # insert missing from collectory
        for num, rar in missing:
            card = expected[(num, rar)]
            image_url = (card.get("cdn_image_url") or card.get("image_url") or "").strip()
            name_kr = (card.get("name_ko") or card.get("name_kr") or "").strip()
            name_en = (card.get("name_en") or card.get("name") or "").strip()
            name_jp = (card.get("name_ja") or "").strip()
            row = {
                "set_id": set_id,
                "card_number": num,
                "rarity": rar,
                "rarity_rank": rank_for_rarity(rar),
                "name_kr": name_kr or name_en,
                "name_en": name_en,
                "name_jp": name_jp,
                "image_url": image_url,
            }
            sb.table("cards").insert(row).execute()
            total_fixed += 1

    print("=" * 60)
    print(f"{'code':8} {'name':16} exp  db  wrong miss extra")
    for code, name, exp, dbn, w, m, e in summary_rows:
        flag = "OK" if w == m == e == 0 else "!!"
        print(f"{flag} {code:8} {name[:16]:16} {exp:3} {dbn:3} {w:5} {m:4} {e:5}")
    print()
    print(f"합계 wrong={total_wrong} missing={total_missing} extra={total_extra}")
    if APPLY:
        print(f"적용 fixed/inserted={total_fixed} deleted={total_deleted}")
    else:
        print("드라이런 — 수정하려면: python verify_oldest20_rr.py --apply")


if __name__ == "__main__":
    main()
