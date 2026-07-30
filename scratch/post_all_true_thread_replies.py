import asyncio, os
from playwright.async_api import async_playwright

async def post_true_threads():
    print("=== [28번 릴스 12명 댓글에 진짜 대댓글(@태그 보존) 일괄 작성] ===")
    
    usernames = ['sioni_sewing22', 'bongnimjung', 'mikyoung4021', 'jsim55212', 'gang_551112', 'so._.on1102', 'minogyeon83', 'suk19570119', 'jiyeon_3239', 'yeoseosnyeo', 'oweolgwang', 'imeunju1357']
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

        success_count = 0
        for idx, uname in enumerate(usernames, start=1):
            print(f"\n[{idx}/{len(usernames)}] @{uname} 님 답글 달기 시도 중...")
            
            clicked = await page.evaluate(f"""
                () => {{
                    const links = Array.from(document.querySelectorAll('a[href*="/{uname}/"]'));
                    if (links.length === 0) return 'no_user';
                    
                    let container = links[0];
                    for (let i = 0; i < 6; i++) {{
                        if (container.parentElement) container = container.parentElement;
                    }}
                    
                    if (container.textContent.includes('DM으로 링크 보내드렸습니다')) {{
                        return 'already';
                    }}
                    
                    const replyBtn = Array.from(container.querySelectorAll('div, span, button')).find(el => 
                        (el.textContent.trim() === '답글 달기' || el.textContent.trim() === 'Reply') && el.offsetWidth > 0
                    );
                    
                    if (replyBtn) {{
                        replyBtn.click();
                        return 'clicked';
                    }}
                    return 'no_btn';
                }}
            """)
            
            print(f"  - 대댓글 버튼 클릭: {clicked}")
            
            if clicked == 'clicked':
                await asyncio.sleep(1.5)
                input_box = page.locator("textarea, div[role='textbox']").first
                if await input_box.is_visible():
                    await input_box.click()
                    await asyncio.sleep(0.5)
                    # @username 태그를 명시적으로 붙여 진짜 대댓글 스레드로 바인딩!
                    reply_msg = f"@{uname} 안녕하세요! DM으로 링크 보내드렸습니다 💕"
                    await input_box.fill(reply_msg)
                    await asyncio.sleep(1)
                    
                    post_btn = page.locator("button:has-text('게시'), button:has-text('Post'), div[role='button']:has-text('게시'), div[role='button']:has-text('Post')").first
                    if await post_btn.is_visible():
                        await post_btn.click(force=True)
                        await asyncio.sleep(3)
                        print(f"  ✅ @{uname} 진짜 대댓글 작성 완료!")
                        success_count += 1
            elif clicked == 'already':
                print(f"  ℹ️ @{uname} 이미 대댓글 작성 완료됨")

            await asyncio.sleep(1.5)

        await page.screenshot(path="/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/scratch/ig_true_thread_batch_done.png")
        print(f"\n🎉 총 {success_count}명의 댓글에 진짜 대댓글(@태그 결합) 작성을 완결했습니다!")
        await context.close()

if __name__ == "__main__":
    asyncio.run(post_true_threads())
