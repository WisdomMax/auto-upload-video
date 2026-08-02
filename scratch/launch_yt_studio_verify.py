import asyncio, os
from playwright.async_api import async_playwright

async def open_verify_window():
    user_data_dir = os.path.expanduser("~/.config/yt_stealth_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    print("=== 🚀 [YouTube Studio 본인 인증 및 채널 전환 브라우저 가동] ===")
    print("💡 맥미니 화면에 크롬 창이 열렸습니다. 본인 인증 및 채널을 선택해 주세요!")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # 화면에 직접 표시
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
        
        # Keep open for 300 seconds so user can complete Identity Verification & Channel Switch
        for _ in range(150):
            await asyncio.sleep(2)
            
        await context.close()

asyncio.run(open_verify_window())
