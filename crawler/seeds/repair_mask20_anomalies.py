"""달다구리 기준으로 변환의 가면부터 20세트의 감사 이상 항목을 보정."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from seeds.kr_sets import KR_SETS
from utils.db import get_supabase


TARGETS = {
    "SV5K": 26, "SV5M": 27, "SV4x": 278, "SV4": 277, "SV4a": 14,
    "SV4K": 276, "SV4M": 15, "SV3a": 275, "SV3": 366, "SV2a": 17,
    "SV2D": 273, "SV2P": 272, "SV1a": 271, "SV1V": 270, "SV1S": 269,
    "S12a": 18, "S12": 268, "S11a": 267, "S11": 266, "S10b": 265,
}
HIGH = {"RR", "RRR", "BWR", "AR", "CHR", "CSR", "SSR", "SR", "TR",
         "MA", "ACE", "SAR", "PR", "UR", "HR", "MUR", "FUR"}


def number(value: str | None) -> int | None:
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else None


def norm(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip()).casefold()


def medium(url: str | None) -> str:
    return (url or "").replace("_thumb.webp", "_medium.webp")


def collectory_candidates(bs_code: str, card_number: str, rarity: str) -> list[str]:
    match = re.search(r"(\d+)\s*/\s*(\d+)", card_number or "")
    if not match:
        return []
    stem = f"{int(match.group(1)):03d}_{int(match.group(2)):03d}"
    base = bs_code.removesuffix("-kr")
    return [
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}{rarity}.webp",
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}{rarity}.jpg",
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}.webp",
        f"https://cdn.collectory.cc/cards/kr/{base}/{stem}.jpg",
    ]


def image_ok(client: httpx.Client, url: str) -> bool:
    try:
        response = client.get(url)
        return response.status_code == 200 and response.headers.get(
            "content-type", ""
        ).startswith("image/")
    except Exception:
        return False


def delete_card_data(sb, card_id: int) -> None:
    for table in ("prices_kr", "prices_jp"):
        sb.table(table).delete().eq("card_id", card_id).execute()
    sb.table("cards").delete().eq("id", card_id).execute()


def main() -> None:
    sb = get_supabase()
    metas = {
        row["set_code"]: row
        for row in sb.table("card_sets")
        .select("id,set_code,name_kr")
        .in_("set_code", list(TARGETS))
        .execute()
        .data
        or []
    }
    bs_codes = {item.code: item.bs_code for item in KR_SETS}
    report = {"added": [], "updated": [], "deleted": [], "unresolved": []}

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for code, source_set_id in TARGETS.items():
            meta = metas[code]
            source = client.get(
                f"https://api.daldagury.com/tcg/sets/{source_set_id}/cards?limit=400"
            ).json()["resultData"]["data"]
            by_number: dict[int, dict] = {}
            by_name: dict[str, dict] = {}
            for row in source:
                n = number(row.get("numberInSet") or row.get("cardNumber"))
                if n is not None and row.get("thumbnailUrl"):
                    by_number.setdefault(n, row)
                by_name[norm(row.get("nameKo"))] = row

            db_cards = (
                sb.table("cards")
                .select("id,name_kr,card_number,rarity,image_url")
                .eq("set_id", meta["id"])
                .execute()
                .data
                or []
            )

            # Fill missing printed numbers and images from the Korean catalog.
            for card in db_cards:
                source_row = by_number.get(number(card.get("card_number")))
                if source_row is None and not number(card.get("card_number")):
                    source_row = by_name.get(norm(card.get("name_kr")))
                updates: dict[str, str] = {}
                if source_row:
                    if not number(card.get("card_number")):
                        updates["card_number"] = source_row["numberInSet"]
                    if not card.get("image_url"):
                        updates["image_url"] = medium(source_row.get("thumbnailUrl"))
                if not updates and card.get("image_url"):
                    continue
                if not updates and source_row is None:
                    candidates = collectory_candidates(
                        bs_codes[code],
                        card.get("card_number") or "",
                        card.get("rarity") or "",
                    )
                    for candidate in candidates:
                        if image_ok(client, candidate):
                            updates["image_url"] = candidate
                            break
                if updates:
                    sb.table("cards").update(updates).eq("id", card["id"]).execute()
                    report["updated"].append({"set_code": code, "card_id": card["id"], **updates})

            # Add high-rarity cards present in Daldagury but absent from DB.
            db_after = (
                sb.table("cards")
                .select("id,card_number,rarity")
                .eq("set_id", meta["id"])
                .execute()
                .data
                or []
            )
            db_high = {
                number(c.get("card_number"))
                for c in db_after
                if (c.get("rarity") or "").upper() in HIGH
            }
            for source_row in source:
                n = number(source_row.get("numberInSet") or source_row.get("cardNumber"))
                rarity = (source_row.get("lowestRarity") or "").upper()
                if n is None or rarity not in HIGH or n in db_high:
                    continue
                card_number = source_row.get("numberInSet") or source_row.get("cardNumber")
                image_url = medium(source_row.get("thumbnailUrl"))
                if not image_url:
                    image_url = next(
                        (
                            candidate
                            for candidate in collectory_candidates(
                                bs_codes[code],
                                card_number,
                                rarity,
                            )
                            if image_ok(client, candidate)
                        ),
                        "",
                    )
                if not image_url:
                    report["unresolved"].append(
                        {"set_code": code, "card_number": card_number, "name": source_row.get("nameKo")}
                    )
                    continue
                inserted = sb.table("cards").insert(
                    {
                        "set_id": meta["id"],
                        "name_jp": "",
                        "name_kr": source_row.get("nameKo") or "",
                        "name_en": "",
                        "rarity": rarity,
                        "rarity_rank": 4,
                        "image_url": image_url,
                        "card_number": card_number,
                        "image_color": "from-slate-600 via-slate-700 to-slate-800",
                    }
                ).execute().data or []
                report["added"].append(
                    {"set_code": code, "card_number": card_number, "name": source_row.get("nameKo"), "id": inserted[0]["id"]}
                )
                db_high.add(n)

            # Remove rows that conflict with Daldagury on the requested legacy set.
            if code == "S12a":
                rows = sb.table("cards").select("id,card_number").eq("set_id", meta["id"]).eq("card_number", "173/172").execute().data or []
                for row in rows:
                    delete_card_data(sb, row["id"])
                    report["deleted"].append({"set_code": code, **row})
            if code == "S11":
                rows = sb.table("cards").select("id,card_number,rarity").eq("set_id", meta["id"]).eq("rarity", "—").execute().data or []
                for row in rows:
                    delete_card_data(sb, row["id"])
                    report["deleted"].append({"set_code": code, **row})

    Path("_audit_out/mask_20_anomaly_repair.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: len(v) for k, v in report.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
