import asyncio
import logging
from urllib.parse import urlparse, parse_qs, unquote
import requests
import urllib.parse
import re

logger = logging.getLogger("coupang_scraper")

async def scrape_coupang_product(url: str) -> str:
    """
    쿠팡 상품 URL에서 상품명을 파싱합니다.
    1. URL 쿼리 파라미터(q, title, product 등)에 상품 한글명이 있으면 네트워크 요청 없이 즉시 반환합니다.
    2. 그렇지 않은 경우, curl_cffi (Chrome impersonate)를 사용해 네이버 통합검색에 '쿠팡 상품번호'를 조회하여 한글 상품명을 간접적으로 긁어옵니다.
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

    # [Step 2] 네이버 검색을 통한 간접 스크래핑 시도 (curl_cffi + BeautifulSoup 우회)
    if product_id:
        try:
            from curl_cffi import requests as cffi_requests
            from bs4 import BeautifulSoup
            
            # 검색 키워드: '쿠팡 상품번호'
            query = f"쿠팡 {product_id}"
            search_url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
            logger.info(f"Attempting to scrape product title via Naver Search: {search_url}...")
            
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            
            # curl_cffi 크롬 임퍼스네이트로 네이버 봇 차단 완벽 회피
            response = cffi_requests.get(search_url, headers=headers, impersonate="chrome", timeout=8)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 블로그, 카페, 쇼핑, 웹 등 통합검색 결과 타이틀 클래스 후보들
                class_candidates = ['title_link', 'total_tit', 'lnk_tit', 'api_txt_lines', 'question_text']
                raw_titles = []
                
                for tag in soup.find_all(class_=lambda x: x and any(c in x for c in class_candidates)):
                    txt = tag.get_text().strip()
                    # 유효한 길이이고 포털 공통 문구가 아닌 경우 수집
                    if txt and len(txt) > 8 and "네이버" not in txt and "naver" not in txt.lower():
                        raw_titles.append(txt)
                
                # 중복 제거
                unique_titles = list(dict.fromkeys(raw_titles))
                logger.info(f"Found {len(unique_titles)} raw titles in Naver Search results.")
                
                best_title = None
                # 패션 의류 카테고리 관련 키워드 가점 매칭 우선순위 부여
                fashion_kws = ['원피스', '세트', '여성', '바지', '상하복', '팬츠', '의류', '빅사이즈', '중년', '투피스', '스커트', '홈웨어', '치마', '가디건', '티셔츠']
                
                for t in unique_titles:
                    if any(kw in t for kw in fashion_kws):
                        best_title = t
                        break
                
                # 패션 키워드가 없는 경우 가장 긴 타이틀을 후보로 선정
                if not best_title and unique_titles:
                    unique_titles.sort(key=len, reverse=True)
                    best_title = unique_titles[0]
                
                if best_title:
                    # 블로그 제목 특유의 장식어/추천 문구 가공 및 정제
                    cleaned_title = re.sub(r'\[쿠팡\]\s*', '', best_title)
                    cleaned_title = re.sub(r'\(.*?\)', '', cleaned_title)
                    cleaned_title = re.sub(r'\[.*?\]', '', cleaned_title)
                    cleaned_title = re.sub(r'\s*추천\s*$', '', cleaned_title)
                    cleaned_title = re.sub(r'\s*후기\s*$', '', cleaned_title)
                    cleaned_title = cleaned_title.replace("쿠팡", "").strip()
                    cleaned_title = re.sub(r'\.+\s*$', '', cleaned_title)  # 끝의 말줄임표 제거
                    
                    if len(cleaned_title) > 5:
                        logger.info(f"Successfully scraped title via Naver Search BeautifulSoup: {cleaned_title}")
                        return cleaned_title
                        
        except Exception as naver_err:
            logger.warning(f"Naver Search BeautifulSoup bypass failed: {naver_err}")
        
    return ""

if __name__ == "__main__":
    # 로컬 단독 테스트용
    async def test():
        test_url_direct = "https://www.coupang.com/vp/products/9419365819?itemId=27993177474&vendorItemId=94950750899"
        title = await scrape_coupang_product(test_url_direct)
        print("\n=== Naver Bypass Scrape Result ===")
        print("Scraped Title:", title)
        print("==================================\n")
    
    asyncio.run(test())
