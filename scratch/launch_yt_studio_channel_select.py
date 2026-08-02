import asyncio, os
from playwright.async_api import async_playwright

async def open_channel_select_window():
    user_data_dir = os.path.expanduser("~/.config/yt_stealth_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    print("=== 🚀 [YouTube 스튜디오 채널 선택 브라우저 창 가동] ===")
    print("💡 맥미니 화면에 크롬 창이 열렸습니다. '엄마아빠 패션다이어리' 채널을 선택해 주세요!")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # 화면에 표시
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://studio.youtube.com/comments", wait_until="domcontentloaded")
        
        # Wait up to 300 seconds for user to select channel and land on Studio comments page
        logged_in = False
        for _ in range(150):
            await asyncio.sleep(2)
            url = page.url
            title = await page.title()
            if "studio.youtube.com" in url and "comments" in url and "accounts.google.com" not in url:
                # Check if page has studio content
                if "스튜디오" in title or "Studio" in title or "댓글" in title:
                    logged_in = True
                    break
                
        if logged_in:
            print("\n" + "="*70)
            print("🎉🎉 [축하합니다! '엄마아빠 패션다이어리' 스튜디오 채널 세션 저장 완료!]")
            print("="*70 + "\n")
            await asyncio.sleep(5)
        else:
            print("⚠️ 대기 시간 초과")
            
        await context.close()

asyncio.run(open_channel_select_window())
