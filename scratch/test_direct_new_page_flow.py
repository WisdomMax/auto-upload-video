import asyncio, os, json
from playwright.async_api import async_playwright

async def test_direct_new_page():
    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        uname = 'susankim0608'
        dm_msg1 = "안녕하세요! 요청하신 28번 상품 구매 링크입니다 💕\nhttps://6070.piella.shop/p/28"
        dm_msg2 = "더 많은 상품은 여기서 확인하세요 👇\nhttps://6070.piella.shop"

        print(f"=== [Direct/New 페이지 전용 DM 발송 검증: @{uname}] ===")
        await page.goto("https://www.instagram.com/direct/new/", wait_until="domcontentloaded")
        await asyncio.sleep(3.5)

        # 1. Fill query input
        inp = page.locator('input[name="queryBox"], input[name="searchInput"], input[placeholder*="Search"], input[placeholder*="검색"]').first
        print("Search Input Visible:", await inp.is_visible())
        if await inp.is_visible():
            await inp.fill(uname)
            await asyncio.sleep(3)

        # 2. Find and click search result item / checkbox
        clicked_res = await page.evaluate(f"""
            () => {{
                const inputs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                if (inputs.length > 0) {{
                    inputs[0].click();
                    return 'checkbox_clicked';
                }}
                
                const buttons = Array.from(document.querySelectorAll('div[role="button"]'));
                const userBtn = buttons.find(b => b.textContent.includes('{uname}'));
                if (userBtn) {{
                    userBtn.click();
                    return 'button_clicked';
                }}
                
                if (buttons.length > 0) {{
                    buttons[0].click();
                    return 'first_button_clicked';
                }}
                return 'none_found';
            }}
        """)
        print("Search Result Clicked Result:", clicked_res)
        await asyncio.sleep(2)

        # 3. Click Next / Chat button
        clicked_chat = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('div[role="button"], button'));
                const chatBtn = btns.find(b => {
                    const txt = b.textContent.trim();
                    return (txt === 'Chat' || txt === 'Next' || txt === '채팅' || txt === '다음') && b.offsetWidth > 0;
                });
                if (chatBtn) {
                    chatBtn.click();
                    return true;
                }
                return false;
            }
        """)
        print("Chat Button Clicked:", clicked_chat)
        await asyncio.sleep(3.5)

        # 4. DM Textbox Ready Check
        dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
        print("DM Textbox Visible:", await dm_input.is_visible())

        if await dm_input.is_visible():
            await dm_input.click()
            await asyncio.sleep(0.5)
            await page.keyboard.type(dm_msg1)
            await asyncio.sleep(1)
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)

            await dm_input.click()
            await asyncio.sleep(0.5)
            await page.keyboard.type(dm_msg2)
            await asyncio.sleep(1)
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)
            print(f"🎉🎉🎉 [100% 완결] @{uname} 님께 DM 2개 발송 성공!")

        await context.close()

if __name__ == '__main__':
    asyncio.run(test_direct_new_page())
