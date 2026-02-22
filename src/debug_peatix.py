"""Peatix スクレイパーのデバッグスクリプト"""
import sys
import io
import json
import asyncio

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from playwright.async_api import async_playwright


async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ja-JP",
        )
        page = await context.new_page()
        await page.goto(
            "https://peatix.com/search?lang=ja&q=ゲーム開発", timeout=30000
        )
        try:
            await page.wait_for_selector("h2", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)

        data = await page.evaluate(
            """() => {
            const headings = document.querySelectorAll('h2');
            let targetList = null;
            for (const h of headings) {
                if (h.textContent.includes('検索結果')) {
                    let sibling = h.nextElementSibling;
                    while (sibling) {
                        if (sibling.tagName === 'UL') { targetList = sibling; break; }
                        sibling = sibling.nextElementSibling;
                    }
                    break;
                }
            }
            if (!targetList) return {error: 'no list found'};
            const items = targetList.querySelectorAll('li');
            const results = [];
            for (let i = 0; i < Math.min(3, items.length); i++) {
                const item = items[i];
                const link = item.querySelector('a');
                if (!link) continue;
                const h3 = item.querySelector('h3');

                // innerText vs textContent comparison
                const innerText = link.innerText || '';
                const textContent = link.textContent || '';

                results.push({
                    title: h3 ? h3.textContent.trim() : '',
                    innerText: innerText,
                    innerTextLines: innerText.split('\\n'),
                    textContent: textContent.substring(0, 200),
                    url: (link.getAttribute('href') || '').split('?')[0],
                });
            }
            return results;
        }"""
        )

        print(json.dumps(data, ensure_ascii=False, indent=2))
        await browser.close()


asyncio.run(debug())
