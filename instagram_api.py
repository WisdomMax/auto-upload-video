import os
import logging
import httpx

logger = logging.getLogger("instagram_api")

GRAPH_API_VERSION = "v17.0"
GRAPH_API_URL = "https://graph.facebook.com"

_page_access_token_cache = None
_ig_biz_id_cache = None

def _get_api_config():
    """
    환경 변수의 토큰을 기반으로 메타 API를 호출하여
    진짜 Page Access Token 및 Instagram Business Account ID를 100% 자동으로 교환/획득합니다.
    """
    global _page_access_token_cache, _ig_biz_id_cache
    
    if _page_access_token_cache and _ig_biz_id_cache:
        return _page_access_token_cache, _ig_biz_id_cache
        
    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    business_account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    
    if not access_token:
        import database
        access_token = database.get_setting("INSTAGRAM_ACCESS_TOKEN")
    if not business_account_id:
        import database
        business_account_id = database.get_setting("INSTAGRAM_BUSINESS_ACCOUNT_ID")

    # [사용자님의 명답 적용]: 사용자 토큰을 Page Access Token 및 IG ID로 자동 변환 획득
    if access_token:
        try:
            url = f"{GRAPH_API_URL}/{GRAPH_API_VERSION}/me"
            params = {
                "fields": "id,name,accounts{id,name,access_token,instagram_business_account{id}}",
                "access_token": access_token
            }
            with httpx.Client(timeout=5.0) as client:
                res = client.get(url, params=params).json()
                accounts = res.get("accounts", {}).get("data", [])
                for acc in accounts:
                    p_token = acc.get("access_token")
                    ig_acc = acc.get("instagram_business_account", {})
                    ig_id = ig_acc.get("id")
                    if p_token and ig_id:
                        _page_access_token_cache = p_token
                        _ig_biz_id_cache = ig_id
                        logger.info(f"✅ Auto-exchanged Page Access Token & IG Business ID ({ig_id}) successfully!")
                        return _page_access_token_cache, _ig_biz_id_cache
        except Exception as e:
            logger.warning(f"Auto token exchange notice: {e}")

    _page_access_token_cache = access_token
    _ig_biz_id_cache = business_account_id
    return access_token, business_account_id

async def get_media_caption(media_id: str) -> str:
    """
    특정 인스타그램 미디어(Reels, Feed 등)의 캡션(본문) 텍스트를 조회합니다.
    """
    access_token, _ = _get_api_config()
    if not access_token:
        logger.error("INSTAGRAM_ACCESS_TOKEN is not set.")
        return ""
        
    url = f"{GRAPH_API_URL}/{GRAPH_API_VERSION}/{media_id}"
    params = {
        "fields": "caption",
        "access_token": access_token
    }
    
    logger.info(f"Fetching caption for media: {media_id}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            res_json = response.json()
            if response.status_code == 200:
                caption = res_json.get("caption", "")
                logger.info(f"Successfully retrieved caption for media {media_id}")
                return caption
            else:
                logger.error(f"Failed to get media caption. Status: {response.status_code}, Response: {res_json}")
                return ""
    except Exception as e:
        logger.error(f"Error calling Instagram Media API: {e}", exc_info=True)
        return ""

async def send_comment_reply(comment_id: str, message: str) -> bool:
    """
    특정 인스타그램 댓글에 대댓글(답글)을 답니다.
    """
    access_token, _ = _get_api_config()
    if not access_token:
        logger.error("INSTAGRAM_ACCESS_TOKEN is not set.")
        return False
        
    url = f"{GRAPH_API_URL}/{GRAPH_API_VERSION}/{comment_id}/replies"
    params = {
        "message": message,
        "access_token": access_token
    }
    
    logger.info(f"Sending reply to comment {comment_id}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params, timeout=10.0)
            res_json = response.json()
            if response.status_code == 200 and "id" in res_json:
                logger.info(f"Successfully replied to comment {comment_id}. Reply ID: {res_json['id']}")
                return True
            else:
                logger.error(f"Failed to send comment reply. Status: {response.status_code}, Response: {res_json}")
                return False
    except Exception as e:
        logger.error(f"Error calling Instagram Comment Reply API: {e}", exc_info=True)
        return False

async def send_instagram_dm(recipient_id: str, message: str) -> bool:
    """
    인스타그램 Scoped User ID(recipient_id)를 대상으로 직접 DM을 발송합니다.
    """
    access_token, business_account_id = _get_api_config()
    if not access_token or not business_account_id:
        logger.error("INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID is not set.")
        return False
        
    url = f"{GRAPH_API_URL}/{GRAPH_API_VERSION}/{business_account_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message
        }
    }
    
    logger.info(f"Sending Instagram DM to recipient {recipient_id}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            res_json = response.json()
            if response.status_code == 200 and "message_id" in res_json:
                logger.info(f"Successfully sent DM to {recipient_id}. Message ID: {res_json.get('message_id')}")
                return True
            else:
                logger.error(f"Failed to send Instagram DM. Status: {response.status_code}, Response: {res_json}")
                return False
    except Exception as e:
        logger.error(f"Error calling Instagram DM API: {e}", exc_info=True)
        return False

async def get_recent_media(limit: int = 15) -> list:
    """
    내 인스타그램 비즈니스 계정의 최근 업로드 미디어(릴스, 피드 등) 목록을 가져옵니다.
    """
    access_token, business_account_id = _get_api_config()
    if not access_token or not business_account_id:
        logger.error("INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID is not set.")
        return []
        
    url = f"{GRAPH_API_URL}/{GRAPH_API_VERSION}/{business_account_id}/media"
    params = {
        "access_token": access_token,
        "limit": limit
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            res_json = response.json()
            if response.status_code == 200:
                return res_json.get("data", [])
            else:
                logger.error(f"Failed to get recent media. Response: {res_json}")
                return []
    except Exception as e:
        logger.error(f"Error getting recent media: {e}", exc_info=True)
        return []

async def get_media_comments(media_id: str) -> list:
    """
    특정 미디어(릴스)에 달린 댓글 목록을 가져옵니다. (달린 대댓글 내역 포함)
    """
    access_token, _ = _get_api_config()
    if not access_token:
        logger.error("INSTAGRAM_ACCESS_TOKEN is not set.")
        return []
        
    url = f"{GRAPH_API_URL}/{GRAPH_API_VERSION}/{media_id}/comments"
    params = {
        "fields": "id,text,from,replies{id,from,text}",
        "access_token": access_token,
        "limit": 50
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            res_json = response.json()
            if response.status_code == 200:
                return res_json.get("data", [])
            else:
                logger.error(f"Failed to get media comments. Response: {res_json}")
                return []
    except Exception as e:
        logger.error(f"Error getting media comments: {e}", exc_info=True)
        return []
