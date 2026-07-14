"""ACE로 저장된 카드 이미지 — ACE SPEC 시각 표기(핑크 테두리/ACE SPEC 문자) 휴리스틱 검사"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
IMG = Path(__file__).parent / "_img_audit" / "ace"
OUT = Path(__file__).parent / "_audit_out"
rows = json.loads((OUT / "ace_db.json").read_text(encoding="utf-8"))


def has_ace_spec_pink(path: Path) -> tuple[bool, float]:
    """카드 좌/우 가장자리에 마젠타/핑크 비율이 높으면 ACE SPEC으로 판정"""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    # sample left and right borders (ACE SPEC has pink sidebars)
    pink = 0
    total = 0
    for y in range(int(h * 0.15), int(h * 0.85), 2):
        for x in list(range(0, max(1, w // 12))) + list(range(w - max(1, w // 12), w)):
            r, g, b = im.getpixel((x, y))
            total += 1
            # magenta/pink: high R, low-mid G, high-ish B or high R>>G
            if r > 160 and b > 100 and r > g + 30 and (r + b) > g * 2.2:
                pink += 1
            elif r > 180 and g < 120 and b > 80:
                pink += 1
    ratio = pink / total if total else 0
    return ratio >= 0.12, ratio


results = []
false_pos = []
true_pos = []
for r in rows:
    code = r["set_code"]
    num = (r["card_number"] or "x").replace("/", "-")
    matches = list(IMG.glob(f"{code}_{num}.*"))
    if not matches:
        print(f"MISSING {code} {num} {r['name_kr']}")
        continue
    path = matches[0]
    ok, ratio = has_ace_spec_pink(path)
    entry = {**r, "pink_ratio": round(ratio, 3), "visual_ace": ok}
    results.append(entry)
    tag = "ACE_OK" if ok else "NOT_ACE"
    print(f"{tag:8} pink={ratio:.3f} {code:6} #{r['card_number']:10} {r['name_kr']}")
    if ok:
        true_pos.append(entry)
    else:
        false_pos.append(entry)

(OUT / "ace_visual.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "ace_false.json").write_text(json.dumps(false_pos, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nvisual ACE OK={len(true_pos)} FALSE={len(false_pos)}")
print("FALSE list:")
for e in false_pos:
    print(f"  id={e['id']} {e['set_code']} #{e['card_number']} {e['name_kr']}")
