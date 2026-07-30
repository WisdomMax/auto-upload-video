import asyncio, os, database
from playwright.async_api import async_playwright

async def fix_thread_replies():
    print("=== [28번 릴스 실물 대댓글 100% 보완 작성] ===")
    
    reply_text = "안녕하세요! DM으로 링크 보내드렸습니다 💕"
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
        print(f"1. 릴스 접속: {url_28}")
        await page.goto(url_28, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 캡션 오른쪽 댓글 영역 스크롤하여 댓글들 완전히 노출시키기
        print("2. 댓글 창 내부 스크롤 및 댓글 불러오기...")
        await page.evaluate("""
            () => {
                const scrollables = document.querySelectorAll('div');
                for (const div of scrollables) {
                    if (div.scrollHeight > div.clientHeight && div.clientHeight > 200) {
                        div.scrollTop = div.scrollHeight;
                    }
                }
            }
        """)
        await asyncio.sleep(2)

        # 스크린샷 확인
        await page.screenshot(path="/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/scratch/ig_replies_before.png")

        # 각 사용자 댓글 바로 아래 답글 달기 버튼 탐색 및 작성
        usernames = ['sioni_sewing22', 'bongnimjung', 'mikyoung4021', 'jsim55212', 'gang_551112', 'so._.on1102', 'minogyeon83', 'suk19570119', 'jiyeon_3239', 'yeoseosnyeo', 'oweolgwang', 'imeunju1357']
        
        success_count = 0
        for uname in usernames:
            print(f"\n👉 @{uname} 님 댓글 답글 달기 시도 중...")
            
            # 해당 사용자 댓글 영역 내 '답글 달기' 버튼 클릭
            clicked = await page.evaluate(f"""
                async () => {{
                    const userLinks = Array.from(document.querySelectorAll('a[href*="/{uname}/"]'));
                    if (userLinks.length === 0) return 'no_user';
                    
                    const userLink = userLinks[0];
                    let parent = userLink;
                    for (let i = 0; i < 6; i++) {{
                        if (parent.parentElement) parent = parent.parentElement;
                    }}
                    
                    // 이미 답글이 달렸는지 확인
                    if (parent.textContent.includes('DM으로 링크 보내드렸습니다')) {{
                        return 'already';
                    }}
                    
                    const replyBtn = Array.from(parent.querySelectorAll('div, span, button')).find(el => 
                        (el.textContent.trim() === '답글 달기' || el.textContent.trim() === 'Reply') && el.offsetWidth > 0
                    );
                    
                    if (replyBtn) {{
                        replyBtn.click();
                        return 'clicked';
                    }}
                    return 'no_btn';
                }}
            """)
            
            print(f"  - 대댓글 버튼 상태: {clicked}")
            
            if clicked == 'clicked':
                await asyncio.sleep(1.5)
                # 입력창 타이핑 & 게시
                input_box = page.locator("textarea, div[role='textbox']").first
                if await input_box.is_visible():
                    await input_box.click()
                    await asyncio.sleep(0.5)
                    await input_box.fill(reply_text)
                    await asyncio.sleep(1)
                    
                    post_btn = page.locator("button:has-text('게시'), button:has-text('Post'), div[role='button']:has-text('게시'), div[role='button']:has-text('Post')").first
                    if await post_btn.is_visible():
                        await post_btn.click(force=True)
                        await asyncio.sleep(3)
                        print(f"  ✅ @{uname} 대댓글 게시 완료!")
                        success_count += 1
            elif clicked == 'already':
                print(f"  ℹ️ @{uname} 이미 대댓글 작성됨")
            
            await asyncio.sleep(1.5)

        # 결과 스크린샷
        await page.screenshot(path="/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/scratch/ig_replies_after.png")
        print(f"\n🎉 [완료] 대댓글 보완 작성 총 {success_count}건 완료!")
        await context.close()

if __name__ == "__main__":
    asyncio.run(fix_thread_replies())
