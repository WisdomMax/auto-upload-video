import asyncio, os
from playwright.async_api import async_playwright

async def test_nav():
    user_data_dir = os.path.expanduser("~/.config/yt_stealth_profile")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Navigate to main studio URL first
        await page.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        print("Studio Main URL:", page.url)
        print("Studio Main Title:", await page.title())
        
        # Click Comments link on left menu
        try:
            comments_menu = page.locator("a[href*='comments'], #menu-item-comments, tp-yt-paper-item:has-text('댓글'), tp-yt-paper-item:has-text('Comments')").first
            if await comments_menu.is_visible():
                await comments_menu.click()
                await asyncio.sleep(4)
        except Exception as e:
            print("Click comments menu error:", e)
            
        print("After Nav URL:", page.url)
        await page.screenshot(path="scratch/yt_studio_nav_proof.png")
        await context.close()

asyncio.run(test_nav())
