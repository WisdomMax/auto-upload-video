import asyncio
import logging
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

logger = logging.getLogger("coupang_scraper")

async def scrape_coupang_product(url: str) -> str:
    """
    Playwright Stealth 모드로 쿠팡 제품 페이지에 접속하여 상품명을 긁어옵니다.
    Akamai 방화벽 차단(Access Denied) 우회를 위해 모바일 도메인(m.coupang.com) 변환 및 상세 헤더 주입을 수행합니다.
    """
    logger.info(f"Scraping Coupang URL: {url}")
    
    if not url or "coupang.com" not in url:
        logger.warning("Invalid Coupang URL provided.")
        return "쿠팡 추천 상품"

    # 시도할 URL 후보군 (1차: 원본 URL, 2차: 모바일 도메인으로 치환한 URL)
    url_candidates = [url]
    if "www.coupang.com" in url:
        mobile_url = url.replace("www.coupang.com", "m.coupang.com")
        url_candidates.append(mobile_url)

    # 쿠팡 상품 정보 페이지의 다양한 제목 셀렉터 목록 (데스크톱 & 모바일 커버)
    title_selectors = [
        "h2.prod-buy-header__title",
        ".prod-buy-header__title",
        ".prod-buy-header .title",
        "h1.prod-buy-header__title",
        "h1.product-title",
        ".product-name",
        "h2.title",
        "h1.title",
        "h1"
    ]

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--headless=new'])
            
            # 실제 iPhone 모바일 기기처럼 보이도록 정교한 헤더 및 User-Agent 지정
            user_agent = (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            )
            
            extra_headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "upgrade-insecure-requests": "1"
            }
            
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 375, "height": 812},
                is_mobile=True,
                extra_http_headers=extra_headers
            )
            
            page = await context.new_page()
            # Stealth 모드 적용
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            product_title = None
            
            for attempt_url in url_candidates:
                logger.info(f"Navigating to: {attempt_url}")
                try:
                    await page.goto(attempt_url, wait_until="networkidle", timeout=30000)
                    
                    # 디버그용 스크린샷 저장
                    import os
                    os.makedirs("static", exist_ok=True)
                    await page.screenshot(path="static/debug_coupang.png")
                    
                    content = await page.content()
                    if "Access Denied" in content or "You don't have permission" in content:
                        logger.warning(f"Access Denied on URL: {attempt_url}. Trying next candidate...")
                        continue  # 차단되었다면 다음 URL 후보(모바일)로 넘어감
                        
                    # 제목 셀렉터 순차 매칭
                    for selector in title_selectors:
                        try:
                            title_element = await page.wait_for_selector(selector, timeout=3000)
                            if title_element:
                                text = await title_element.inner_text()
                                if text and text.strip():
                                    product_title = text.strip()
                                    logger.info(f"Successfully scraped title with selector '{selector}': {product_title}")
                                    break
                        except Exception:
                            continue
                            
                    if product_title:
                        break  # 제목 추출에 성공했으면 시도 중단
                        
                except Exception as ex:
                    logger.error(f"Navigation or parsing failed for {attempt_url}: {ex}")
                    continue
            
            await browser.close()
            
            if product_title:
                return product_title
            else:
                logger.warning("Coupang title element not found on page after trying all options.")
                return "쿠팡 추천 상품"
                
    except Exception as e:
        logger.error(f"Exception while scraping Coupang: {e}")
        return "쿠팡 추천 상품"

if __name__ == "__main__":
    # 로컬 단독 간이 테스트용
    async def test():
        test_url = "https://www.coupang.com/vp/products/8070806412"
        title = await scrape_coupang_product(test_url)
        print("Scraped Title Result:", title)
    
    asyncio.run(test())
