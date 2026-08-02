import asyncio, os
from playwright.async_api import async_playwright

async def test_main_comments():
    user_data_dir = os.path.expanduser("~/.config/yt_stealth_profile")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://studio.youtube.com/comments", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        print("URL:", page.url)
        print("Title:", await page.title())
        await page.screenshot(path="scratch/yt_studio_main_comments.png")
        await context.close()

asyncio.run(test_main_comments())
