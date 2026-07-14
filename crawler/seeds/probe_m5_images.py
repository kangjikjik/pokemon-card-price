"""M5 어비스아이 시크릿 카드 이미지 URL 탐색"""
import asyncio
import httpx
from playwright.async_api import async_playwright

JP_BASE = "https://www.pokemon-card.com"
# cardID = 50220 + (card_number - 1)
# SAR: 112-117, MUR: 118, SR: 082-099, AR: 100-111

SECRET_CARDS = [
    (112, "SAR", "メガゼラオラex", "050331"),
    (113, "SAR", "メガシャンデラex", "050332"),
    (114, "SAR", "メガダークライex", "050333"),
    (115, "SAR", "モルペコex", "050334"),
    (116, "SAR", "グラジオの決戦", "050335"),
    (117, "SAR", "ムク", "050336"),
    (118, "MUR", "メガダークライex", "050337"),
]

# 다양한 파일명 패턴 시도
def url_patterns(card_id: str, name_hint: str):
    short = name_hint.replace("メガ", "M").replace("ex", "EX")[:20]
    patterns = [
        f"/assets/images/card_images/large/M5/{card_id}_P_{name_hint}.jpg",
        f"/assets/images/card_images/large/M5/{card_id}.jpg",
        f"/assets/images/card_images/large/M5/{card_id}_P_M{name_hint[2:]}.jpg" if name_hint.startswith("メガ") else None,
    ]
    return [p for p in patterns if p]


async def probe_urls():
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for num, rarity, name, cid in SECRET_CARDS:
            for path in url_patterns(cid, name):
                url = JP_BASE + path
                try:
                    r = await client.head(url)
                    if r.status_code == 200:
                        print(f"OK {num} {rarity} {name}: {url}")
                        break
                except Exception:
                    pass
            else:
                print(f"MISS {num} {rarity} {name} (id={cid})")


async def probe_yuyutei():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://yuyu-tei.jp/sell/poc/s/MG6", timeout=30000)
        await asyncio.sleep(3)
        imgs = await page.evaluate('''
            () => {
                const items = [];
                document.querySelectorAll(".card-product, .product-item, [class*='card']").forEach(el => {
                    const img = el.querySelector("img");
                    const name = el.querySelector("h4, .card-name, a");
                    const price = el.querySelector("strong, .price");
                    if (img && img.src) {
                        items.push({
                            name: name ? name.textContent.trim().slice(0,40) : "",
                            src: img.src.slice(0,100),
                            price: price ? price.textContent.trim() : ""
                        });
                    }
                });
                return items.slice(0, 20);
            }
        ''')
        for i in imgs:
            print(i)
        await browser.close()


if __name__ == "__main__":
    print("=== Official URL probe ===")
    asyncio.run(probe_urls())
    print("\n=== Yuyutei MG6 ===")
    asyncio.run(probe_yuyutei())
