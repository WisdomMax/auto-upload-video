import asyncio, os, json
from playwright.async_api import async_playwright

async def inspect_modal_selectors():
    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        await page.goto('https://www.instagram.com/direct/inbox/', wait_until='domcontentloaded')
        await asyncio.sleep(4)

        # Click new message button
        await page.evaluate("""
            () => {
                const btn = document.querySelector('svg[aria-label="새 메시지"], svg[aria-label="New message"], a[href="/direct/new/"]');
                if (btn) {
                    let p = btn;
                    for (let i = 0; i < 3; i++) { if (p.parentElement) p = p.parentElement; }
                    p.click();
                }
            }
        """)
        await asyncio.sleep(2.5)

        # Get HTML of dialog modal
        dialog_info = await page.evaluate("""
            () => {
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return 'NO DIALOG FOUND';
                const inputs = Array.from(dialog.querySelectorAll('input')).map(i => ({
                    name: i.getAttribute('name'),
                    placeholder: i.getAttribute('placeholder'),
                    type: i.getAttribute('type'),
                    className: i.className
                }));
                return {
                    dialogHTML: dialog.innerHTML.slice(0, 500),
                    inputs: inputs
                };
            }
        """)

        print("=== DIALOG INSPECTION ===")
        print(json.dumps(dialog_info, ensure_ascii=False, indent=2))

        await context.close()

if __name__ == '__main__':
    asyncio.run(inspect_modal_selectors())
