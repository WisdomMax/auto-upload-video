import asyncio, os, database
from playwright.async_api import async_playwright

async def run_perfect_batch():
    print("=== [인스타그램 소급 DM 정밀 전송 - 메시지 2개 분리 전송] ===")
    database.init_db()

    product_no = 28
    # 1. 쿠팡 직행 링크 (깔끔한 28번 상세)
    product_link = f"https://6070.piella.shop/p/{product_no}"
    # 2. 홈페이지 카탈로그 링크 (메인 몰 주소만)
    catalog_link = "https://6070.piella.shop"
    
    # 두 개의 별도 메시지로 분리
    dm_msg_1 = f"안녕하세요! 요청하신 {product_no}번 상품 구매 링크입니다 💕\n{product_link}"
    dm_msg_2 = f"더 많은 상품은 여기서 확인하세요 👇\n{catalog_link}"

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

        print(f"📋 추출된 소급 대상 {len(commenters)}명: {[c[1] for c in commenters]}")

        for idx, (target_href, display_name) in enumerate(commenters, start=1):
            target_username = target_href.strip("/")
            print(f"\n----------------------------------------")
            print(f"[{idx}/{len(commenters)}] @{target_username} ({display_name}) 님 DM 메시지 분리 발송...")

            # 1. 프로필 이동 & 팔로우
            profile_url = f"https://www.instagram.com{target_href}"
            await page.goto(profile_url, wait_until="domcontentloaded")
            await asyncio.sleep(2.5)

            follow_btn = await page.query_selector("button:has-text('Follow')") or await page.query_selector("button:has-text('팔로우')")
            if follow_btn:
                await follow_btn.click()
                await asyncio.sleep(2)
                print(f"  [1/3] ➕ 팔로우 클릭 완료")
            else:
                print(f"  [1/3] ℹ️ 이미 팔로우 상태")

            # 2. DM 대화함 진입
            await page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            user_inbox = page.locator(f"span:has-text('{target_username}'), span:has-text('{display_name}')").first
            found_inbox = False
            try:
                if await user_inbox.is_visible():
                    await user_inbox.click()
                    await asyncio.sleep(2)
                    found_inbox = True
            except:
                pass

            if not found_inbox:
                compose_btn = await page.query_selector("svg[aria-label='새 메시지'], svg[aria-label='New message'], a[href='/direct/new/']")
                if compose_btn:
                    await compose_btn.click()
                    await asyncio.sleep(2)

                await page.evaluate(f"""
                    () => {{
                        const inp = document.querySelector('div[role="dialog"] input, input[name="queryBox"]');
                        if (inp) {{
                            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                            nativeSetter.call(inp, '{target_username}');
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}
                """)
                await asyncio.sleep(2.5)

                await page.evaluate(f"""
                    async () => {{
                        const dialog = document.querySelector('div[role="dialog"]');
                        if (!dialog) return;
                        const opt = dialog.querySelector('div[role="option"]');
                        if (opt) opt.click();
                        await new Promise(r => setTimeout(r, 1000));
                        const chatBtn = Array.from(dialog.querySelectorAll('div[role="button"], button')).find(el => {{
                            const txt = el.textContent.trim();
                            return (txt === 'Chat' || txt === 'Next' || txt === '채팅' || txt === '다음') && el.offsetWidth > 0;
                        }});
                        if (chatBtn) chatBtn.click();
                    }}
                """)
                await asyncio.sleep(3)

            # 3. 메시지 1 전송 (28번 상품 직행 링크)
            try:
                input_box = page.locator('div[aria-label*="Message"], div[aria-label*="메시지"], div[contenteditable="true"], p[data-lexical-editor="true"]').first
                await input_box.wait_for(timeout=6000)
                await input_box.click()
                await asyncio.sleep(0.5)
                await page.keyboard.type(dm_msg_1)
                await asyncio.sleep(1)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                print(f"  [2/3] ✅ 메시지1 (쿠팡 상품 직행 링크) 발송 완료!")

                # 4. 메시지 2 전송 (홈페이지 메인 몰 링크)
                await input_box.click()
                await asyncio.sleep(0.5)
                await page.keyboard.type(dm_msg_2)
                await asyncio.sleep(1)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                print(f"  [3/3] ✅ 메시지2 (홈페이지 메인 링크) 발송 완료!")

            except Exception as e_dm:
                print(f"  ⚠️ DM 입력/전송 오류: {e_dm}")

            await asyncio.sleep(2.5)

        print(f"\n🎉 [완료] 과거 댓글 작성자 전체 소급 2개 분리 DM 전송 완료!")
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_perfect_batch())
