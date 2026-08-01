import asyncio, os
from playwright.async_api import async_playwright

async def test_youtube_comments_browser():
    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print('=== [유튜브 채널 접속 및 실시간 댓글 조회 테스트] ===')
        channel_url = 'https://www.youtube.com/channel/UC-bYx0BTsO133T_jRL96o4Q/videos'
        print(f'1. 채널 동영상 목록 접속 중: {channel_url}')
        await page.goto(channel_url, wait_until='domcontentloaded')
        await asyncio.sleep(4)

        video_links = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href*="/watch?v="], a[href*="/shorts/"]'));
                return Array.from(new Set(links.map(l => l.getAttribute('href')))).slice(0, 5);
            }
        """)

        print(f'📋 최신 동영상/숏츠 {len(video_links)}개 포착 성공!')
        for idx, v in enumerate(video_links, start=1):
            print(f'  [{idx}] https://www.youtube.com{v}')

        if video_links:
            test_vurl = f'https://www.youtube.com{video_links[0]}'
            print(f'\n2. 최신 동영상 접속 댓글 스캔 중: {test_vurl}')
            await page.goto(test_vurl, wait_until='domcontentloaded')
            await asyncio.sleep(4)

            await page.evaluate('window.scrollTo(0, 700)')
            await asyncio.sleep(3)

            comments = await page.evaluate("""
                () => {
                    const els = Array.from(document.querySelectorAll('#content-text, #comments #content-text'));
                    return els.map(e => e.textContent.trim()).filter(t => t.length > 0).slice(0, 10);
                }
            """)

            print(f'💬 동영상 내부 댓글 스캔 결과 (총 {len(comments)}개 감지):')
            for c_idx, c in enumerate(comments, start=1):
                print(f'  [{c_idx}] "{c}"')

        await context.close()

if __name__ == '__main__':
    asyncio.run(test_youtube_comments_browser())
