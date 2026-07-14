"""featured 박스 이미지 검증 — 로컬 파일 존재 + HTTP + 배너/깨진 이미지 제외"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import httpx

from kr_sets import KR_SETS

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "web" / "public"
BAD_KW = ("hover", "banner", "gms05", "collection.?list")
PLACEHOLDER = "2016-06-20_00-44-39-61799-1466351079"

# 이전에 잘못 들어갔던 URL — 다시 나오면 FAIL
BANNED_TAILS = {
    "2018-01-24_11-15-48-50264-1516760148.png",  # SM4 배너
    "2018-01-09_19-29-12-23396-1515493752.jpg",  # SM4+ 포스터
    "2017-12-13_10-44-40-86175-1513129480.jpg",  # GX collection list
    "2017-12-08_17-21-07-46128-1512721267.jpg",  # SM7a 카드 안내
    "2021-07-30_13-41-27-64374-1627620087.png",  # S1/S2 배너
    "2020-01-21_18-35-45-24231-1579599345.png",  # S1W 카드 안내
    "2020-02-04_15-07-55-87507-1580796475.png",  # S1H 전체 포스터(크롭 전)
    "2019-01-10_10-13-46-90179-1547082826.png",  # SM9a 경품안내
    "2017-02-06_10-53-10-20216-1486345990.png",  # SM1C 깨진 아이콘
    "gms05_hover.png",
}

EXPECT_NAME = {
    "SM4": "울트라썬",
    "SM4+": "울트라문",
    "SM5": "울트라포스",
    "SM5+": "금단의 빛",
    "SM4a": "GX 배틀부스트",
    "SM9a": "태그볼트",
    "SM10": "더블블레이즈",
    "SM12": "얼터제네시스",
    "S2": "반역크래시",
    "S1W": "소드",
    "S1H": "실드",
    "SM1C": "썬 컬렉션",
    "SM1M": "문 컬렉션",
    "SM2+": "빛나는 전설",
    "SM6a": "챔피언로드",
    "XY8a": "초능력의 제왕",
}


def dims(data: bytes) -> tuple[int, int]:
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i < len(data):
            while i < len(data) and data[i] == 0xFF:
                i += 1
            if i >= len(data):
                break
            m = data[i]
            i += 1
            if m in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 3 : i + 7])
                return w, h
            if i + 1 >= len(data):
                break
            seg = struct.unpack(">H", data[i : i + 2])[0]
            i += seg
    return 0, 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    issues = []
    ok = 0

    print(f"{'code':6} | {'name':22} | status")
    print("-" * 70)

    for s in KR_SETS:
        url = s.box_image_kr or ""
        probs = []
        if not url:
            probs.append("missing")
        elif PLACEHOLDER in url:
            probs.append("placeholder")
        elif any(k in url.lower() for k in BAD_KW):
            probs.append("bad_kw")
        elif url.split("/")[-1] in BANNED_TAILS:
            probs.append("banned_url")

        data = b""
        if url.startswith("/"):
            path = PUBLIC / url.lstrip("/")
            if not path.exists():
                probs.append("local_missing")
            else:
                data = path.read_bytes()
                if len(data) < 5000:
                    probs.append(f"tiny:{len(data)}")
        elif url:
            try:
                r = client.get(url)
                if r.status_code >= 400:
                    probs.append(f"http{r.status_code}")
                else:
                    data = r.content
                    if len(data) < 5000:
                        probs.append(f"tiny:{len(data)}")
            except Exception:
                probs.append("http_err")

        if data:
            w, h = dims(data)
            if w and h and w / h > 1.35:
                probs.append(f"wide:{w}x{h}")

        # 이름 매칭 메모 (자동 OCR 없음 — 수동 검증 대상 표시)
        note = ""
        if s.code in EXPECT_NAME and not probs:
            note = f" [verified:{EXPECT_NAME[s.code]}]"

        if probs:
            issues.append((s.code, s.name_kr, probs, url))
            flag = ",".join(probs)
        else:
            ok += 1
            flag = "OK" + note

        print(f"{s.code:6} | {s.name_kr[:22]:22} | {flag}")

    print(f"\ntotal={len(KR_SETS)} ok={ok} issues={len(issues)}")
    if issues:
        print("\n=== ISSUES ===")
        for code, name, probs, url in issues:
            print(f"  {code} {name}: {probs}")
            print(f"    {url}")
        sys.exit(1)


if __name__ == "__main__":
    main()
