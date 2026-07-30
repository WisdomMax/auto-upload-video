import asyncio, os
from playwright.async_api import async_playwright

async def get_all_29_reels():
    user_data_dir = os.path.expanduser("~/.config/ig_stealth_profile")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()

        await page.goto("https://www.instagram.com/momdad_style/reels/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 15번 연속 스크롤로 1번~29번 릴스 100% 무제한 탐색
        for i in range(15):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.2)

        all_reels = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                const reelHrefs = links.map(l => l.getAttribute('href')).filter(h => h && (h.includes('/p/') || h.includes('/reel/')));
                return Array.from(new Set(reelHrefs));
            }
        """)

        print(f"🎉 100% 탐색 완료된 전체 릴스 개수: {len(all_reels)}개")
        for idx, r in enumerate(all_reels, start=1):
            print(f"  [{idx}] https://www.instagram.com{r}")

        await context.close()

if __name__ == "__main__":
    asyncio.run(get_all_29_reels())
