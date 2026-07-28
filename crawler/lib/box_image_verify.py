"""번개장터 박스 매물 이미지 ↔ 세트 기준 박스 이미지 검증."""
from __future__ import annotations

import io
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
SET_BOX_DIR = ROOT / "web" / "public" / "set-boxes"

COMPARE_SIZE = 64
# 팩/박스 기준图 모두 일러스트 중앙이 같아 전체 비교보다 crop 비교가 낫다
ARTWORK_CROP_RATIO = 0.55
MIN_ART_SIMILARITY = 0.60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def bunjang_listing_image_url(item: dict) -> str:
    u = str(item.get("product_image") or item.get("image") or "")
    return u.replace("{res}", "360").replace("{RES}", "360")


def _center_crop(img: Image.Image, ratio: float = ARTWORK_CROP_RATIO) -> Image.Image:
    w, h = img.size
    cw, ch = max(1, int(w * ratio)), max(1, int(h * ratio))
    left = (w - cw) // 2
    top = (h - ch) // 2
    return img.crop((left, top, left + cw, top + ch))


def _fingerprint(img: Image.Image, size: int = COMPARE_SIZE) -> tuple[float, ...]:
    img = img.convert("RGB").resize((size, size), Image.Resampling.BILINEAR)
    return tuple(p / 255.0 for rgb in img.getdata() for p in rgb)


def _similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    diff = sum(abs(x - y) for x, y in zip(a, b)) / len(a)
    return 1.0 - diff


def _artwork_similarity(ref: Image.Image, listing: Image.Image) -> float:
    a = _center_crop(ref)
    b = _center_crop(listing)
    return _similarity(_fingerprint(a), _fingerprint(b))


def _is_acceptable_listing_photo(img: Image.Image) -> bool:
    w, h = img.size
    if w < 80 or h < 80:
        return False
    ratio = w / h
    if ratio < 0.45 or ratio > 2.2:
        return False
    gray = img.convert("L").resize((32, 32))
    pixels = list(gray.getdata())
    mean = sum(pixels) / len(pixels)
    if mean < 12 or mean > 248:
        return False
    return True


class BoxImageVerifier:
    """세트 기준 이미지와 번개 매물 사진의 일러스트 유사도 + 기본 품질 검증."""

    def __init__(self, set_code: str, box_image_url: str = ""):
        self.set_code = set_code.upper()
        self._box_image_url = (box_image_url or "").strip()
        self._client = httpx.Client(timeout=15, follow_redirects=True, headers=HEADERS)
        self._ref_img: Image.Image | None = None
        self._ref_loaded = False
        self._listing_cache: dict[str, bool] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BoxImageVerifier:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def has_reference(self) -> bool:
        return self._load_reference() is not None

    def _load_reference(self) -> Image.Image | None:
        if self._ref_loaded:
            return self._ref_img
        self._ref_loaded = True

        local = SET_BOX_DIR / f"{self.set_code}.png"
        data = b""
        if local.exists():
            data = local.read_bytes()
        elif self._box_image_url.startswith("/"):
            path = ROOT / "web" / "public" / self._box_image_url.lstrip("/")
            if path.exists():
                data = path.read_bytes()
        elif self._box_image_url.startswith("http"):
            try:
                r = self._client.get(self._box_image_url)
                if r.status_code < 400 and len(r.content) > 500:
                    data = r.content
            except Exception:
                pass

        if not data:
            return None
        try:
            self._ref_img = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            self._ref_img = None
        return self._ref_img

    def matches(self, item: dict) -> bool:
        url = bunjang_listing_image_url(item)
        pid = str(item.get("pid") or url or "")
        if pid and pid in self._listing_cache:
            return self._listing_cache[pid]

        ref = self._load_reference()
        if ref is None:
            ok = False
        elif not url.startswith("http"):
            ok = False
        else:
            try:
                r = self._client.get(url)
                if r.status_code >= 400 or len(r.content) < 200:
                    ok = False
                else:
                    listing = Image.open(io.BytesIO(r.content)).convert("RGB")
                    if not _is_acceptable_listing_photo(listing):
                        ok = False
                    else:
                        sim = _artwork_similarity(ref, listing)
                        ok = sim >= MIN_ART_SIMILARITY
            except Exception:
                ok = False

        if pid:
            self._listing_cache[pid] = ok
        return ok
