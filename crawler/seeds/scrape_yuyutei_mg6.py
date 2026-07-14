"""유유테이 MG6(어비스아이) 카드 목록 스크래핑"""
import asyncio
import re
import httpx
from playwright.async_api import async_playwright

URLS = [
    "https://yuyu-tei.jp/sell/poc/s/MG6",
    "https://yuyu-tei.jp/sell/poc/s/search?search_word=アビスアイ",
    "https://yuyu-tei.jp/sell/poc/s/search?search_word=MG6",
]


async def scrape_httpx():
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ja-JP"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20) as c:
        for url in URLS:
            r = await c.get(url)
            print(f"\n=== {url} status={r.status_code} len={len(r.text)} ===")
            # card.yuyu-tei.jp 이미지
            imgs = re.findall(r'https://card\.yuyu-tei\.jp/poc/[^"\']+\.jpg', r.text)
            names = re.findall(r'<h4[^>]*>([^<]+)</h4>', r.text)
            prices = re.findall(r'([\d,]+)\s*円', r.text)
            print(f"  images: {len(imgs)}, names: {len(names)}, prices: {len(prices)}")
            for i, (n, img) in enumerate(zip(names[:15], imgs[:15])):
                print(f"  {n} | {img}")


async def scrape_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://yuyu-tei.jp/sell/poc/s/MG6", timeout=30000)
        await asyncio.sleep(2)

        # 레어도 탭 클릭 시도
        for label in ["SAR", "SR", "AR", "RR", "MUR"]:
            try:
                btn = page.locator(f"text={label}").first
                if await btn.count() > 0:
                    await btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

        cards = await page.evaluate('''
            () => {
                const results = [];
                document.querySelectorAll("a[href*='/sell/poc/card/']").forEach(a => {
                    const img = a.querySelector("img");
                    const h4 = a.querySelector("h4") || a.closest("div")?.querySelector("h4");
                    const price = a.closest("div")?.querySelector("strong");
                    if (h4) {
                        results.push({
                            name: h4.textContent.trim(),
                            img: img ? img.src : "",
                            href: a.href,
                            price: price ? price.textContent.trim() : ""
                        });
                    }
                });
                return results;
            }
        ''')
        print(f"\nPlaywright MG6: {len(cards)} cards")
        for c in cards[:30]:
            print(c)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_httpx())
    asyncio.run(scrape_playwright())
