"""번개장터 카드 매물 사진과 공식 카드 이미지 비교."""
from __future__ import annotations

import io

import httpx
from PIL import Image, ImageOps

OFFICIAL_CARD_IMAGE_HOST = "cards.image.pokemonkorea.co.kr"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

COMPARE_SIZE = 64
# 사진 촬영 각도·배경·보호용품 차이를 감안해 명백한 오매칭만 차단한다.
MIN_CARD_SIMILARITY = 0.25


def bunjang_listing_image_url(item: dict) -> str:
    url = str(item.get("product_image") or item.get("image") or "").strip()
    return url.replace("{res}", "720").replace("{RES}", "720")


def _fingerprint(image: Image.Image) -> tuple[float, ...]:
    fitted = ImageOps.fit(
        image.convert("RGB"),
        (COMPARE_SIZE, COMPARE_SIZE),
        method=Image.Resampling.BILINEAR,
        centering=(0.5, 0.5),
    )
    return tuple(value / 255.0 for rgb in fitted.getdata() for value in rgb)


def _similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    difference = sum(abs(a - b) for a, b in zip(left, right)) / len(left)
    return 1.0 - difference


class CardImageVerifier:
    """공식 이미지와 매물 사진을 보수적으로 비교한다."""

    def __init__(self, official_image_url: str = ""):
        self._official_image_url = (official_image_url or "").strip()
        self._client = httpx.Client(timeout=15, follow_redirects=True, headers=HEADERS)
        self._reference: Image.Image | None = None
        self._loaded = False
        self._cache: dict[str, bool] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CardImageVerifier":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _load_reference(self) -> Image.Image | None:
        if self._loaded:
            return self._reference
        self._loaded = True
        if not self._official_image_url.startswith("http"):
            return None
        try:
            url = self._official_image_url
            if OFFICIAL_CARD_IMAGE_HOST in url and "w=" not in url:
                url = f"{url}&w=512" if "?" in url else f"{url}?w=512"
            response = self._client.get(url)
            if response.status_code >= 400 or len(response.content) < 200:
                return None
            self._reference = Image.open(io.BytesIO(response.content)).convert("RGB")
        except Exception:
            self._reference = None
        return self._reference

    def matches(self, item: dict) -> bool:
        url = bunjang_listing_image_url(item)
        cache_key = str(item.get("pid") or url)
        if cache_key in self._cache:
            return self._cache[cache_key]

        reference = self._load_reference()
        # 이미지가 없거나 다운로드할 수 없으면 기존 제목·등급 검증 결과를 유지한다.
        matched = True
        if reference is not None and url.startswith("http"):
            try:
                response = self._client.get(url)
                if response.status_code < 400 and len(response.content) >= 200:
                    listing = Image.open(io.BytesIO(response.content)).convert("RGB")
                    width, height = listing.size
                    if min(width, height) >= 80 and 0.35 <= width / height <= 2.8:
                        matched = (
                            _similarity(_fingerprint(reference), _fingerprint(listing))
                            >= MIN_CARD_SIMILARITY
                        )
            except Exception:
                matched = True

        self._cache[cache_key] = matched
        return matched
