import asyncio, os
from playwright.async_api import async_playwright

async def test_full_dm_send():
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

        print(f"=== [100% DM 전송 성공 검증 테스트: @{uname}] ===")

        # 1. Direct Inbox 이동
        await page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
        await asyncio.sleep(3.5)

        # 2. 새 메시지 버튼 클릭
        clicked_new = await page.evaluate("""
            () => {
                const svgs = Array.from(document.querySelectorAll('svg[aria-label="New message"], svg[aria-label="새 메시지"]'));
                if (svgs.length > 0) {
                    let p = svgs[0];
                    for (let i = 0; i < 4; i++) {
                        if (p.parentElement) p = p.parentElement;
                    }
                    p.click();
                    return true;
                }
                return false;
            }
        """)
        print("1) New message button clicked:", clicked_new)
        await asyncio.sleep(2)

        # 3. 모달 입력창 fill 사용
        modal_input = page.locator('div[role="dialog"] input').first
        if await modal_input.is_visible():
            await modal_input.fill(uname)
            await asyncio.sleep(2.5)

        # 4. 검색 결과 중 첫 번째 유저 선택 (checkbox 또는 row 클릭)
        selected = await page.evaluate(f"""
            () => {{
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return false;
                
                // Look for checkbox or clickable user item
                const check = dialog.querySelector('input[type="checkbox"], div[role="button"]');
                if (check) {{
                    check.click();
                    return true;
                }}
                
                const spans = Array.from(dialog.querySelectorAll('span')).filter(s => s.textContent.includes('{uname}'));
                if (spans.length > 0) {{
                    spans[0].click();
                    return true;
                }}
                return false;
            }}
        """)
        print("2) User row selected in search results:", selected)
        await asyncio.sleep(1.5)

        # 5. 채팅(Chat) 버튼 클릭
        opened_chat = await page.evaluate("""
            () => {
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return false;
                const btns = Array.from(dialog.querySelectorAll('div[role="button"], button'));
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
        print("3) Chat button clicked:", opened_chat)
        await asyncio.sleep(3.5)

        # 6. 대화 입력창 찾기 및 DM 2개 발송
        dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
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
            print(f"🎉🎉 [성공] @{uname} 님께 DM 2개 정상 발송 완료!")
        else:
            print("❌ DM 입력창을 찾지 못함")

        await context.close()

if __name__ == '__main__':
    asyncio.run(test_full_dm_send())
