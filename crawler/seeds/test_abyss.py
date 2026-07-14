"""pokecahack에서 SAR 이미지 URL 추출"""
import asyncio, re
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://pokecahack.com/m5/", timeout=30000)
        await asyncio.sleep(3)

        # SAR 섹션 이미지 추출
        imgs = await page.evaluate('''
            () => {
                const results = [];
                const imgs = document.querySelectorAll("img");
                for (const img of imgs) {
                    const alt = img.alt || "";
                    const src = img.src || "";
                    const parent = img.closest("h2, h3, h4, section, div");
                    const context = parent ? parent.textContent.slice(0,50) : "";
                    if (src.includes("pokemon-card.com") || src.includes("card")) {
                        results.push({alt, src: src.slice(0,120), context});
                    }
                }
                return results.slice(0, 30);
            }
        ''')
        for img in imgs:
            print(img)

        # SAR 텍스트 주변 이미지
        sar_section = await page.evaluate('''
            () => {
                const all = document.body.innerHTML;
                const sarIdx = all.indexOf("SAR");
                return all.slice(sarIdx, sarIdx + 3000);
            }
        ''')
        urls = re.findall(r'https?://[^"\'<>\s]+\.(?:jpg|png|webp)', sar_section or "")
        print("\nSAR URLs:", urls[:10])

        await browser.close()

asyncio.run(main())
