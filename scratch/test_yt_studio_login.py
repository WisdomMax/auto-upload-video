import asyncio, os
from playwright.async_api import async_playwright

async def check_studio_login():
    user_data_dir = os.path.expanduser("~/.config/ig_stealth_profile") # check existing profile or yt profile
    print("=== 🚀 [YouTube Studio 로그인 세션 상태 검증] ===")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://studio.youtube.com/channel/UC-bYx0BTsO133T_jRL96o4Q/comments", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        
        url = page.url
        title = await page.title()
        print("Current URL:", url)
        print("Page Title:", title)
        
        is_logged_in = "studio.youtube.com" in url and "accounts.google.com" not in url
        print(f"📌 YouTube Studio 로그인 여부: {is_logged_in}")
        
        # Take screenshot for proof
        await page.screenshot(path="scratch/yt_studio_login_proof.png")
        print("Saved screenshot to scratch/yt_studio_login_proof.png")
        
        await context.close()

asyncio.run(check_studio_login())
