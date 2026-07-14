"""Fetch yuyutei front images for S7F UR 126-128."""
from __future__ import annotations

import re
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")

# yuyutei card page id pattern: s08/10{card_num}
PAGES = [
    ("126/100", "126", "파워태블릿"),
    ("127/100", "127", "트레이닝 코트"),
    ("128/100", "128", "기본 풀 에너지"),
]

client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})


def extract_images(html: str) -> list[str]:
    imgs = re.findall(r"(https://img\.yuyu-tei\.jp/[^\"'\s>]+\.(?:jpg|webp|png))", html)
    # prefer front/card images
    out = []
    for u in imgs:
        if "card" in u.lower() or "poc" in u.lower() or "front" in u.lower():
            out.append(u)
    return out or imgs


for num, yid, name in PAGES:
    url = f"https://yuyu-tei.jp/sell/poc/card/s08/10{yid}"
    r = client.get(url)
    print(f"\n=== {num} {name} status={r.status_code} ===")
    if r.status_code != 200:
        continue
    imgs = extract_images(r.text)
    for u in imgs[:5]:
        rr = client.get(u)
        print(f"  img {rr.status_code} {len(rr.content)} {u}")
