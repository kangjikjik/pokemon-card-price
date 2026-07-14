"""Find images for BW4 UR cards and probe EX→RR mapping."""
from __future__ import annotations

import re
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")
client = httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})

for i in [74, 75, 76]:
    r = client.get(f"https://www.serebii.net/card/darkrush/{i:03d}.shtml")
    imgs = re.findall(r'src="(/card/darkrush/[^"]+)"', r.text)
    print(i, r.status_code, imgs[:5])
    for src in imgs[:3]:
        u = "https://www.serebii.net" + src
        ir = client.get(u)
        print(" ", ir.status_code, len(ir.content), u)

# JP pokemon-card search
print("\n=== jp tries ===")
jp_patterns = [
    "https://www.pokemon-card.com/assets/images/card_images/large/BW4/022xxx_P_SANAITO.jpg",
]
for u in [
    "https://www.pokemon-card.com/card-search/details.php/card/28564",
    "https://pokemontcg.io",
]:
    r = client.get(u)
    print(u, r.status_code, len(r.content))

# pkmncards
for q in ["gardevoir dark-rush", "bw4-074"]:
    pass

for i, slug in [(74, "gardevoir"), (75, "archeops"), (76, "pokemon-catcher")]:
    for u in [
        f"https://images.pokemontcg.io/bw5/{i}.png",  # dark explorers?
        f"https://images.pokemontcg.io/bw5/{i}_hires.png",
        f"https://serebii.net/card/darkrush/{i:03d}.jpg",
        f"https://www.serebii.net/card/darkrush/{i:03d}.jpg",
        f"https://www.serebii.net/card/darkrush/{i:03d}.png",
    ]:
        r = client.get(u)
        ct = r.headers.get("content-type", "")
        if r.status_code == 200 and "image" in ct:
            print("OK", len(r.content), u)
            break
        else:
            print(r.status_code, ct[:30], u)
