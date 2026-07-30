import asyncio, os
from playwright.async_api import async_playwright

async def test_true_thread():
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

        url_28 = "https://www.instagram.com/p/DbAkcJDE7dt/"
        print(f"1. 28번 릴스 접속: {url_28}")
        await page.goto(url_28, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 1개의 댓글 작성자 (예: sioni_sewing22) 에 대해 테스트
        target_username = "sioni_sewing22"
        reply_msg = f"@{target_username} 안녕하세요! DM으로 링크 보내드렸습니다 💕"

        print(f"2. @{target_username} 답글 달기 버튼 클릭...")
        clicked = await page.evaluate(f"""
            () => {{
                const links = Array.from(document.querySelectorAll('a[href*="/{target_username}/"]'));
                if (links.length === 0) return false;
                
                let container = links[0];
                for (let i = 0; i < 6; i++) {{
                    if (container.parentElement) container = container.parentElement;
                }}
                
                const replyBtn = Array.from(container.querySelectorAll('div, span, button')).find(el => 
                    (el.textContent.trim() === '답글 달기' || el.textContent.trim() === 'Reply') && el.offsetWidth > 0
                );
                
                if (replyBtn) {{
                    replyBtn.click();
                    return true;
                }}
                return false;
            }}
        """)
        
        print(f"  - 클릭 결과: {clicked}")
        await asyncio.sleep(2)

        # 입력창에 @username 이 포함된 텍스트 채우기
        input_box = page.locator("textarea, div[role='textbox']").first
        if await input_box.is_visible():
            await input_box.click()
            await asyncio.sleep(0.5)
            # fill 텍스트에 @username 필수 포함!
            await input_box.fill(reply_msg)
            await asyncio.sleep(1)
            
            post_btn = page.locator("button:has-text('게시'), button:has-text('Post'), div[role='button']:has-text('게시'), div[role='button']:has-text('Post')").first
            if await post_btn.is_visible():
                await post_btn.click(force=True)
                await asyncio.sleep(3)
                print(f"✅ @{target_username} 에게 진짜 대댓글 작성 완료!")

        await page.screenshot(path="/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/scratch/ig_true_thread_result.png")
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_true_thread())
