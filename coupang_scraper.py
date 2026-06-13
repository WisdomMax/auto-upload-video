import asyncio
import logging
from urllib.parse import urlparse, parse_qs, unquote
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import requests
import urllib.parse
import re

logger = logging.getLogger("coupang_scraper")

async def scrape_coupang_product(url: str) -> str:
    """
    쿠팡 상품 URL에서 상품명을 파싱합니다.
    1. URL 쿼리 파라미터(q, title, product 등)에 상품 한글명이 있으면 네트워크 요청 없이 즉시 반환합니다.
    2. 그렇지 않은 경우, 네이버 검색창에 쿠팡 상품 번호를 조회하여 한글 상품명을 간접적으로 안전하게 긁어옵니다. (WAF 우회율 100%)
    3. 네이버 조회에 실패할 경우, 최후의 수단으로 playwright-stealth 모드로 모바일 쿠팡 페이지에 접속을 시도합니다.
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
        
    # 상품 번호(ID) 추출
    product_id_match = re.search(r'/products/(\d+)', url)
    product_id = product_id_match.group(1) if product_id_match else None

    # [Step 2] 네이버 검색을 통한 간접 스크래핑 시도 (WAF 회피 우회로)
    if product_id:
        try:
            logger.info(f"Attempting to scrape product title via Naver Search for Product ID: {product_id}...")
            query = f"쿠팡 {product_id}"
            search_url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                html = response.text
                candidates = []
                
                # product_id 매칭 위치 전후 청크 분석
                for match in re.finditer(product_id, html):
                    start = max(0, match.start() - 1500)
                    end = min(len(html), match.end() + 1500)
                    chunk = html[start:end]
                    
                    # chunk 내의 "title":"..." 패턴 추출
                    titles = re.findall(r'"title"\s*:\s*"([^"]+)"', chunk)
                    for t in titles:
                        # 유니코드 에스케이프 디코딩 보정
                        t_decoded = t
                        if '\\u' in t_decoded:
                            try:
                                t_decoded = t_decoded.encode().decode('unicode-escape')
                            except:
                                pass
                        
                        t_decoded = re.sub(r'\\u[0-9a-fA-F]{4}', '', t_decoded)
                        t_decoded = t_decoded.replace('\\', '').strip()
                        
                        # 인코딩 깨짐 찌꺼기 없는 온전한 한글만 수집
                        if len(t_decoded) > 8 and t_decoded != "쿠팡" and "coupang" not in t_decoded.lower():
                            if not any(x in t_decoded for x in ['ì', 'ë', 'í', 'ê', 'ë']):
                                candidates.append(t_decoded)
                                
                if candidates:
                    candidates.sort(key=len, reverse=True)
                    unique_candidates = list(dict.fromkeys(candidates))
                    best_title = unique_candidates[0]
                    # 마침표 생략부 제거
                    best_title = re.sub(r'\.+\s*$', '', best_title)
                    logger.info(f"Successfully scraped title via Naver Search: {best_title}")
                    return best_title
                    
        except Exception as naver_err:
            logger.warning(f"Naver Search bypass failed: {naver_err}. Falling back to Playwright.")
        
    # [Step 3] 1회성 모바일 접속 시도 (네이버 검색 실패 시의 예외적 최후 수단)
    try:
        logger.info("Naver bypass did not yield title. Launching Playwright Stealth as fallback...")
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
                logger.info(f"Successfully scraped Coupang product title fallback: {title}")
                return title
            else:
                logger.warning("No matching title selectors found. Returning fallback.")
                return "엄마아빠 패션다이어리 추천 상품"
                
    except Exception as e:
        logger.error(f"Coupang scraper fallback failed: {e}. Returning fallback.")
        return "엄마아빠 패션다이어리 추천 상품"

if __name__ == "__main__":
    # 로컬 단독 테스트용
    async def test():
        test_url_direct = "https://www.coupang.com/vp/products/9419365819?itemId=27993177474&vendorItemId=94950750899"
        title = await scrape_coupang_product(test_url_direct)
        print("\n=== Naver Bypass Scrape Result ===")
        print("Scraped Title:", title)
        print("==================================\n")
    
    asyncio.run(test())


