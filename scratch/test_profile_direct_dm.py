import asyncio, os
from playwright.async_api import async_playwright

async def send_dm_via_profile_page():
    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        uname = 'ilovehusky486'
        profile_url = f'https://www.instagram.com/{uname}/'
        print(f"=== [@{uname} 프로필 직접 이동 DM 전송 테스트] ===")
        await page.goto(profile_url, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # Look for Message button on profile page
        msg_btn = page.locator("div[role='button']:has-text('Message'), div[role='button']:has-text('메시지 보내기'), button:has-text('Message'), button:has-text('메시지 보내기'), a:has-text('Message')").first
        print("Message button on profile visible:", await msg_btn.is_visible())

        if await msg_btn.is_visible():
            await msg_btn.click()
            await asyncio.sleep(4)
            print("Current URL after profile message click:", page.url)

            dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
            print("DM Input visible:", await dm_input.is_visible())

            if await dm_input.is_visible():
                dm_text = "안녕하세요! 요청하신 29번 상품 링크입니다 💕 https://6070.piella.shop/p/29"
                await dm_input.click()
                await asyncio.sleep(0.5)
                await page.keyboard.type(dm_text)
                await asyncio.sleep(1)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                print(f"🎉 프로필 메시지 버튼으로 @{uname} 님께 DM 직접 전송 완료!")

        await context.close()

if __name__ == '__main__':
    asyncio.run(send_dm_via_profile_page())
