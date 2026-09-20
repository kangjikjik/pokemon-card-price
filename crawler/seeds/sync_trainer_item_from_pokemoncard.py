"""스톰에메랄다 제외 — 트레이너·아이템 name_kr/image_url 을 pokemoncard.co.kr 공식값으로 동기화.

  python -m seeds.sync_trainer_item_from_pokemoncard
  python -m seeds.sync_trainer_item_from_pokemoncard --set MG6
  python -m seeds.sync_trainer_item_from_pokemoncard --apply
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from kr_sets import KR_SETS
from lib.pokemoncard_kr import (
    SKIP_SET_CODES,
    fetch_set_trainers,
    goods_name_for_set,
)
from lib.trainer_item_cards import card_number_int
from utils.db import get_supabase

APPLY = "--apply" in sys.argv


def _arg_set() -> str | None:
    if "--set" not in sys.argv:
        return None
    i = sys.argv.index("--set")
    return sys.argv[i + 1] if i + 1 < len(sys.argv) else None


def _norm_rarity(r: str) -> str:
    return (r or "").strip().upper().replace(" ", "")


def _rarity_group(r: str) -> str:
    r = _norm_rarity(r)
    if r in {"SR", "SAR", "UR", "HR", "CSR", "CHR", "SSR", "MUR"}:
        return "secret"
    if r in {"ACE"}:
        return "ace"
    if r in {"AR", "RR", "K"}:
        return "art"
    return "low"


def _rarity_ok(db_rarity: str, off_rarity: str) -> bool:
    og = _rarity_group(off_rarity)
    dg = _rarity_group(db_rarity)
    if og != dg:
        return False
    o = _norm_rarity(off_rarity)
    d = _norm_rarity(db_rarity)
    if o and d and o != d:
        return False
    return True


def _img_key(url: str) -> str:
    return (url or "").split("?")[0].strip()


def load_cards(sb, set_id: str) -> list[dict]:
    rows: list[dict] = []
    start = 0
    page = 1000
    while True:
        batch = (
            sb.table("cards")
            .select("id,card_number,name_kr,name_jp,rarity,image_url")
            .eq("set_id", set_id)
            .range(start, start + page - 1)
            .execute()
            .data
            or []
        )
        rows.extend(batch)
        if len(batch) < page:
            break
        start += page
    return rows


def _name_key(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def _has_kana(s: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff]", s or ""))


def pick_db_card(
    cards: list[dict],
    off_name: str,
    off_number: int,
    rarity: str,
    used_ids: set[str],
) -> tuple[dict | None, str]:
    want = _norm_rarity(rarity)
    key = _name_key(off_name)
    unused = [c for c in cards if c["id"] not in used_ids]
    name_hits = [
        c
        for c in unused
        if _name_key(c.get("name_kr") or "") == key
        and _rarity_ok(c.get("rarity") or "", rarity)
    ]
    if len(name_hits) == 1:
        return name_hits[0], "이름+등급"
    if len(name_hits) > 1:
        return None, "이름중복"

    same_num = [
        c
        for c in unused
        if card_number_int(c.get("card_number") or "") == off_number
        and _rarity_ok(c.get("rarity") or "", rarity)
    ]
    if len(same_num) != 1:
        return None, "DB없음"
    db = same_num[0]
    old = (db.get("name_kr") or "").strip()
    if old and not _has_kana(old) and _name_key(old) != key:
        return None, "번호불일치"
    return db, "번호+등급"


def main() -> None:
    only = (_arg_set() or "").strip()
    targets = []
    for s in KR_SETS:
        if s.code.upper() in SKIP_SET_CODES:
            continue
        if only and s.code.upper() != only.upper():
            continue
        targets.append(s)
    if not targets:
        print("대상 세트 없음")
        return

    sb = get_supabase()
    set_rows = sb.table("card_sets").select("id,set_code").execute().data or []
    id_by_code = {r["set_code"]: r["id"] for r in set_rows}

    total_upd = 0
    problems: list[str] = []
    changes: list[dict] = []

    for s in targets:
        goods = goods_name_for_set(s.name_kr)
        print(f"\n[{s.name_kr}] goods={goods!r}")
        if not goods:
            problems.append(f"{s.name_kr}: 공식 제품명 매칭 없음")
            continue
        set_id = id_by_code.get(s.code)
        if not set_id:
            problems.append(f"{s.name_kr}: DB 세트 없음")
            continue

        officials = fetch_set_trainers(goods)
        print(f"  공식 트레이너/아이템 {len(officials)}장")
        if not officials:
            problems.append(f"{s.name_kr}: 공식 트레이너 0장")
            continue

        db_cards = load_cards(sb, set_id)
        used_ids: set[str] = set()
        n = 0
        matched = 0
        missing = 0
        for off in officials:
            db, how = pick_db_card(
                db_cards, off.name_kr, off.number, off.rarity, used_ids
            )
            if db is None:
                if how == "DB없음":
                    missing += 1
                    continue
                problems.append(
                    f"{s.name_kr} {off.printed} {off.rarity} {off.name_kr}: {how}"
                )
                continue
            used_ids.add(db["id"])
            matched += 1

            old_name = (db.get("name_kr") or "").strip()
            old_img = _img_key(db.get("image_url") or "")
            payload: dict = {}
            if old_name != off.name_kr:
                payload["name_kr"] = off.name_kr
            if old_img != off.image_url:
                payload["image_url"] = off.image_url
            if not payload:
                continue

            print(
                f"  [{db.get('card_number')} {off.rarity} {off.kind}] {how} "
                f"{old_name!r} → {off.name_kr!r} (공식 {off.printed})"
            )
            if "image_url" in payload:
                print(f"    img → {off.image_url}")
            if APPLY:
                sb.table("cards").update(payload).eq("id", db["id"]).execute()
            n += 1
            changes.append(
                {
                    "set": s.name_kr,
                    "db_number": db.get("card_number"),
                    "db_rarity": db.get("rarity"),
                    "off_printed": off.printed,
                    "off_rarity": off.rarity,
                    "how": how,
                    "old_name": old_name,
                    "new_name": off.name_kr,
                    "old_img": old_img,
                    "new_img": off.image_url,
                    "kind": off.kind,
                }
            )
        print(f"  매칭 {matched}/{len(officials)} 미수록 {missing} 변경 {n}장")
        total_upd += n

    print(f"\n{'적용' if APPLY else '드라이런'} 합계 변경: {total_upd}장")
    outp = os.path.join(os.path.dirname(__file__), "..", "_audit_out", "trainer_sync_result.json")
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    import json

    with open(outp, "w", encoding="utf-8") as f:
        json.dump(
            {"apply": APPLY, "changes": total_upd, "problems": problems, "rows": changes},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"결과 {outp}")
    if problems:
        print(f"문제 {len(problems)}건:")
        for line in problems[:80]:
            print(" ", line)
        if len(problems) > 80:
            print(f"  … 외 {len(problems) - 80}건")


if __name__ == "__main__":
    main()
