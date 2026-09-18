"""트레이너·아이템 카드 식별 (SNKRDUNK 제외·한국 공식명 검색용)."""

from __future__ import annotations



import re



# MG6 시크릿 SR/SAR 중 포켓몬 ex 제외 (102–111, 116–117)

MG6_TRAINER_ITEM_NUMBERS: frozenset[int] = frozenset(

    list(range(102, 112)) + [116, 117]

)



# Collectory JP 세트 영문명 매핑 (name_jp → English) — MG6 레거시

MG6_NAME_JP_TO_EN: dict[str, str] = {

    "アイアンディフェンダー": "Iron Defender",

    "エネルギーつけかえ": "Energy Switch",

    "クラッシュハンマー": "Crushing Hammer",

    "ダークベル": "Dark Bell",

    "ごうかいボム": "Heroic Bomb",

    "ブレイブバングル": "Brave Bangle",

    "カスミの元気": "Misty's Energy",

    "グラジオの決戦": "Gladion's Fighting Spirit",

    "サビ組のしたっぱ": "Rust Syndicate Grunts",

    "ムク": "Gwynn",

}



MEGA_SET_CODES = frozenset({"MG4", "MG4A", "MG5", "MG5A", "MG6", "MG7"})





def card_number_int(card_number: str) -> int | None:

    if not card_number or "/" not in card_number:

        return None

    try:

        return int(card_number.split("/")[0])

    except ValueError:

        return None





def is_mg6_trainer_or_item(card_number: str) -> bool:

    n = card_number_int(card_number)

    return n is not None and n in MG6_TRAINER_ITEM_NUMBERS





def is_trainer_or_item_card(

    set_code: str,

    card_number: str,

    name_jp: str = "",

) -> bool:

    code = (set_code or "").upper()

    if code == "MG6" and is_mg6_trainer_or_item(card_number):

        return True

    if code in MEGA_SET_CODES:
        try:
            from lib.collectory_kr_sync import is_trainer_by_collectory  # noqa: PLC0415

            if is_trainer_by_collectory(code, card_number, name_jp):
                return True
        except Exception:
            pass

    return False





def skip_card_number_in_title(set_code: str, card_number: str, name_jp: str = "") -> bool:

    """DB 일본 팩번호 ≠ 번개 제목 한국 팩번호 — 트레이너·아이템은 번호 매칭 생략."""

    return is_trainer_or_item_card(set_code, card_number, name_jp)

