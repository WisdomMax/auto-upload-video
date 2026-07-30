import asyncio, os, database
from playwright.async_api import async_playwright

async def run_stealth_reply():
    print("=== Playwright Stealth 28번 릴스 실전 대댓글 발송 테스트 개시 ===")
    
    # 28번 상품 데이터
    item28 = database.get_item_by_product_no(28)
    coupang_link = item28.get("short_url") or item28.get("coupang_url")
    catalog_link = "https://6070.piella.shop/p/28"
    
    reply_text = f"안녕하세요 어머님! 요청하신 28번 상품 상세 정보와 쿠팡 구매 링크입니다 💕 {coupang_link}"
    
    user_data_dir = os.path.expanduser("~/.config/ig_stealth_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    async with async_playwright() as p:
        # 세션 보존 및 스텔스 브라우저 실행
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
        
        # 1. 28번 릴스 진입
        url = "https://www.instagram.com/p/DbAkcJDE7dt/"
        print(f"1. 28번 릴스 접속: {url}")
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(2)
        
        # 2. 첫 번째 답글 달기 버튼 탐색
        reply_btn = await page.query_selector("text='답글 달기'")
        if not reply_btn:
            reply_btn = await page.query_selector("text='Reply'")
            
        if reply_btn:
            print("🎯 '답글 달기' 버튼 포착 성공! 클릭 시도...")
            await reply_btn.click()
            await asyncio.sleep(1)
            
            # 입력창 탐색
            input_box = await page.query_selector("textarea") or await page.query_selector("div[role='textbox']")
            if input_box:
                print("⌨️ 대댓글 입력창 포착! 대댓글 문구 타이핑 중...")
                await input_box.fill(reply_text)
                await asyncio.sleep(1)
                
                # 게시 버튼 탐색 및 클릭
                post_btn = await page.query_selector("text='게시'") or await page.query_selector("text='Post'")
                if post_btn:
                    print("🚀 '게시' 버튼 포착! 대댓글 최종 작성 전송 중...")
                    await post_btn.click()
                    await asyncio.sleep(3)
                    print("✅ [성공] 28번 릴스 기존 댓글 밑에 실물 대댓글 작성 완료!")
                else:
                    print("⚠️ 로그인 필요 여부 확인 (게시 버튼 탐색 단계)")
            else:
                print("⚠️ 대댓글 입력창을 찾지 못했습니다 (로그인 세션 필요 가능성)")
        else:
            print("⚠️ '답글 달기' 버튼을 찾지 못했습니다.")
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_stealth_reply())
