"""공식 API 응답 구조 확인"""
import asyncio, json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.pokemon-card.com/card-search/index.php?pg=954", timeout=30000)
        await asyncio.sleep(3)
        data = await page.evaluate('''
            async () => {
                const resp = await fetch("/card-search/resultAPI.php?pg=954", {credentials:"include"});
                return await resp.json();
            }
        ''')
        cards = data.get("cardList", [])[:3]
        print(json.dumps(cards, ensure_ascii=False, indent=2))
        await browser.close()

asyncio.run(main())
