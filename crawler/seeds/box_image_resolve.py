"""pokemoncard 페이지 HTML에서 박스 이미지 추출 (placeholder 제외)"""
from __future__ import annotations

import re

import httpx

from verify_batch1_kr import scrape_page

PLACEHOLDER = "2016-06-20_00-44-39-61799-1466351079"
IMG_RE = re.compile(
    r"(https?://(?:data1\.)?pokemonkorea\.co\.kr/20\d{2}/[^\"'\s>]+\.(?:png|jpg|PNG|JPG|jpeg))"
)
COLLECTORY_SET_RE = re.compile(
    r"(https://cdn\.collectory\.cc/sets/[a-f0-9-]+\.(?:png|webp))"
)


def pick_box_from_html(html: str) -> str:
    imgs = [
        u for u in IMG_RE.findall(html)
        if PLACEHOLDER not in u and "/card/" not in u.lower()
    ]
    imgs.sort(reverse=True)
    if imgs:
        return imgs[0]
    # 구간 페이지에 박스 URL 없음 — collectory sets URL은 최후 수단
    c = COLLECTORY_SET_RE.findall(html)
    return c[0] if c else ""


def fetch_collectory_box(collectory_id: str) -> str:
    if not collectory_id:
        return ""
    import httpx

    r = httpx.get("https://collectory.cc/api/sets", timeout=60)
    for s in r.json().get("sets") or []:
        if s.get("id") == collectory_id:
            url = s.get("image_url") or ""
            if url and "cdn.collectory.cc/sets/" in url:
                return url
    return ""


def resolve_box_image(page: int, collectory_id: str = "") -> str:
    client = httpx.Client(timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r = client.get(f"https://pokemoncard.co.kr/card/{page}", timeout=15)
    r.encoding = "utf-8"
    box = pick_box_from_html(r.text)
    if box and "pokemonkorea" in box:
        return box
    # collectory set image (박스 형태) — pokemonkorea 없을 때
    col = fetch_collectory_box(collectory_id)
    return col
