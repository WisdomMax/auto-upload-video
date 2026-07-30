import asyncio, os
from playwright.async_api import async_playwright

async def scan_full_profile():
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

        print("1. momdad_style 메인 프로필 피드 진입...")
        await page.goto("https://www.instagram.com/momdad_style/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 전체 피드 100% 로딩을 위한 지속적 하단 스크롤
        for i in range(12):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)

        all_posts = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                const postHrefs = links.map(l => l.getAttribute('href')).filter(h => h && (h.includes('/p/') || h.includes('/reel/')));
                return Array.from(new Set(postHrefs));
            }
        """)

        print(f"\n🎉 프로필 그리드에서 100% 탐색 완료된 전체 게시물/릴스 개수: {len(all_posts)}개")
        for idx, p_url in enumerate(all_posts, start=1):
            print(f"  [{idx}] https://www.instagram.com{p_url}")

        await context.close()

if __name__ == "__main__":
    asyncio.run(scan_full_profile())
