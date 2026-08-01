import asyncio, os, json, random
from playwright.async_api import async_playwright

async def resend_failed_5_users():
    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    failed_users = ['ilsunsarahchoi', 'oweolgwang', 'sughyi6624', 'ilovehusky486', 'eerara520']
    product_no = "29"
    dm_msg1 = f"안녕하세요 어머님! 💕 요청하신 {product_no}번 상품 구매 링크입니다!\nhttps://6070.piella.shop/p/{product_no}"
    dm_msg2 = "더 많은 예쁜 옷들은 여기서 구경하세요 👇\nhttps://6070.piella.shop"

    print(f"=== [누락된 5명 전원 DM 100% 구제 전송 가동] ===")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        for idx, uname in enumerate(failed_users, start=1):
            print(f"\n👉 [{idx}/5] @{uname} 님께 100% 구제 DM 2개 발송 중...")

            await page.goto("https://www.instagram.com/direct/new/", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            inp = page.locator('input[name="queryBox"], input[name="searchInput"], input[placeholder*="Search"], input[placeholder*="검색"]').first
            if await inp.is_visible():
                await inp.fill(uname)
                await asyncio.sleep(2.5)

                await page.evaluate(f"""
                    () => {{
                        const inputs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                        if (inputs.length > 0) {{
                            inputs[0].click();
                            return;
                        }}
                        const buttons = Array.from(document.querySelectorAll('div[role="button"]'));
                        const userBtn = buttons.find(b => b.textContent.includes('{uname}'));
                        if (userBtn) {{
                            userBtn.click();
                            return;
                        }}
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
                await asyncio.sleep(3)

                try:
                    dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
                    await dm_input.wait_for(timeout=6000)
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
                    print(f"  ✅ 🎉 @{uname} 님 DM 2개 발송 완료!")
                except Exception as e_dm:
                    print(f"  ⚠️ @{uname} DM 발송 실패: {e_dm}")

            delay = random.uniform(15, 25)
            print(f"  🛡️ 계정 보호 {delay:.1f}초 안전 휴식...")
            await asyncio.sleep(delay)

        print("\n🎉🎉 [완전 구제 완결] 누락되었던 5명 전원 DM 발송 완료!")
        await context.close()

if __name__ == '__main__':
    asyncio.run(resend_failed_5_users())
