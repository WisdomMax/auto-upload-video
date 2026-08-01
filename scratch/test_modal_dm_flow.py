import asyncio, os
from playwright.async_api import async_playwright

async def test_native_modal_type():
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
        print('=== [Native Modal Type DM Flow Test] ===')
        await page.goto('https://www.instagram.com/direct/inbox/', wait_until='domcontentloaded')
        await asyncio.sleep(4)

        # 1. Click compose new message icon
        await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('svg[aria-label="새 메시지"], svg[aria-label="New message"], a[href="/direct/new/"]'));
                if (btns.length > 0) {
                    let p = btns[0];
                    for (let i = 0; i < 3; i++) { if (p.parentElement) p = p.parentElement; }
                    p.click();
                }
            }
        """)
        await asyncio.sleep(2)

        # 2. Focus input inside dialog and type username
        await page.evaluate("""
            () => {
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return;
                const inp = dialog.querySelector('input');
                if (inp) inp.focus();
            }
        """)
        await page.keyboard.type(uname, delay=100)
        await asyncio.sleep(3)

        # 3. Check search results in dialog
        opts = await page.evaluate("""
            () => {
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return [];
                const rows = Array.from(dialog.querySelectorAll('div[role="button"], label, div[aria-selected]'));
                return rows.map(r => r.textContent.trim()).filter(t => t.length > 0).slice(0, 10);
            }
        """)
        print('Search Results in Dialog:', opts)

        # 4. Click the search result option
        clicked_opt = await page.evaluate(f"""
            () => {{
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return false;
                const rows = Array.from(dialog.querySelectorAll('div[role="button"], label, div[aria-selected]'));
                const match = rows.find(r => r.textContent.includes('{uname}'));
                if (match) {{
                    match.click();
                    return true;
                }}
                if (rows.length > 0) {{
                    rows[0].click();
                    return true;
                }}
                return false;
            }}
        """)
        print('Option clicked:', clicked_opt)
        await asyncio.sleep(1.5)

        # 5. Click Next / Chat button
        clicked_chat = await page.evaluate("""
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
        print('Chat button clicked:', clicked_chat)
        await asyncio.sleep(3)

        dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
        print('DM Input Ready:', await dm_input.is_visible())

        await context.close()

if __name__ == '__main__':
    asyncio.run(test_native_modal_type())
