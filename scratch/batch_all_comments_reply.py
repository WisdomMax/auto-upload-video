import asyncio, os, re, database
from playwright.async_api import async_playwright

async def batch_process_comments():
    print("=== [인스타그램 릴스 과거 댓글 전체 소급 대댓글 & DM 자동 발송] ===")
    
    database.init_db()
    
    # 28번 상품 정보 조회
    item28 = database.get_item_by_product_no(28)
    coupang_link = item28.get("short_url") or item28.get("coupang_url") or "https://www.coupang.com"
    catalog_link = "https://6070.piella.shop/p/28"
    
    reply_text = "안녕하세요! DM으로 링크 보내드렸습니다 💕"
    dm_text = f"안녕하세요! 요청하신 28번 상품 쿠팡 구매 링크입니다 💕\n{coupang_link}\n\n더 많은 상품은 여기서 확인하세요 👇\n{catalog_link}"

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
        print(f"\n1. 릴스 진입: {url_28}")
        await page.goto(url_28, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 댓글 아이콘 클릭하여 댓글 목록 펼치기
        comment_icon = await page.query_selector("svg[aria-label='댓글'], svg[aria-label='Comment']")
        if comment_icon:
            await comment_icon.click()
            await asyncio.sleep(2)
        
        # 댓글 스크롤 내려서 많이 불러오기
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(1)

        # 댓글 작성자 프로필 링크 수집
        all_links = await page.query_selector_all("a[href]")
        commenter_hrefs = []
        seen = set()
        for lnk in all_links:
            h = await lnk.get_attribute("href")
            t = (await lnk.inner_text()).strip()
            if (h and h.startswith("/") and "p/" not in h and "reels/" not in h
                    and "explore" not in h and "legal" not in h and "popular" not in h
                    and "web/" not in h and "accounts/" not in h
                    and t and "momdad_style" not in h and h not in seen and len(t) > 1):
                commenter_hrefs.append(h)
                seen.add(h)

        print(f"📋 소급 대상 사용자 총 {len(commenter_hrefs)}명 포착: {commenter_hrefs}")

        # 전체 사용자 순회 및 발송
        success_count = 0
        for idx, target_href in enumerate(commenter_hrefs, start=1):
            target_username = target_href.strip("/")
            print(f"\n----------------------------------------")
            print(f"[{idx}/{len(commenter_hrefs)}] @{target_username} 님 처리 시작...")

            # A. 프로필 이동 & 팔로우
            profile_url = f"https://www.instagram.com{target_href}"
            await page.goto(profile_url, wait_until="domcontentloaded")
            await asyncio.sleep(2.5)

            follow_btn = await page.query_selector("button:has-text('Follow')") or await page.query_selector("button:has-text('팔로우')")
            if follow_btn:
                await follow_btn.click()
                await asyncio.sleep(2)
                print(f"  [1/3] ➕ @{target_username} 팔로우 클릭 완료!")
            else:
                print(f"  [1/3] ℹ️ @{target_username} 이미 팔로우 중")

            # B. DM 전송
            await page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
            await asyncio.sleep(2.5)

            compose_btn = await page.query_selector("svg[aria-label='새 메시지'], svg[aria-label='New message'], a[href='/direct/new/']")
            if compose_btn:
                await compose_btn.click()
                await asyncio.sleep(2)

            # 검색창 입력
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
            await asyncio.sleep(2)

            # 모달 내 option 클릭 & Chat 버튼 클릭
            chat_opened = await page.evaluate(f"""
                async () => {{
                    const dialog = document.querySelector('div[role="dialog"]');
                    if (!dialog) return false;
                    
                    const opt = dialog.querySelector('div[role="option"]');
                    if (opt) {{
                        opt.click();
                    }} else {{
                        const checkInput = dialog.querySelector('input[type="checkbox"], input[type="radio"]');
                        if (checkInput) checkInput.click();
                    }}
                    
                    await new Promise(r => setTimeout(r, 1200));
                    
                    const chatBtn = Array.from(dialog.querySelectorAll('div[role="button"], button')).find(el => {{
                        const txt = el.textContent.trim();
                        return (txt === 'Chat' || txt === 'Next' || txt === '채팅' || txt === '다음') && el.offsetWidth > 0;
                    }});
                    
                    if (chatBtn) {{
                        chatBtn.click();
                        return true;
                    }}
                    return false;
                }}
            """)
            await asyncio.sleep(2.5)

            # DM 입력 & 전송
            dm_sent = await page.evaluate(f"""
                async () => {{
                    const selectors = ['div[aria-label*="Message"]', 'div[aria-label*="메시지"]', 'div[contenteditable="true"]', 'p[data-lexical-editor="true"]', 'textarea'];
                    let inputEl = null;
                    for (const sel of selectors) {{
                        const el = document.querySelector(sel);
                        if (el && el.offsetWidth > 0) {{ inputEl = el; break; }}
                    }}
                    if (!inputEl) return false;
                    inputEl.focus();
                    if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {{
                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeSetter.call(inputEl, `{dm_text}`);
                        inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }} else {{
                        inputEl.textContent = `{dm_text}`;
                        inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                    return true;
                }}
            """)

            if dm_sent:
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                print(f"  [2/3] 📩 @{target_username} 님에게 DM 구매링크 발송 완료!")
            else:
                print(f"  [2/3] ⚠️ @{target_username} DM 입력창 탐색 미완료")

            # 안전 대기
            success_count += 1
            await asyncio.sleep(2)

        print(f"\n🎉 [소급 완료] 총 {len(commenter_hrefs)}명 중 {success_count}명에게 팔로우 및 DM 발송 작업을 완료했습니다!")
        await context.close()

if __name__ == "__main__":
    asyncio.run(batch_process_comments())
