import asyncio, json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.pokemon-card.com/card-search/index.php?pg=954", timeout=30000)
        await asyncio.sleep(3)
        all_cards = []
        for pg in range(1, 5):
            data = await page.evaluate(f'''
                async () => {{
                    const resp = await fetch("/card-search/resultAPI.php?pg=954&page={pg}", {{credentials:"include"}});
                    return await resp.json();
                }}
            ''')
            batch = data.get("cardList", [])
            if not batch:
                break
            for c in batch:
                num = int(c["cardID"]) - 50219
                all_cards.append((num, c["cardNameViewText"], c["cardID"]))
            if pg >= data.get("maxPage", 1):
                break
        await browser.close()

    for num, name, cid in all_cards:
        print(f"{num:03d} {name} {cid}")

asyncio.run(main())
