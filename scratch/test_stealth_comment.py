import asyncio, os
from playwright.async_api import async_playwright

async def test_stealth_28():
    print("=== Playwright Stealth 28번 릴스 시범 스캔 개시 ===")
    
    async with async_playwright() as p:
        # 봇 탐지 우회를 위한 브라우저 옵션 설정
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        url = "https://www.instagram.com/p/DbAkcJDE7dt/"
        print(f"1. 28번 릴스 페이지 진입: {url}")
        await page.goto(url, wait_until="networkidle")
        
        # 스크린샷 캡처로 화면 상태 확인
        ss_path = os.path.join(os.path.dirname(__file__), "ig_28_scan.png")
        await page.screenshot(path=ss_path)
        print(f"✅ 28번 릴스 화면 캡처 완료: {ss_path}")
        
        # 댓글 요소 선택자 스캔
        title = await page.title()
        print(f"2. 페이지 타이틀: {title}")
        
        # '답글 달기' 또는 'Reply' 버튼 요소 검색
        reply_buttons = await page.query_selector_all("text='답글 달기'")
        if not reply_buttons:
            reply_buttons = await page.query_selector_all("text='Reply'")
            
        print(f"✅ 포착된 답글 버튼 개수: {len(reply_buttons)}개")
        
        await browser.close()

asyncio.run(test_stealth_28())
