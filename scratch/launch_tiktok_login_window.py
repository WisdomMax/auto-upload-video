import asyncio, os
from playwright.async_api import async_playwright

async def open_tiktok_login_window():
    user_data_dir = os.path.expanduser("~/.config/tiktok_stealth_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    print("\n" + "="*70)
    print("=== 🚀 [TikTok '@momdad_style' 로그인용 브라우저 창 가동] ===")
    print("💡 맥 화면에 틱톡 로그인 창이 열렸습니다.")
    print("📱 스마트폰 틱톡 앱으로 [QR 코드 스캔] 또는 [간편 로그인]을 완료해 주세요!")
    print("="*70 + "\n", flush=True)
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # 화면에 직접 창을 띄움
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://www.tiktok.com/login", wait_until="domcontentloaded")
        
        # 최대 180초 동안 사용자 로그인 대기
        logged_in = False
        for i in range(90):
            await asyncio.sleep(2)
            url = page.url
            # 로그인 완료 시 프로필 아이콘 또는 피드/프로필 페이지로 이동
            is_login_page = "login" in url
            has_profile_avatar = await page.evaluate("""
                () => {
                    const avatar = document.querySelector('[data-e2e="profile-icon"], img[class*="Avatar"], a[href*="/@"]');
                    const logoutBtn = document.querySelector('button:has-text("Log out"), div:has-text("로그아웃")');
                    return !!(avatar || logoutBtn);
                }
            """)
            
            if not is_login_page and (has_profile_avatar or "@" in url):
                logged_in = True
                break
                
        if logged_in:
            print("\n" + "="*70)
            print("🎉🎉 [축하합니다! TikTok '@momdad_style' 로그인 세션 저장 완결!]")
            print("이제 이 창을 닫으셔도 로그인 세션이 영구 보존되어 24시간 틱톡 자동 응답 데몬이 작동합니다!")
            print("="*70 + "\n", flush=True)
            await asyncio.sleep(3)
        else:
            print("⚠️ 로그인 대기 시간이 초과되었습니다. 다시 시도해 주세요.", flush=True)
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(open_tiktok_login_window())
