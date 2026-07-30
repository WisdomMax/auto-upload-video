import asyncio, os
from playwright.async_api import async_playwright

async def delete_my_comments():
    print("=== [momdad_style 도배 댓글 100% 자동 즉시 삭제] ===")
    
    user_data_dir = os.path.expanduser("~/.config/ig_stealth_profile")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()

        url_28 = "https://www.instagram.com/p/DbAkcJDE7dt/"
        print(f"1. 28번 릴스 진입: {url_28}")
        await page.goto(url_28, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        deleted_count = 0
        
        for attempt in range(30):
            # 스크롤
            await page.evaluate("""
                () => {
                    const divs = document.querySelectorAll('div');
                    for (const d of divs) {
                        if (d.scrollHeight > d.clientHeight && d.clientHeight > 150) {
                            d.scrollTop = d.scrollHeight;
                        }
                    }
                }
            """)
            await asyncio.sleep(1)

            # momdad_style 이 쓴 "DM으로 링크 보내드렸습니다" 댓글 마우스 오버 및 옵션 버튼 클릭
            del_result = await page.evaluate("""
                async () => {
                    const allSpans = Array.from(document.querySelectorAll('span, a'));
                    const targetComment = allSpans.find(el => 
                        el.textContent.includes('DM으로 링크 보내드렸습니다') && el.offsetWidth > 0
                    );
                    
                    if (!targetComment) return 'no_more';

                    let container = targetComment;
                    for (let i = 0; i < 6; i++) {
                        if (container.parentElement) container = container.parentElement;
                    }

                    // 마우스오버
                    container.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
                    
                    // 점 3개 또는 옵션 버튼 찾기
                    const btns = Array.from(container.querySelectorAll('button, svg, [role="button"]'));
                    for (const b of btns) {
                        const aria = b.getAttribute('aria-label') || '';
                        if (aria.includes('옵션') || aria.includes('More') || aria.includes('Delete') || aria.includes('삭제') || b.tagName === 'svg') {
                            b.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                            return 'clicked';
                        }
                    }
                    
                    return 'not_found_btn';
                }
            """)

            if del_result == 'no_more':
                print("✅ 모든 momdad_style 도배 댓글이 완전히 제거되었습니다!")
                break

            await asyncio.sleep(1.5)
            
            # 모달 팝업에서 '삭제' 클릭
            del_confirm = page.locator("button:has-text('삭제'), button:has-text('Delete'), div[role='button']:has-text('삭제'), div[role='button']:has-text('Delete')").first
            try:
                if await del_confirm.is_visible():
                    await del_confirm.click()
                    deleted_count += 1
                    print(f"  🗑️ [{deleted_count}개째] 도배 댓글 삭제 완료!")
                    await asyncio.sleep(2)
            except Exception as e:
                pass

        await page.screenshot(path="/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/scratch/ig_cleaned_comments.png")
        print(f"\n🎉 총 {deleted_count}개의 도배 댓글을 일괄 삭제했습니다.")
        await context.close()

if __name__ == "__main__":
    asyncio.run(delete_my_comments())
