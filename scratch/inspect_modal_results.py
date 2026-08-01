import asyncio, os, json
from playwright.async_api import async_playwright

async def inspect_dialog_options():
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
        await page.goto('https://www.instagram.com/direct/inbox/', wait_until='domcontentloaded')
        await asyncio.sleep(3.5)

        await page.evaluate("""
            () => {
                const svgs = Array.from(document.querySelectorAll('svg[aria-label="New message"], svg[aria-label="새 메시지"]'));
                if (svgs.length > 0) {
                    let p = svgs[0];
                    for (let i = 0; i < 4; i++) { if (p.parentElement) p = p.parentElement; }
                    p.click();
                }
            }
        """)
        await asyncio.sleep(2)

        modal_input = page.locator('div[role="dialog"] input').first
        if await modal_input.is_visible():
            await modal_input.fill(uname)
            await asyncio.sleep(3.5)

        info = await page.evaluate("""
            () => {
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return 'NO DIALOG';
                const allElements = Array.from(dialog.querySelectorAll('*'));
                return allElements.map(e => ({
                    tag: e.tagName,
                    role: e.getAttribute('role'),
                    text: e.textContent.trim().slice(0, 40),
                    className: e.className.slice(0, 30)
                })).filter(e => e.text.length > 0).slice(0, 30);
            }
        """)

        print("=== DIALOG ELEMENTS AFTER SEARCH ===")
        print(json.dumps(info, ensure_ascii=False, indent=2))

        await context.close()

if __name__ == '__main__':
    asyncio.run(inspect_dialog_options())
