import asyncio, os
from playwright.async_api import async_playwright

async def test_pure_url_send():
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
        prod_no = '29'

        msg1 = f"안녕하세요 어머님! 💕 요청하신 {prod_no}번 상품 구매 링크입니다!"
        msg2 = f"https://6070.piella.shop/p/{prod_no}"
        msg3 = f"https://6070.piella.shop"

        print(f"=== [순수 링크 독자 발송(Pure URL Only) DM 테스트: @{uname}] ===")
        await page.goto("https://www.instagram.com/direct/t/104188580976706/", wait_until="domcontentloaded")
        await asyncio.sleep(4)

        dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
        if await dm_input.is_visible():
            # 1. 안내 메시지 발송
            await dm_input.click()
            await page.keyboard.type(msg1)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)

            # 2. 100% PURE 상품 링크만 단독 발송
            await dm_input.click()
            await page.keyboard.type(msg2)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)

            # 3. 100% PURE 메인 카탈로그 링크만 단독 발송
            await dm_input.click()
            await page.keyboard.type(msg3)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)

            print("🎉🎉 [성공] 순수 링크 100% 단독 메시지 분리 발송 완료!")

        await context.close()

if __name__ == '__main__':
    asyncio.run(test_pure_url_send())
