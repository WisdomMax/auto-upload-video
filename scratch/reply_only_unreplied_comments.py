import asyncio, os, database
from playwright.async_api import async_playwright

async def reply_unreplied_comments():
    print("=== [미작성 댓글 대상 대댓글 달기 작업 (DM 중복 방지)] ===")
    database.init_db()

    reply_text = "안녕하세요! DM으로 링크 보내드렸습니다 💕"
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
        print(f"\n1. 28번 릴스 진입: {url_28}")
        await page.goto(url_28, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        comment_icon = await page.query_selector("svg[aria-label='댓글'], svg[aria-label='Comment']")
        if comment_icon:
            await comment_icon.click()
            await asyncio.sleep(2)
        
        for _ in range(4):
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(1)

        # 댓글 작성자 추출
        all_links = await page.query_selector_all("a[href]")
        commenters = []
        seen = set()
        for lnk in all_links:
            h = await lnk.get_attribute("href")
            t = (await lnk.inner_text()).strip()
            if (h and h.startswith("/") and "p/" not in h and "reels/" not in h
                    and "explore" not in h and "legal" not in h and "popular" not in h
                    and "web/" not in h and "accounts/" not in h
                    and t and "momdad_style" not in h and h not in seen and len(t) > 1):
                commenters.append((h, t))
                seen.add(h)

        print(f"📋 스캔 대상 댓글 작성자 {len(commenters)}명: {[c[1] for c in commenters]}")

        success_comments = 0
        skipped_comments = 0

        for idx, (target_href, display_name) in enumerate(commenters, start=1):
            target_username = target_href.strip("/")
            print(f"\n[{idx}/{len(commenters)}] @{target_username} 님 댓글 답글 여부 검사 중...")

            # 릴스 페이지에서 해당 사용자 댓글 찾기
            comment_status = await page.evaluate(f"""
                async () => {{
                    const replyEls = Array.from(document.querySelectorAll('*')).filter(el => 
                        (el.textContent.trim() === '답글 달기' || el.textContent.trim() === 'Reply') && el.offsetWidth > 0
                    );
                    
                    for (const rel of replyEls) {{
                        let container = rel;
                        for (let i = 0; i < 8; i++) {{
                            if (container.parentElement) container = container.parentElement;
                        }}
                        const userLink = Array.from(container.querySelectorAll('a[href]')).find(a => {{
                            const h = a.getAttribute('href');
                            return h && h.includes('{target_username}');
                        }});
                        
                        if (userLink) {{
                            const textContent = container.textContent;
                            if (textContent.includes('DM으로 링크 보내드렸습니다')) {{
                                return 'already_replied';
                            }}
                            rel.click();
                            return 'clicked';
                        }}
                    }}
                    return 'not_found';
                }}
            """)

            if comment_status == 'clicked':
                await asyncio.sleep(1.5)
                input_box = await page.query_selector("textarea") or await page.query_selector("div[role='textbox']")
                if input_box:
                    await input_box.click()
                    await asyncio.sleep(0.5)
                    await input_box.fill(reply_text)
                    await asyncio.sleep(1)
                    post_btn = await page.query_selector("text='게시'") or await page.query_selector("text='Post'")
                    if post_btn:
                        await post_btn.click(force=True)
                        await asyncio.sleep(2.5)
                        print(f"  ✅ @{target_username} 님 댓글에 답글 작성 완료!")
                        success_comments += 1
            elif comment_status == 'already_replied':
                print(f"  ℹ️ @{target_username} 님 댓글은 이미 답글이 달림 (중복 작성 방지)")
                skipped_comments += 1
            else:
                print(f"  ⚠️ @{target_username} 님 댓글 위치 탐색 불가")

            await asyncio.sleep(1)

        print(f"\n🎉 [완료] 대댓글 신규 작성 {success_comments}건, 기존 답글 완료 건 {skipped_comments}건 (DM 중복 전송 없이 무사히 마무리되었습니다!)")
        await context.close()

if __name__ == "__main__":
    asyncio.run(reply_unreplied_comments())
