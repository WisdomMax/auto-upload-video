import os
import time
import hmac
import hashlib
import requests
import urllib.parse
import json
import random
import logging
from dotenv import load_dotenv
import database

# .env 로드
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

logger = logging.getLogger("recommendation_agent")
logging.basicConfig(level=logging.INFO)

COUPANG_ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY", "").strip()
COUPANG_SECRET_KEY = os.getenv("COUPANG_SECRET_KEY", "").strip()

DEFAULT_KEYWORDS = ["60대여성의류", "마담블라우스", "시니어여성복", "할머니옷", "어머니 원피스", "중년 여성 바지", "60대 여성 가디건"]

def extract_coupang_product_key(url: str) -> str:
    """쿠팡 URL에서 고유 상품 키(pageKey 또는 일반 상품 ID)를 추출합니다."""
    if not url:
        return ""
    import urllib.parse
    import re
    try:
        parsed = urllib.parse.urlparse(url)
        # 1. 쿼리 스트링에서 pageKey 파싱
        qs = urllib.parse.parse_qs(parsed.query)
        if "pageKey" in qs:
            return qs["pageKey"][0]
        # 2. URL 경로에서 /products/(\d+) 파싱
        match = re.search(r'/products/(\d+)', parsed.path)
        if match:
            return match.group(1)
        # 3. 차선책: itemId 파싱
        if "itemId" in qs:
            return qs["itemId"][0]
    except Exception as e:
        logger.error(f"Error parsing Coupang URL key: {e}")
    return url

def get_keywords_list():
    """DB 설정에서 검색 키워드 목록을 가져오거나 기본값을 반환합니다."""
    kws_str = database.get_setting("coupang_recommend_keywords")
    if kws_str:
        try:
            return [k.strip() for k in kws_str.split(",") if k.strip()]
        except Exception:
            pass
    
    # 기본값이 설정에 없으면 저장
    database.set_setting("coupang_recommend_keywords", ",".join(DEFAULT_KEYWORDS))
    return DEFAULT_KEYWORDS

def generate_signature(method, path, query_params, secret_key):
    """쿠팡 API용 HmacSHA256 서명을 생성합니다."""
    gmt_time = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    message = gmt_time + method + path + query_params
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    authorization = f"CEA algorithm=HmacSHA256, access-key={COUPANG_ACCESS_KEY}, signed-date={gmt_time}, signature={signature}"
    return authorization

def search_coupang_best_products(keyword: str, limit: int = 5):
    """쿠팡 파트너스 API를 통해 키워드로 제품을 검색해 리턴합니다."""
    if not COUPANG_ACCESS_KEY or not COUPANG_SECRET_KEY:
        logger.error("Coupang API keys not configured in .env")
        return []
        
    host = "api-gateway.coupang.com"
    path = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search"
    
    query_params = f"keyword={urllib.parse.quote(keyword)}&limit={limit}"
    url = f"https://{host}{path}?{query_params}"
    
    authorization = generate_signature("GET", path, query_params, COUPANG_SECRET_KEY)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": authorization
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("data") and data["data"].get("productData"):
                return data["data"]["productData"]
        else:
            logger.error(f"Coupang API search failed with status {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"Exception calling Coupang API search: {e}")
        
    return []

def generate_partners_short_link(coupang_url: str) -> str:
    """쿠팡 일반 URL을 파트너스 수익성 숏링크로 변환합니다."""
    if not COUPANG_ACCESS_KEY or not COUPANG_SECRET_KEY:
        logger.error("Coupang API keys not configured.")
        return ""
        
    host = "api-gateway.coupang.com"
    path = "/v2/providers/affiliate_open_api/apis/openapi/v1/links"
    
    url = f"https://{host}{path}"
    authorization = generate_signature("POST", path, "", COUPANG_SECRET_KEY)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": authorization
    }
    
    payload = {
        "coupangUrls": [coupang_url]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0].get("shortenUrl", "")
        else:
            logger.error(f"Coupang API shortlink creation failed with status {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"Exception calling Coupang API links: {e}")
        
    return ""

async def run_recommendation_batch(max_items_to_add: int = 2):
    """하루치 인기 옷 선추천 상품을 발굴하여 DB에 적재합니다."""
    logger.info("Starting Coupang Product Recommendation batch process...")
    
    keywords = get_keywords_list()
    if not keywords:
        logger.warning("No keywords configured for recommendation.")
        return
        
    # 랜덤하게 2~3개의 키워드를 선택해서 검색 실행
    selected_kws = random.sample(keywords, min(len(keywords), 3))
    
    added_count = 0
    existing_items = database.get_items()
    pending_recs = database.get_recommended_items(status="pending")
    
    # 중복 체크 속도 및 정확도를 위한 Set 캐시 생성
    existing_names = {item.get("title", "").strip() for item in existing_items if item.get("title")}
    existing_keys = {extract_coupang_product_key(item.get("coupang_url")) for item in existing_items if item.get("coupang_url")}
    
    pending_names = {r.get("product_name", "").strip() for r in pending_recs if r.get("product_name")}
    pending_keys = {extract_coupang_product_key(r.get("coupang_url")) for r in pending_recs if r.get("coupang_url")}
    
    for kw in selected_kws:
        if added_count >= max_items_to_add:
            break
            
        logger.info(f"Searching for hot clothing products with keyword: '{kw}'...")
        products = search_coupang_best_products(kw, limit=8)
        
        for prod in products:
            if added_count >= max_items_to_add:
                break
                
            name = prod.get("productName", "").strip()
            price = prod.get("productPrice", 0)
            img_url = prod.get("productImage", "")
            orig_url = prod.get("productUrl", "")
            
            if not name or not orig_url:
                continue
                
            # 상품명 정제 (꾸밈말 깎아내기) - 중복 검증을 위해 먼저 수행
            import re
            cleaned_name = re.sub(r'\[.*?\]', '', name)
            cleaned_name = re.sub(r'\(.*?\)', '', cleaned_name)
            cleaned_name = cleaned_name.split(",")[0].strip()
            
            # 너무 짧은 상품명 필터
            if len(cleaned_name) < 5:
                cleaned_name = name[:30]
                
            # 상품 고유 식별 키 추출
            prod_key = extract_coupang_product_key(orig_url)
            
            # 이미 등록된 상품(고유 키 또는 상품명 매치)이거나 추천 대기 목록에 있다면 중복 등록 패스
            if (prod_key and (prod_key in existing_keys or prod_key in pending_keys)) or (cleaned_name in existing_names or cleaned_name in pending_names):
                logger.info(f"Duplicate product skipped by key/name: {cleaned_name}")
                continue
                
            # 추천 상품 등록
            rec_id = database.create_recommended_item(
                product_name=cleaned_name,
                coupang_url=orig_url,
                original_image_url=img_url,
                price=price
            )
            
            logger.info(f"Successfully added AI recommended item #{rec_id}: {cleaned_name} ({price}원)")
            
            # 메모리 내 캐시 갱신 (동일 루프 내 중복 수집 방지)
            if prod_key:
                pending_keys.add(prod_key)
            pending_names.add(cleaned_name)
            
            added_count += 1
            
    database.create_agent_log(
        task_type="recommendation_search",
        status="success",
        message=f"🛍️ [AI 추천 발굴 완료] 60대 타겟 인기 의류 {added_count}종을 새로 발굴하여 대기 목록에 적재했습니다."
    )
    logger.info(f"Coupang Product Recommendation batch completed. Added {added_count} items.")

if __name__ == "__main__":
    # 로컬 테스트 구동
    import asyncio
    asyncio.run(run_recommendation_batch(max_items_to_add=2))
