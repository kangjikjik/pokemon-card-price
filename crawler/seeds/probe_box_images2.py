import httpx, re
HEADERS = {"User-Agent": "Mozilla/5.0"}
# pokemon official expansion pages
pages = {
    "SV5a": "917",
    "SV2a": "882",
    "MG6": "954",
}
for code, pg in pages.items():
    url = f"https://www.pokemon-card.com/ex/sv/sv{pg}/" if not code.startswith("MG") else f"https://www.pokemon-card.com/ex/mega/"
    # try product search API
    api = f"https://www.pokemon-card.com/card-search/resultAPI.php?pg={pg}&regulation_sidebar_form=all&se_ta=&keyword=&card_kind=all&card_kind_mode=all"
    r = httpx.get(api, headers=HEADERS, timeout=20)
    imgs = re.findall(r'https://[^"\']+\.(?:jpg|png)', r.text)
    print(f"=== {code} api imgs {len(imgs)} ===")
    for u in imgs[:3]:
        print(" ", u[:100])

# try pokeca expansion list image
r = httpx.get("https://www.pokemon-card.com/products/sv/sv5a.html", headers=HEADERS, follow_redirects=True, timeout=20)
print("sv5a page", r.status_code, len(r.text))
imgs = re.findall(r'src="(/assets/[^"]+\.(?:jpg|png))"', r.text)
for u in imgs[:10]:
    print(" ", u)
