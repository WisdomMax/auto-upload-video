import asyncio, os
from playwright.async_api import async_playwright

async def inspect_husky_dm():
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
        print(f"=== [@{uname} DM 대화창 현황 정밀 검증] ===")
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
            await asyncio.sleep(4)

            # Extract last messages sent in chat thread
            chat_messages = await page.evaluate("""
                () => {
                    const msgs = Array.from(document.querySelectorAll('div[role="row"], div[data-testid="message_container"], div[class*="html-div"]'));
                    return msgs.map(m => m.textContent.trim()).filter(t => t.length > 0 && (t.includes('piella.shop') || t.includes('상품'))).slice(-5);
                }
            """)
            print(f"Direct 대화창 내 발송된 메시지 기록 ({len(chat_messages)}개 발견):")
            for idx, m in enumerate(chat_messages, start=1):
                print(f"  [{idx}] {m[:100]}")

            # Save screenshot of chat thread
            os.makedirs("scratch", exist_ok=True)
            screenshot_path = os.path.abspath("scratch/husky_dm_chat_proof.png")
            await page.screenshot(path=screenshot_path)
            print(f"📸 대화창 스크린샷 저장 완료: {screenshot_path}")

        await context.close()

if __name__ == '__main__':
    asyncio.run(inspect_husky_dm())
