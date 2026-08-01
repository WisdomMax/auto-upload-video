import asyncio, os, json
from playwright.async_api import async_playwright

async def inspect_comment_buttons():
    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        reel_url = "https://www.instagram.com/momdad_style/reel/DbWg-WlkdhL/"
        print(f"=== [릴스 댓글 비공개 답장 버튼 DOM 요소 정밀 탐색: {reel_url}] ===")
        await page.goto(reel_url, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # Inspect all buttons and links in comment section
        info = await page.evaluate("""
            () => {
                const svgs = Array.from(document.querySelectorAll('svg'));
                return svgs.map(s => ({
                    ariaLabel: s.getAttribute('aria-label'),
                    parentTag: s.parentElement ? s.parentElement.tagName : null,
                    parentRole: s.parentElement ? s.parentElement.getAttribute('role') : null,
                    outerHTML: s.outerHTML.slice(0, 150)
                })).filter(s => s.ariaLabel);
            }
        """)

        print("=== SVGs ON REEL PAGE ===")
        print(json.dumps(info, ensure_ascii=False, indent=2))

        await context.close()

if __name__ == '__main__':
    asyncio.run(inspect_comment_buttons())
