import asyncio, os, database
from playwright.async_api import async_playwright

async def run_cookie_reply():
    print("=== 28번 릴스 대댓글 + DM 소급 발송 ===")
    
    username = "momdad_style"
    password = "kim998@@"
    
    item28 = database.get_item_by_product_no(28)
    coupang_link = item28.get("short_url") or item28.get("coupang_url")
    catalog_link = "https://6070.piella.shop/p/28"
    
    reply_text = "안녕하세요! DM으로 링크 보내드렸습니다."
    dm_text = f"안녕하세요! 요청하신 28번 상품 쿠팡 구매 링크입니다.\n{coupang_link}\n\n더 많은 상품은 여기서 확인하세요:\n{catalog_link}"

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

        # 1. 28번 릴스 진입
        url_28 = "https://www.instagram.com/p/DbAkcJDE7dt/"
        print("1. 28번 릴스 진입...")
        await page.goto(url_28, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await page.evaluate("window.scrollBy(0, 400)")
        await asyncio.sleep(2)

        # 2. 댓글 작성자 목록 수집
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
        print(f"댓글 작성자 {len(commenter_hrefs)}명: {commenter_hrefs}")

        # 3. 대댓글 작성
        reply_btn = await page.query_selector("text='답글 달기'") or await page.query_selector("text='Reply'")
        if reply_btn:
            print("대댓글 작성 중...")
            await reply_btn.click(force=True)
            await asyncio.sleep(2)
            input_box = await page.query_selector("textarea") or await page.query_selector("div[role='textbox']")
            if input_box:
                await input_box.click()
                await asyncio.sleep(0.5)
                await input_box.fill(reply_text)
                await asyncio.sleep(1)
                post_btn = await page.query_selector("text='게시'") or await page.query_selector("text='Post'")
                if post_btn:
                    await post_btn.click(force=True)
                    await asyncio.sleep(3)
                    print("[성공] 대댓글 작성 완료!")

        # 4. 첫 번째 댓글 작성자에게 팔로우
        if not commenter_hrefs:
            print("댓글 작성자를 찾지 못했습니다.")
            await context.close()
            return

        target_href = commenter_hrefs[0]
        target_username = target_href.strip("/")
        profile_url = f"https://www.instagram.com{target_href}"

        print(f"프로필 이동: {profile_url}")
        await page.goto(profile_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        follow_btn = await page.query_selector("button:has-text('Follow')") or await page.query_selector("button:has-text('팔로우')")
        if follow_btn:
            print("팔로우 클릭!")
            await follow_btn.click()
            await asyncio.sleep(2)
            print("[성공] 팔로우 완료!")
        else:
            print("이미 팔로우 중")

        # 5. DM 전송: inbox 페이지 이동 후 compose
        print(f"DM 전송 시도: @{target_username}")
        await page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        compose_btn = await page.query_selector("svg[aria-label='새 메시지'], svg[aria-label='New message'], a[href='/direct/new/']")
        if compose_btn:
            await compose_btn.click()
            await asyncio.sleep(2)

        print(f"DM 수신자 검색: @{target_username}")
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

        print("모달 내 [role=option] 클릭 및 Chat 버튼 클릭 중...")
        chat_opened = await page.evaluate(f"""
            async () => {{
                const dialog = document.querySelector('div[role="dialog"]');
                if (!dialog) return false;
                
                // 1. role="option" 클릭
                const opt = dialog.querySelector('div[role="option"]');
                if (opt) {{
                    opt.click();
                }} else {{
                    const checkInput = dialog.querySelector('input[type="checkbox"], input[type="radio"]');
                    if (checkInput) checkInput.click();
                }}
                
                await new Promise(r => setTimeout(r, 1500));
                
                // 2. role="button" text="Chat" 클릭
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
        
        print(f"Chat 버튼 처리 결과: {chat_opened}")
        await asyncio.sleep(3)
        await page.screenshot(path=os.path.join(os.path.dirname(__file__), "ig_dm_chat_opened.png"))

        print("DM 메시지 입력창 탐색 중...")
        dm_sent = await page.evaluate(f"""
            async () => {{
                const selectors = [
                    'div[aria-label*="Message"]',
                    'div[aria-label*="메시지"]',
                    'div[contenteditable="true"]',
                    'p[data-lexical-editor="true"]',
                    'textarea'
                ];
                
                let inputEl = null;
                for (const sel of selectors) {{
                    const el = document.querySelector(sel);
                    if (el && el.offsetWidth > 0) {{
                        inputEl = el;
                        break;
                    }}
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
            print("메시지 입력 완료! 엔터키 전송 중...")
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)
            done_ss = os.path.join(os.path.dirname(__file__), "ig_dm_done.png")
            await page.screenshot(path=done_ss)
            print(f"[성공] DM 링크 전송 완료! 결과 캡처: {done_ss}")
        else:
            print("[경고] DM 입력창을 찾지 못했습니다.")
            await page.screenshot(path=os.path.join(os.path.dirname(__file__), "ig_dm_err.png"))

        await context.close()

if __name__ == "__main__":
    asyncio.run(run_cookie_reply())
