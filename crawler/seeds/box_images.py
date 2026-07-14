"""확장팩 박스/팩 이미지 — 한국 공식 박스만 (kr_sets.py)"""

from kr_sets import KR_BOX_IMAGES

SET_BOX_IMAGES: dict[str, str] = dict(KR_BOX_IMAGES)

LOGO_PATTERNS = ("/cards/sets/", "pokemontcg.io", "/set-logo", "set-logo2.webp", "pokemon-card.com")
CARD_PATTERNS = ("cdn.collectory.cc/cards/", "/cards/kr/", "/cards/jp/", "/cards/us/")


def is_bad_url(url: str) -> bool:
    u = (url or "").lower()
    return any(p in u for p in LOGO_PATTERNS + CARD_PATTERNS)


def pick_box_image(set_code: str, meta_url: str | None, cards: list[dict] | None = None) -> str:
    preset = SET_BOX_IMAGES.get(set_code)
    if preset:
        return preset
    if meta_url and not is_bad_url(meta_url):
        if "pokemonkorea.co.kr" in meta_url or (
            "cdn.collectory.cc/sets/" in meta_url and "cards/" not in meta_url
        ):
            return meta_url
    return ""
