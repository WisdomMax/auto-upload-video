import asyncio
import logging
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

logger = logging.getLogger("coupang_scraper")

async def scrape_coupang_product(url: str) -> str:
    """
    Playwright Stealth 모드로 쿠팡 제품 페이지에 접속하여 상품명을 긁어옵니다.
    """
    logger.info(f"Scraping Coupang URL: {url}")
    
    if not url or "coupang.com" not in url:
        logger.warning("Invalid Coupang URL provided.")
        return "쿠팡 추천 상품"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # 일반 데스크톱 브라우저의 User-Agent 모사
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
            
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1280, "height": 800}
            )
            
            page = await context.new_page()
            # Stealth 모드 적용
            await stealth_async(page)
            
            logger.info("Navigating to product page...")
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            # 쿠팡 상품 정보 페이지의 다양한 제목 셀렉터 목록
            title_selectors = [
                "h2.prod-buy-header__title",
                ".prod-buy-header__title",
                ".prod-buy-header .title",
                "h2.title"
            ]
            
            product_title = None
            for selector in title_selectors:
                try:
                    title_element = await page.wait_for_selector(selector, timeout=3000)
                    if title_element:
                        product_title = await title_element.inner_text()
                        if product_title:
                            product_title = product_title.strip()
                            logger.info(f"Successfully scraped title with selector '{selector}': {product_title}")
                            break
                except Exception:
                    continue
            
            await browser.close()
            
            if product_title:
                return product_title
            else:
                logger.warning("Coupang title element not found on page.")
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
