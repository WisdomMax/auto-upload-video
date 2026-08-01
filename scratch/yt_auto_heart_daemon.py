import asyncio, os, time
from playwright.async_api import async_playwright

async def run_yt_heart_and_like():
    user_data_dir = os.path.expanduser("~/.config/yt_stealth_profile")
    print("=== 🚀 [유튜브 스튜디오 '엄마아빠 패션다이어리' 하트(❤️) + 좋아요(👍) 정밀 가동] ===")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        # 1. 스튜디오 메인 진입
        await page.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        
        # 2. 커뮤니티/댓글 메뉴 클릭
        try:
            menu_btn = page.locator("a[href*='comments'], #menu-item-comments, tp-yt-paper-item:has-text('커뮤니티'), tp-yt-paper-item:has-text('댓글')").first
            if await menu_btn.is_visible():
                await menu_btn.click()
                await asyncio.sleep(5)
        except Exception as e_menu:
            print("메뉴 클릭 예외:", e_menu)
            
        hearts_clicked = 0
        likes_clicked = 0
        
        try:
            # Scroll to load more comments
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1.5)
                
            # Click Heart buttons
            # Inspect heart buttons via evaluate script
            clicked_h = await page.evaluate("""
                () => {
                    let count = 0;
                    // Find all heart containers / buttons in YouTube Studio comments
                    const hearts = document.querySelectorAll('ytcp-comment-heart #button, button#heart-button, #heart-button, [aria-label*="하트"]');
                    hearts.forEach(el => {
                        if (el && el.click) {
                            el.click();
                            count++;
                        }
                    });
                    return count;
                }
            """)
            hearts_clicked = clicked_h

            # Click Like buttons
            clicked_l = await page.evaluate("""
                () => {
                    let count = 0;
                    const likes = document.querySelectorAll('ytcp-comment-action-buttons #like-button, button#like-button');
                    likes.forEach(el => {
                        if (el && el.click) {
                            el.click();
                            count++;
                        }
                    });
                    return count;
                }
            """)
            likes_clicked = clicked_l

            print(f"\n🎉🎉 [완료] 유튜브 '엄마아빠 패션다이어리' 댓글 하트(❤️) {hearts_clicked}개 / 좋아요(👍) {likes_clicked}개 클릭 완료!")
            
            # Screenshot proof
            await page.screenshot(path="scratch/yt_heart_live_proof_eval.png")
            print("📸 라이브 스크린샷 증명 저장: scratch/yt_heart_live_proof_eval.png")
            
        except Exception as e:
            print(f"⚠️ 자동 하트 진행 중 예외: {e}")
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_yt_heart_and_like())
