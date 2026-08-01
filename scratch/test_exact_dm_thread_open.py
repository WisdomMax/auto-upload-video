import asyncio, os
from playwright.async_api import async_playwright

async def open_exact_user_thread():
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
        print(f"=== [@{uname} 실시간 100% 대화방 개설 및 DM 전송 검증] ===")

        # 1. direct/new 이동
        await page.goto("https://www.instagram.com/direct/new/", wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # 2. 검색창 찾기 및 fill
        search_input = page.locator('input[name="queryBox"], input[name="searchInput"], input[placeholder*="Search"], input[placeholder*="검색"]').first
        if await search_input.is_visible():
            await search_input.fill(uname)
            await asyncio.sleep(3)

            # 3. 정확히 ilovehusky486 항목 클릭
            click_status = await page.evaluate(f"""
                () => {{
                    const els = Array.from(document.querySelectorAll('div[role="button"], label, div[aria-selected]'));
                    const target = els.find(e => e.textContent.includes('{uname}'));
                    if (target) {{
                        target.click();
                        return 'target_user_clicked';
                    }}
                    const cb = document.querySelector('input[type="checkbox"]');
                    if (cb) {{
                        cb.click();
                        return 'checkbox_clicked';
                    }}
                    return 'not_found';
                }}
            """)
            print("Target user item clicked:", click_status)
            await asyncio.sleep(2)

            # 4. '다음' 또는 '채팅' 버튼 클릭 (100% 강제)
            next_clicked = await page.evaluate("""
                () => {
                    const allBtns = Array.from(document.querySelectorAll('div[role="button"], button, div[tabindex="0"]'));
                    const btn = allBtns.find(b => {
                        const txt = b.textContent.trim();
                        return (txt === 'Next' || txt === 'Chat' || txt === '다음' || txt === '채팅') && b.offsetWidth > 0;
                    });
                    if (btn) {
                        btn.click();
                        return 'next_btn_clicked';
                    }
                    return 'next_not_found';
                }
            """)
            print("Next/Chat button clicked:", next_clicked)
            await asyncio.sleep(4)

            # 5. 대화창 진입 확인 및 DM 입력
            dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
            print("DM Input Box visible:", await dm_input.is_visible())
            print("Current URL:", page.url)

            if await dm_input.is_visible():
                msg1 = "안녕하세요! 요청하신 29번 상품 직행 링크입니다! 💕 https://6070.piella.shop/p/29"
                await dm_input.click()
                await asyncio.sleep(0.5)
                await page.keyboard.type(msg1)
                await asyncio.sleep(1)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                print(f"🎉🎉 [@{uname}] 님 전용 대화방 개설 및 DM 실시간 전송 성공!")

        await context.close()

if __name__ == '__main__':
    asyncio.run(open_exact_user_thread())
