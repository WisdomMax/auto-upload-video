import asyncio, os
from playwright.async_api import async_playwright

async def scan_all_channel_videos():
    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        video_ids = ['Fxj0Agi1g1g', 'DKKhbNr9p4I', 'Ipal8L2_Eps', 'pNyF5OYlMoM']
        print(f"=== [유튜브 채널 전체 {len(video_ids)}개 동영상 댓글 스캔 테스트] ===")

        for idx, vid in enumerate(video_ids, start=1):
            url = f"https://www.youtube.com/watch?v={vid}"
            print(f"\n[{idx}/{len(video_ids)}] 🔍 접속 스캔 중: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(3)

            for _ in range(3):
                await page.evaluate("window.scrollTo(0, 800)")
                await asyncio.sleep(1)

            comments = await page.evaluate("""
                () => {
                    const els = Array.from(document.querySelectorAll('#content-text'));
                    return els.map(e => e.textContent.trim()).filter(t => t.length > 0);
                }
            """)

            if comments:
                print(f"  🔥 [{vid}] 댓글 {len(comments)}개 발견!")
                for c_idx, c in enumerate(comments[:5], start=1):
                    print(f"    - [{c_idx}] \"{c}\"")
            else:
                print(f"  ✅ [{vid}] 댓글 없음")

        await context.close()

if __name__ == '__main__':
    asyncio.run(scan_all_channel_videos())
