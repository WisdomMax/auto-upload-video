import asyncio, os
from playwright.async_api import async_playwright

async def live_dm_test():
    uname = 'ilovehusky486'
    prod_no = '29'

    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print(f"=== 🚀 [@{uname} 님 대상 4단계 실시간 DM 발송 라이브 테스트] ===")
        await page.goto("https://www.instagram.com/direct/new/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        inp = page.locator('input[name="queryBox"], input[name="searchInput"], input[placeholder*="Search"], input[placeholder*="검색"]').first
        if await inp.is_visible():
            await inp.fill(uname)
            await asyncio.sleep(2.5)

            await page.evaluate(f"""
                () => {{
                    const inputs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                    if (inputs.length > 0) {{ inputs[0].click(); return; }}
                    const buttons = Array.from(document.querySelectorAll('div[role="button"]'));
                    const userBtn = buttons.find(b => b.textContent.includes('{uname}'));
                    if (userBtn) {{ userBtn.click(); return; }}
                    if (buttons.length > 0) buttons[0].click();
                }}
            """)
            await asyncio.sleep(1.5)

            await page.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll('div[role="button"], button'));
                    const chatBtn = btns.find(b => {
                        const txt = b.textContent.trim();
                        return (txt === 'Chat' || txt === 'Next' || txt === '채팅' || txt === '다음') && b.offsetWidth > 0;
                    });
                    if (chatBtn) chatBtn.click();
                }
            """)
            await asyncio.sleep(3.5)

            dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
            await dm_input.wait_for(timeout=6000)

            # 1. 안내 메시지
            await dm_input.click()
            await page.keyboard.type(f"안녕하세요 어머님! 💕 요청하신 {prod_no}번 상품 구매 링크입니다!")
            await page.keyboard.press("Enter")
            await asyncio.sleep(1.5)

            # 2. PURE 상품 링크
            await dm_input.click()
            await page.keyboard.type(f"https://6070.piella.shop/p/{prod_no}")
            await page.keyboard.press("Enter")
            await asyncio.sleep(1.5)

            # 3. 카탈로그 안내
            await dm_input.click()
            await page.keyboard.type("더 많은 예쁜 옷들은 여기서 구경하세요 👇")
            await page.keyboard.press("Enter")
            await asyncio.sleep(1.5)

            # 4. PURE 카탈로그 링크
            await dm_input.click()
            await page.keyboard.type("https://6070.piella.shop")
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)

            # Take screenshot of the DM chat window as visual proof!
            screenshot_path = "/Users/wisdom/.gemini/antigravity/brain/a0dd2e95-6511-4a02-994e-bb9b211d118e/live_husky_dm_test_proof.png"
            await page.screenshot(path=screenshot_path)
            print(f"🎉🎉 [라이브 테스트 완결] @{uname} 대화방 화면 캡처 저장: {screenshot_path}")

        await context.close()

if __name__ == '__main__':
    asyncio.run(live_dm_test())
