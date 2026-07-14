"""Probe image sources for S7F UR 126-128."""
from __future__ import annotations

import os
import re
import sys
import time

import httpx
from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8")

TARGETS = [
    ("126/100", "UR", "파워태블릿", ["パワータブレット", "Power Tablet"]),
    ("127/100", "UR", "트레이닝 코트", ["トレーニングコート", "Training Court"]),
    ("128/100", "UR", "기본 풀 에너지", ["基本草エネルギー", "Basic Grass Energy"]),
]

client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})


def probe(url: str) -> tuple[bool, int]:
    try:
        r = client.get(url)
        ok = r.status_code == 200 and len(r.content) > 5000
        return ok, len(r.content) if ok else r.status_code
    except Exception as e:
        return False, str(e)


def main() -> None:
    for num, rar, kr, keys in TARGETS:
        left = num.split("/")[0]
        right = num.split("/")[1]
        print(f"\n=== {num} {rar} {kr} ===")
        candidates = []
        for jp in ["S8", "s8"]:
            for lf in [left, left.zfill(3), str(int(left))]:
                for suf in [rar, "UR", ""]:
                    for ext in ["webp", "jpg", "png"]:
                        candidates.append(f"https://cdn.collectory.cc/cards/jp/{jp}/{lf}_{right}{suf}.{ext}")
                        candidates.append(f"https://cdn.collectory.cc/cards/kr/BS2021018/{lf}_{right}{suf}.{ext}")
        for url in candidates:
            ok, info = probe(url)
            if ok:
                print("  OK", url, info)
                break
        else:
            print("  CDN: none")

        # pokemon-card.com card search
        for kw in keys:
            q = httpx.URL("https://www.pokemon-card.com/card-search/index.php", params={"keyword": kw, "regulation_sidebar_form": "all"})
            html = client.get(str(q)).text
            ids = re.findall(r"/card-search/details\.php/card/(\d+)", html)
            print(f"  search {kw}: card_ids={ids[:5]}")
            for cid in ids[:3]:
                d = client.get(f"https://www.pokemon-card.com/card-search/details.php/card/{cid}").text
                img = re.search(r'(https?://[^"\']+?\.(?:png|jpg|webp))', d)
                num_match = re.search(r"(\d{3})\s*/\s*(\d{3})", d)
                set_match = re.search(r"フュージョンアーツ|Fusion Arts|S8", d)
                if img:
                    print(f"    id={cid} num={num_match.group(0) if num_match else '?'} set={bool(set_match)} img={img.group(1)[:80]}")
            time.sleep(0.5)


if __name__ == "__main__":
    main()
