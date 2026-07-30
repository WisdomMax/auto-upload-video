import asyncio, os
from playwright.async_api import async_playwright

async def check_new_comments():
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

        # 프로필 페이지 접속하여 최근 릴스/게시물 URL 추출
        print("1. momdad_style 프로필 진입하여 최근 게시물 확인...")
        await page.goto("https://www.instagram.com/momdad_style/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        posts = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]'));
                return Array.from(new Set(links.map(l => l.getAttribute('href')))).slice(0, 5);
            }
        """)

        print(f"📋 최근 게시물 URL 5개: {posts}")

        for post_href in posts:
            full_url = f"https://www.instagram.com{post_href}"
            print(f"\n🔍 게시물 확인: {full_url}")
            await page.goto(full_url, wait_until="domcontentloaded")
            await asyncio.sleep(2.5)

            # 스크롤
            await page.evaluate("""
                () => {
                    const divs = document.querySelectorAll('div');
                    for (const d of divs) {
                        if (d.scrollHeight > d.clientHeight && d.clientHeight > 150) {
                            d.scrollTop = d.scrollHeight;
                        }
                    }
                }
            """)
            await asyncio.sleep(1)

            comments = await page.evaluate("""
                () => {
                    const spans = Array.from(document.querySelectorAll('span, a'));
                    const results = [];
                    for (const s of spans) {
                        const txt = s.textContent.trim();
                        if (txt === '엄마' || txt.includes('엄마') || txt.includes('링크') || txt.includes('가격')) {
                            results.push(txt);
                        }
                    }
                    return results;
                }
            """)
            print(f"  - 감지된 댓글 텍스트들: {comments[:10]}")

        await context.close()

if __name__ == "__main__":
    asyncio.run(check_new_comments())
