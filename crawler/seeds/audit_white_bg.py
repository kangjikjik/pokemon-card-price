"""흰 배경 / 잘못된 팩 이미지 감사"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import httpx
from kr_sets import KR_SETS

sys.stdout.reconfigure(encoding="utf-8")
client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
OUT = Path(__file__).parent / "_img_audit"
OUT.mkdir(exist_ok=True)

# 스크린샷에서 문제된 코드들 + S6H
CODES = ["S6H", "S4B", "S3H", "S3Z", "S2R", "S2", "S1a", "S1W", "S1H", "S4SV", "CEL"]


def png_info(data: bytes):
    if not data.startswith(b"\x89PNG"):
        return None
    w, h = struct.unpack(">II", data[16:24])
    # sample corner pixels for white bg
    return w, h


for code in CODES:
    s = next(x for x in KR_SETS if x.code == code)
    url = s.box_image_kr
    print(f"\n{code} {s.name_kr}")
    print(f"  {url}")
    if url.startswith("/"):
        path = Path(__file__).resolve().parents[2] / "web" / "public" / url.lstrip("/")
        data = path.read_bytes() if path.exists() else b""
        print(f"  local {len(data)} bytes")
    else:
        r = client.get(url)
        data = r.content
        print(f"  http {r.status_code} {len(data)} bytes")
    if data:
        ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
        (OUT / f"bg_{code}{ext}").write_bytes(data)
        print(f"  saved bg_{code}{ext}")
