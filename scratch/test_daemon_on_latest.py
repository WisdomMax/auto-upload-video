import asyncio, os
from playwright.async_api import async_playwright

async def test_latest_reel_reply():
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

        # 최신 릴스 진입
        url_latest = "https://www.instagram.com/momdad_style/reel/DbWg-WlkdhL/"
        print(f"1. 최신 릴스 진입: {url_latest}")
        await page.goto(url_latest, wait_until="domcontentloaded")
        await asyncio.sleep(3)

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
        await asyncio.sleep(1.5)

        # 댓글들 캡처
        await page.screenshot(path="/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/scratch/ig_latest_reel_comments.png")
        
        # 댓글 텍스트 목록 출력
        comments_info = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                const results = [];
                const blacklist = ['legal', 'privacy', 'terms', 'cookies', 'popular', 'weblite', 'accounts', 'meta', 'about', 'help', 'api', 'jobs', 'explore', 'momdad_style'];
                
                for (const a of links) {
                    const href = a.getAttribute('href');
                    const text = a.textContent.trim();
                    if (href && href.startsWith('/') && !href.includes('p/') && !href.includes('reels/') && text.length > 1) {
                        const uname = href.replace(/\//g, '').trim();
                        if (!/^[a-zA-Z0-9._]+$/.test(uname)) continue;
                        if (blacklist.some(b => uname.toLowerCase().includes(b))) continue;
                        results.push({ username: uname, href: href });
                    }
                }
                return results;
            }
        """)
        
        print("=== 최신 릴스 댓글 작성자 목록 ===")
        print(comments_info)
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_latest_reel_reply())
