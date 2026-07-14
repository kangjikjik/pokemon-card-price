"""featured 100팩 — 흰 배경·깨진 이미지·세트 불일치 전수 감사"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import httpx
from PIL import Image

from kr_sets import KR_SETS

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).parent / "_audit_out"
OUT.mkdir(exist_ok=True)
PUBLIC = Path(__file__).resolve().parents[2] / "web" / "public"
AUDIT_IMG = Path(__file__).parent / "_img_audit"
AUDIT_IMG.mkdir(exist_ok=True)
client = httpx.Client(timeout=25, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})


def corner_whiteness(data: bytes) -> float:
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return -1.0
    w, h = im.size
    pts = []
    for x in range(0, min(30, w)):
        for y in range(0, min(30, h)):
            pts.append(im.getpixel((x, y)))
        for y in range(max(0, h - 30), h):
            pts.append(im.getpixel((x, y)))
    for x in range(max(0, w - 30), w):
        for y in range(0, min(30, h)):
            pts.append(im.getpixel((x, y)))
        for y in range(max(0, h - 30), h):
            pts.append(im.getpixel((x, y)))
    if not pts:
        return -1.0
    white = sum(1 for r, g, b in pts if r >= 235 and g >= 235 and b >= 235)
    return white / len(pts)


def load_bytes(url: str) -> tuple[bytes, str]:
    if url.startswith("/"):
        path = PUBLIC / url.lstrip("/")
        if not path.exists():
            return b"", "missing"
        return path.read_bytes(), "local"
    r = client.get(url)
    if r.status_code >= 400:
        return b"", f"http{r.status_code}"
    return r.content, "remote"


results = []
for s in KR_SETS:
    url = s.box_image_kr or ""
    data, kind = load_bytes(url) if url else (b"", "empty")
    wh = corner_whiteness(data) if data else -1.0
    tiny = len(data) < 8000 if data else True
    issues = []
    if kind in ("empty", "missing") or kind.startswith("http"):
        issues.append(kind)
    if tiny and data is not None:
        issues.append("tiny")
    if wh >= 0.25:
        issues.append("white_bg")
    elif wh >= 0.10:
        issues.append("soft_white")
    # save suspects for visual review
    if issues and data:
        ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
        (AUDIT_IMG / f"full_{s.code}{ext}").write_bytes(data)
    row = {
        "code": s.code,
        "name": s.name_kr,
        "url": url,
        "kind": kind,
        "bytes": len(data),
        "whiteness": round(wh, 3),
        "issues": issues,
    }
    results.append(row)
    flag = ",".join(issues) if issues else "OK"
    print(f"{s.code:6} wh={wh:5.2f} {kind:8} {flag:20} {s.name_kr}")

suspects = [r for r in results if r["issues"]]
print(f"\nOK={sum(1 for r in results if not r['issues'])} suspects={len(suspects)}")
(OUT / "pack_audit.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "pack_suspects.json").write_text(json.dumps(suspects, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {OUT / 'pack_suspects.json'}")
for r in sorted(suspects, key=lambda x: -x["whiteness"]):
    print(f"  {r['code']:6} wh={r['whiteness']:.2f} {r['issues']} {r['name']}")
