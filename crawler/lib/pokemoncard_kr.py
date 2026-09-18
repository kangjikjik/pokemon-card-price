"""pokemoncard.co.kr 카드검색 — 트레이너·아이템 공식 한글명·이미지."""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

import httpx

BASE = "https://pokemoncard.co.kr"
AJAX = f"{BASE}/v2/ajax2_dev2"
IMG_BASE = "https://cards.image.pokemonkorea.co.kr/data"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE}/cards",
    "Origin": BASE,
    "X-Requested-With": "XMLHttpRequest",
}
TRAINER_CARD_TYPES = "아이템,포켓몬의 도구,서포,스타디움"
TRAINER_KINDS = ("아이템", "포켓몬의 도구", "서포트", "스타디움", "ACE SPEC")
SKIP_SET_CODES = frozenset({"MG7"})  # 스톰에메랄다 — 공식 카드 사진 미완
CACHE_PATH = Path(__file__).resolve().parents[1] / "_audit_out" / "official_trainers_cache.json"

NAME_RE = re.compile(r'<span class="card-hp title">([^<]+)</span>')
KIND_RE = re.compile(r"카드 종류\s*:\s*([^<\n]+)")
PNUM_RE = re.compile(
    r'<span class="p_num">\s*(\d+)\s*/\s*(\d+)\s*<span[^>]*>\s*([^<]*?)\s*</span>',
    re.I,
)
IMG_RE = re.compile(
    r'<img src="(https://cards\.image\.pokemonkorea\.co\.kr/data/wmimages/[^"?]+)'
)
OPTION_RE = re.compile(r'<option value="([^"]+)"')
QUOTED_RE = re.compile(r"「([^」]+)」")
IMG_NUM_RE = re.compile(r"_(\d{2,4})\.(?:png|jpg|webp)$", re.I)


def _space_norm(s: str) -> str:
    return re.sub(r"[\s·・\.]", "", (s or "").strip()).casefold()


@dataclass(frozen=True)
class OfficialTrainer:
    card_id: str
    name_kr: str
    kind: str
    number: int
    printed: str
    rarity: str
    image_url: str
    goods_name: str


def _client() -> httpx.Client:
    c = httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True)
    c.get(f"{BASE}/cards")
    return c


@lru_cache(maxsize=1)
def goods_options() -> tuple[str, ...]:
    r = httpx.get(f"{BASE}/cards", headers=HEADERS, timeout=30, follow_redirects=True)
    r.raise_for_status()
    r.encoding = "utf-8"
    opts = []
    seen: set[str] = set()
    for m in OPTION_RE.finditer(r.text):
        v = m.group(1).strip()
        if not v or v in seen or v.endswith("전체"):
            continue
        seen.add(v)
        opts.append(v)
    return tuple(opts)


def goods_name_for_set(name_kr: str) -> str | None:
    target = _space_norm(name_kr)
    if not target:
        return None
    quoted_hits: list[str] = []
    contains: list[str] = []
    for opt in goods_options():
        m = QUOTED_RE.search(opt)
        inner = _space_norm(m.group(1) if m else "")
        if inner == target:
            quoted_hits.append(opt)
        elif target and target in _space_norm(opt):
            contains.append(opt)
    pool = quoted_hits or contains
    if not pool:
        return None
    for needle in ("확장팩", "하이클래스팩", "강화 확장팩"):
        pref = [o for o in pool if needle in o and "박스" not in o and "BOX" not in o]
        if len(pref) == 1:
            return pref[0]
        if pref:
            pool = pref
            break
    pack_only = [o for o in pool if "박스" not in o and "BOX" not in o and "덱" not in o]
    if pack_only:
        pool = pack_only
    return sorted(pool, key=len)[0]


def _rows(result) -> list[dict]:
    if not result:
        return []
    if isinstance(result, dict):
        return [v for v in result.values() if isinstance(v, dict)]
    if isinstance(result, list):
        return [v for v in result if isinstance(v, dict)]
    return []


def fetch_trainer_ids(goods_name: str, client: httpx.Client | None = None) -> list[dict]:
    own = client is None
    c = client or _client()
    try:
        seen: set[str] = set()
        out: list[dict] = []
        limit = "0"
        for _ in range(30):
            r = c.post(
                AJAX,
                data={
                    "action": "get_more_cards",
                    "limit": limit,
                    "GoodsName": goods_name,
                    "CardTypeNum": "2",
                    "CardType": TRAINER_CARD_TYPES,
                    "order": "ASC",
                    "orderby": "CardNum",
                },
            )
            r.raise_for_status()
            obj = r.json()
            rows = _rows(obj.get("result"))
            fresh = []
            for row in rows:
                cid = str(row.get("CardNum") or "").strip()
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                fresh.append(row)
            if not fresh:
                break
            out.extend(fresh)
            nxt = obj.get("limit")
            limit = str(nxt if nxt is not None else int(limit) + 1)
            if len(fresh) < 10:
                break
            time.sleep(0.12)
        return out
    finally:
        if own:
            c.close()


def parse_detail(html: str) -> dict | None:
    name_m = NAME_RE.search(html)
    kind_m = KIND_RE.search(html)
    p_m = PNUM_RE.search(html)
    img_m = IMG_RE.search(html)
    if not name_m or not kind_m or not p_m or not img_m:
        return None
    name = name_m.group(1).strip()
    kind = kind_m.group(1).strip()
    num = int(p_m.group(1))
    printed = f"{int(p_m.group(1)):03d}/{int(p_m.group(2)):03d}"
    rarity = (p_m.group(3) or "").strip().upper()
    image = img_m.group(1).split("?")[0]
    return {
        "name_kr": name,
        "kind": kind,
        "number": num,
        "printed": printed,
        "rarity": rarity,
        "image_url": image,
    }


def is_trainer_kind(kind: str) -> bool:
    k = kind or ""
    if "에너지" in k:
        return False
    if any(t in k for t in TRAINER_KINDS):
        return True
    if "포켓몬" in k and "도구" not in k:
        return False
    return False


def image_number_ok(image_url: str, number: int) -> bool:
    m = IMG_NUM_RE.search(image_url.split("?")[0])
    if not m:
        return True
    return int(m.group(1)) == number


def fetch_detail(card_id: str, client: httpx.Client) -> dict | None:
    r = client.get(f"{BASE}/cards/detail/{card_id}")
    if r.status_code != 200:
        return None
    r.encoding = "utf-8"
    return parse_detail(r.text)


def fetch_set_trainers(goods_name: str, *, use_cache: bool = True) -> list[OfficialTrainer]:
    if use_cache and CACHE_PATH.exists():
        try:
            blob = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            rows = blob.get(goods_name)
            if rows:
                return [OfficialTrainer(**r) for r in rows]
        except Exception:
            pass
    c = _client()
    try:
        rows = fetch_trainer_ids(goods_name, c)
        out: list[OfficialTrainer] = []
        for row in rows:
            cid = str(row.get("CardNum") or "").strip()
            feat = (row.get("feature_image") or "").split("?")[0].lstrip("/")
            detail = fetch_detail(cid, c)
            time.sleep(0.08)
            if not detail:
                continue
            if not is_trainer_kind(detail["kind"]):
                continue
            img = detail["image_url"]
            if feat.startswith("wmimages/"):
                img = f"{IMG_BASE}/{feat}".split("?")[0]
            if not image_number_ok(img, detail["number"]):
                continue
            out.append(
                OfficialTrainer(
                    card_id=cid,
                    name_kr=detail["name_kr"],
                    kind=detail["kind"],
                    number=detail["number"],
                    printed=detail["printed"],
                    rarity=detail["rarity"],
                    image_url=img,
                    goods_name=goods_name,
                )
            )
        if out:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            blob: dict = {}
            if CACHE_PATH.exists():
                try:
                    blob = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
                except Exception:
                    blob = {}
            blob[goods_name] = [asdict(x) for x in out]
            CACHE_PATH.write_text(json.dumps(blob, ensure_ascii=False), encoding="utf-8")
        return out
    finally:
        c.close()
