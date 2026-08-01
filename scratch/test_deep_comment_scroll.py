import asyncio, os
from playwright.async_api import async_playwright

async def test_deep_scroll_comments():
    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # Test on reel 29 (DbWg-WlkdhL)
        reel_url = "https://www.instagram.com/momdad_style/reel/DbWg-WlkdhL/"
        print(f"=== [릴스 전체 댓글 100% 딥 스크롤 스캔 테스트: {reel_url}] ===")
        await page.goto(reel_url, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # Click 'View comments' or scroll comment section repeatedly
        click_more_count = 0
        for i in range(25):
            clicked = await page.evaluate("""
                () => {
                    // Look for 'View more comments', '댓글 더보기', '+' icon, or reply buttons
                    const btns = Array.from(document.querySelectorAll('span, div[role="button"], button'));
                    const moreBtn = btns.find(b => {
                        const txt = b.textContent.trim();
                        return (txt.includes('댓글 더 보기') || txt.includes('View more comments') || txt.includes('댓글 더보기') || txt === '+') && b.offsetWidth > 0;
                    });
                    if (moreBtn) {
                        moreBtn.click();
                        return true;
                    }
                    return false;
                }
            """)
            if clicked:
                click_more_count += 1
                await asyncio.sleep(1.2)
            
            # Scroll down comment section container
            await page.evaluate("""
                () => {
                    const containers = Array.from(document.querySelectorAll('div[class*="x1n2onr6"], ul, div[role="dialog"]'));
                    for (const c of containers) {
                        if (c.scrollHeight > c.clientHeight) {
                            c.scrollTop += 1500;
                        }
                    }
                    window.scrollTo(0, document.body.scrollHeight);
                }
            """)
            await asyncio.sleep(1.0)

        # Extract all comments rendered
        comments = await page.evaluate("""
            () => {
                const nodes = Array.from(document.querySelectorAll('span'));
                const userComments = [];
                for (const n of nodes) {
                    const txt = n.textContent.trim();
                    if (txt.length > 1 && !txt.includes('좋아요') && !txt.includes('답글') && !txt.includes('게시') && !txt.includes('수정')) {
                        // find parent username
                        let p = n;
                        let uname = '';
                        for (let k = 0; k < 5; k++) {
                            if (p.parentElement) p = p.parentElement;
                            const a = p.querySelector('a[href^="/"]');
                            if (a) {
                                const href = a.getAttribute('href');
                                if (href && href !== '/' && !href.includes('/reel/')) {
                                    uname = href.replace(/\//g, '');
                                    break;
                                }
                            }
                        }
                        if (uname && uname !== 'momdad_style') {
                            userComments.append ? userComments.append({uname, txt}) : userComments.push({uname, txt});
                        }
                    }
                }
                return userComments;
            }
        """)

        print(f"📊 딥 스크롤 결과: '댓글 더보기' 클릭 {click_more_count}회 수행")
        print(f"🔥 총 추출된 사용자 댓글 수: {len(comments)}개!")
        
        unique_users = set(c['uname'] for c in comments)
        print(f"👥 추출된 순수 유저 수: {len(unique_users)}명!")

        await context.close()

if __name__ == '__main__':
    asyncio.run(test_deep_scroll_comments())
