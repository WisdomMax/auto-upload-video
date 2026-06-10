import asyncio
import logging
from urllib.parse import urlparse, parse_qs, unquote
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

logger = logging.getLogger("coupang_scraper")

async def scrape_coupang_product(url: str) -> str:
    """
    쿠팡 상품 URL에서 상품명을 파싱합니다.
    1. URL 쿼리 파라미터(q, title, product 등)에 상품 한글명이 있으면 네트워크 요청 없이 즉시 반환합니다.
    2. 그렇지 않은 경우, playwright-stealth 모드로 모바일 쿠팡 페이지에 딱 1회만 접속을 시도합니다.
    3. Akamai 방화벽 등에 의해 403 차단되거나 로딩 실패 시, 재시도 없이 즉시 기본값('엄마아빠 패션다이어리 추천 상품')을 반환하여 추가 차단을 방지합니다.
    """
    logger.info(f"Scraper requested for URL: {url}")
    
    # [Step 1] 무네트워크(Zero-network) URL 파라미터 분석
    try:
        parsed_url = urlparse(url)
        queries = parse_qs(parsed_url.query)
        
        # 흔히 사용되는 검색 키워드 및 상품 이름 관련 파라미터 후보들
        title_candidates = ["q", "title", "name", "prodName", "productName"]
        for key in title_candidates:
            if key in queries and queries[key]:
                val = unquote(queries[key][0]).strip()
                # 숫자가 아닌 유의미한 한글/영어 텍스트인 경우 반환
                if len(val) > 2 and not val.isdigit():
                    logger.info(f"Successfully extracted product name from URL query parameter '{key}': {val}")
                    return val
    except Exception as e:
        logger.warning(f"Failed to parse URL query parameters: {e}")
        
    # [Step 2] 1회성 모바일 접속 시도 (최대한 조심스럽게)
    try:
        target_url = url
        if "www.coupang.com" in url:
            target_url = url.replace("www.coupang.com", "m.coupang.com")
            
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security"
                ]
            )
            
            # 모바일(iPhone Safari)로 브라우저 콘텍스트 위장 설정
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                viewport={"width": 375, "height": 812},
                is_mobile=True,
                has_touch=True,
                locale="ko-KR",
                timezone_id="Asia/Seoul"
            )
            
            page = await context.new_page()
            
            # stealth 적용
            await Stealth().apply_stealth_async(page)
            
            # 타임아웃은 최대 8초로 단축하여 스케줄러 행(Hang) 예방
            response = await page.goto(target_url, timeout=8000, wait_until="domcontentloaded")
            
            if not response or response.status != 200:
                logger.warning(f"Failed to reach Coupang. Status: {response.status if response else 'None'}. Returning fallback.")
                await browser.close()
                return "엄마아빠 패션다이어리 추천 상품"
                
            # 상품 제목을 찾기 위한 다양한 셀렉터
            selectors = [
                "h2.prod-buy-header__title", 
                "h1.prod-buy-header__title", 
                ".prod-buy-header__title",
                ".prod-title",
                "h2.title"
            ]
            
            title = None
            for selector in selectors:
                try:
                    element = page.locator(selector)
                    if await element.count() > 0:
                        raw_title = await element.first.text_content()
                        if raw_title:
                            title = raw_title.strip()
                            break
                except Exception:
                    continue
                    
            await browser.close()
            
            if title:
                logger.info(f"Successfully scraped Coupang product title: {title}")
                return title
            else:
                logger.warning("No matching title selectors found. Returning fallback.")
                return "엄마아빠 패션다이어리 추천 상품"
                
    except Exception as e:
        logger.error(f"Coupang scraper failed: {e}. Returning fallback.")
        return "엄마아빠 패션다이어리 추천 상품"

if __name__ == "__main__":
    # 로컬 단독 테스트용
    async def test():
        # 1) 네트워크를 타지 않고 URL 파라미터에서 바로 한글명을 추출하는 케이스 테스트
        test_url_query = "https://www.coupang.com/vp/products/8070806412?q=%EB%A9%8B%EC%A7%84%20%EA%B0%80%EB%94%94%EA%B1%B4"
        title1 = await scrape_coupang_product(test_url_query)
        print("\n=== Test 1 (URL Query extraction) Result ===")
        print("Expected: 멋진 가디건, Actual:", title1)
        
        # 2) 네트워크를 타는 일반적인 케이스 테스트 (현재 IP 차단 상태라면 기본값 반환할 것)
        test_url_direct = "https://www.coupang.com/vp/products/8070806412"
        title2 = await scrape_coupang_product(test_url_direct)
        print("\n=== Test 2 (Direct network request) Result ===")
        print("Scraped Title:", title2)
        print("============================================\n")
    
    asyncio.run(test())


