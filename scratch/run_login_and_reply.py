import asyncio, os, database
from playwright.async_api import async_playwright

async def run_login_and_reply():
    print("=== Playwright Stealth 인스타 자동 로그인 & 28번 대댓글 작성 개시 ===")
    
    username = "momdad_style"
    password = "kim998@@"
    
    item28 = database.get_item_by_product_no(28)
    coupang_link = item28.get("short_url") or item28.get("coupang_url")
    catalog_link = "https://6070.piella.shop/p/28"
    
    reply_text = f"안녕하세요 어머님! 요청하신 28번 상품 상세 정보와 쿠팡 구매 링크입니다 💕 {coupang_link}"
    
    user_data_dir = os.path.expanduser("~/.config/ig_stealth_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=[
                '--disable-blink-features=AutomationControlled',
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # 1. 인스타그램 로그인 페이지 진입
        print("1. 인스타그램 로그인 페이지 접속...")
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # 쿠키 동의 팝업 또는 팝업 버튼 처리
        try:
            cookie_btn = await page.query_selector("button:has-text('Allow'), button:has-text('허용'), button:has-text('동의')")
            if cookie_btn:
                await cookie_btn.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        # 로그인 입력창 대기
        try:
            print("🔑 로그인 입력창 수신 대기...")
            username_input = await page.wait_for_selector("input[name='username'], input[name='email'], input[type='text']", timeout=15000)
            if username_input:
                await username_input.fill(username)
                await page.fill("input[name='password']", password)
                await asyncio.sleep(1)
                
                # 로그인 버튼 클릭
                submit_btn = await page.query_selector("button[type='submit']")
                if submit_btn:
                    await submit_btn.click()
                    print("🚀 로그인 버튼 클릭 완료! 5초 승인 대기 중...")
                    await asyncio.sleep(6)
        except Exception as e_login:
            print(f"⚠️ 로그인 입력 폼 처리 경고: {e_login}")
            ss_err = os.path.join(os.path.dirname(__file__), "ig_login_err.png")
            await page.screenshot(path=ss_err)
            print(f"📸 로그인 시점 스크린샷 저장 완료: {ss_err}")
            
        # 2. 28번 릴스 페이지 진입
        url_28 = "https://www.instagram.com/p/DbAkcJDE7dt/"
        print(f"\n2. 28번 릴스 페이지 진입: {url_28}")
        await page.goto(url_28, wait_until="networkidle")
        await asyncio.sleep(3)
        
        # 스크린샷 캡처로 로그인 후 28번 릴스 상태 점검
        ss_path = os.path.join(os.path.dirname(__file__), "ig_28_logged_in.png")
        await page.screenshot(path=ss_path)
        print(f"📸 로그인 후 28번 릴스 캡처 완료: {ss_path}")
        
        # 3. 답글 달기 버튼 탐색 및 클릭
        reply_btn = await page.query_selector("text='답글 달기'")
        if not reply_btn:
            reply_btn = await page.query_selector("text='Reply'")
            
        if reply_btn:
            print("🎯 '답글 달기' 버튼 포착! 클릭 진행 중...")
            await reply_btn.click()
            await asyncio.sleep(2)
            
            # 입력창 포착
            input_box = await page.query_selector("textarea") or await page.query_selector("div[role='textbox']")
            if input_box:
                print("⌨️ 대댓글 입력창 포착! 대댓글 메시지 타이핑 완료...")
                await input_box.fill(reply_text)
                await asyncio.sleep(1)
                
                # 게시 버튼 클릭
                post_btn = await page.query_selector("text='게시'") or await page.query_selector("text='Post'")
                if post_btn:
                    print("🚀 '게시' 버튼 클릭! 대댓글 최종 작성 전송 완료!")
                    await post_btn.click()
                    await asyncio.sleep(4)
                    
                    # 작성 후 결과 스크린샷
                    res_ss = os.path.join(os.path.dirname(__file__), "ig_28_reply_done.png")
                    await page.screenshot(path=res_ss)
                    print(f"🎉 [대성공] 28번 릴스 기존 댓글 밑에 실물 대댓글 작성 완료! 결과 캡처: {res_ss}")
                else:
                    print("⚠️ '게시' 버튼을 찾지 못했습니다.")
            else:
                print("⚠️ 대댓글 입력창을 찾지 못했습니다.")
        else:
            print("⚠️ '답글 달기' 버튼을 찾지 못했습니다.")
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_login_and_reply())
