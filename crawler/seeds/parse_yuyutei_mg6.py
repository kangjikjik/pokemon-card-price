"""유유테이 MG6 전체 카드 파싱 (SAR/SR/AR/MUR 포함)"""
import re
import httpx

BASE = "https://yuyu-tei.jp/sell/poc/s/MG6"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ja-JP"}

# 카드명 + 가격 + 링크 패턴
CARD_RE = re.compile(
    r'([\u3040-\u9fff\u30a0-\u30ffa-zA-Z0-9ぁ-んー・の決戦]+(?:ex|EX)?)\s+([\d,]+)\s*円\s*<a[^>]+href="([^"]+/sell/poc/card/m05/(\d+))"',
    re.DOTALL,
)

IMG_RE = re.compile(r'https://card\.yuyu-tei\.jp/poc/100_140/m05/(\d+)\.jpg')

# alt 태그에서 카드번호/레어도
ALT_RE = re.compile(
    r'alt="\s*(\d+/\d+)\s+([A-Z]+(?:\s+[A-Z]+)?)\s+([^"]+?)\s*"'
)


def fetch_all() -> list[dict]:
    cards: dict[str, dict] = {}
    urls = [BASE, f"{BASE}?rare=SAR", f"{BASE}?rare=SR", f"{BASE}?rare=AR", f"{BASE}?rare=MUR", f"{BASE}?rare=RR"]

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20) as c:
        for url in urls:
            text = c.get(url).text
            for m in CARD_RE.finditer(text):
                name, price, href, cid = m.groups()
                name = name.strip()
                key = f"{cid}_{name}"
                cards[key] = {
                    "name_jp": name,
                    "price_jpy": int(price.replace(",", "")),
                    "href": href,
                    "card_id": cid,
                    "image_url": f"https://card.yuyu-tei.jp/poc/100_140/m05/{cid}.jpg",
                    "source_url": url,
                }
            for m in ALT_RE.finditer(text):
                num, rarity, name = m.groups()
                if "/081" in num or "/083" in num or "M5" in num or num.endswith("/081"):
                    key = f"alt_{num}_{name.strip()}"
                    cards[key] = {
                        "name_jp": name.strip(),
                        "card_number": num.strip(),
                        "rarity": rarity.strip().split()[0],
                        "price_jpy": 0,
                        "image_url": "",
                    }

    return list(cards.values())


if __name__ == "__main__":
    cards = fetch_all()
    print(f"Total: {len(cards)}")
    # 가격순 정렬
    priced = [c for c in cards if c.get("price_jpy", 0) > 0]
    priced.sort(key=lambda x: -x["price_jpy"])
    print("\n=== Top by price ===")
    for c in priced[:20]:
        print(f"{c['price_jpy']:>8}円 | {c['name_jp']} | {c.get('card_id','')} | {c['image_url']}")

    print("\n=== Alt tags (secret) ===")
    for c in cards:
        if c.get("card_number"):
            print(c)
