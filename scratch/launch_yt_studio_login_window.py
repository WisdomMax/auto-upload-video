import asyncio, os
from playwright.async_api import async_playwright

async def open_login_window():
    user_data_dir = os.path.expanduser("~/.config/yt_stealth_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    print("=== 🚀 [YouTube Studio 로그인용 브라우저 창 가동] ===")
    print("💡 맥미니 화면에 크롬 창이 열렸습니다. 구글 로그인을 진행해 주세요!")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # 화면에 직접 표시
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://studio.youtube.com/channel/UC-bYx0BTsO133T_jRL96o4Q/comments", wait_until="domcontentloaded")
        
        # Wait up to 180 seconds for user to log in and land on studio.youtube.com
        logged_in = False
        for _ in range(90):
            await asyncio.sleep(2)
            url = page.url
            if "studio.youtube.com" in url and "accounts.google.com" not in url:
                logged_in = True
                break
                
        if logged_in:
            print("\n" + "="*70)
            print("🎉🎉 [축하합니다! YouTube Studio 로그인 세션 저장 완결!]")
            print("이제 이 창을 닫으셔도 로그인 세션이 영구 보존되어 24시간 자동 하트(❤️)가 켜집니다!")
            print("="*70 + "\n")
            await asyncio.sleep(3)
        else:
            print("⚠️ 로그인 대기 시간이 초과되었습니다. 다시 시도해 주세요.")
            
        await context.close()

asyncio.run(open_login_window())
