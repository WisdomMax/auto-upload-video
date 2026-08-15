import asyncio, os, sys
from playwright.async_api import async_playwright

async def open_tiktok_login_window():
    user_data_dir = os.path.expanduser("~/.config/tiktok_stealth_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    print("\n" + "="*70)
    print("=== 🚀 [TikTok '@momdad_style' 로그인 브라우저 가동] ===")
    print("💡 맥 화면에 틱톡 로그인 창이 열렸습니다.")
    print("📱 스마트폰 틱톡 앱으로 [QR 코드 스캔] 또는 [아이디/비번 로그인]을 진행해 주세요.")
    print("👉 로그인이 완료되면 이 터미널에서 [Enter(엔터)] 키를 누르시면 세션이 영구 저장됩니다!")
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
        
        # 터미널에서 사용자가 엔터를 누를 때까지 창을 끄지 않고 무제한 대기
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input, "\n👉 브라우저에서 로그인을 완료하신 후, 여기 터미널에서 [Enter]를 눌러주세요: ")
        
        print("\n" + "="*70)
        print("🎉🎉 [축하합니다! TikTok '@momdad_style' 로그인 세션 저장 완결!]")
        print("세션이 '~/.config/tiktok_stealth_profile'에 영구 보존되었습니다.")
        print("="*70 + "\n", flush=True)
        await asyncio.sleep(2)
        await context.close()

if __name__ == "__main__":
    asyncio.run(open_tiktok_login_window())
