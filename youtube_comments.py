import os
import re
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import database

logger = logging.getLogger("youtube_comments")

# PKCE code_verifier 임시 캐시용 글로벌 변수
_oauth_code_verifier = None

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

def get_oauth_flow():
    # client_secrets.json이 있으면 사용
    secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_secrets.json")
    if os.path.exists(secrets_path):
        try:
            return Flow.from_client_secrets_file(
                secrets_path,
                scopes=SCOPES,
                redirect_uri="http://localhost:18888/api/youtube/callback"
            )
        except Exception as e:
            logger.error(f"Failed to create flow from client_secrets.json: {e}")
    
    # 없으면 DB 설정에서 읽음
    client_id = database.get_setting("YOUTUBE_CLIENT_ID")
    client_secret = database.get_setting("YOUTUBE_CLIENT_SECRET")
    
    if client_id and client_secret:
        client_config = {
            "web": {
                "client_id": client_id,
                "project_id": "youtube-automation",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": ["http://localhost:18888/api/youtube/callback"]
            }
        }
        try:
            return Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri="http://localhost:18888/api/youtube/callback"
            )
        except Exception as e:
            logger.error(f"Failed to create flow from client configuration settings: {e}")
            
    return None

def get_credentials():
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            logger.error(f"Error loading token.json: {e}")
            
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        except Exception as e:
            # 인스타그램 집중 가동을 위해 만료된 유튜브 토큰 에러 도배를 완전히 차단합니다.
            logger.debug(f"Error refreshing credentials: {e}")
            creds = None
            
    return creds

def save_credentials(creds):
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
    with open(token_path, "w") as token:
        token.write(creds.to_json())

def get_youtube_service():
    creds = get_credentials()
    if not creds:
        return None
    return build("youtube", "v3", credentials=creds)

def check_and_reply_to_comments():
    youtube = get_youtube_service()
    if not youtube:
        logger.warning("YouTube service is not authenticated. Skipping comment reply task.")
        return
        
    channel_id = database.get_setting("YOUTUBE_CHANNEL_ID")
    if not channel_id:
        logger.warning("YOUTUBE_CHANNEL_ID not set. Skipping comment reply task.")
        return
        
    try:
        # 1. 채널 비디오-상품코드 매핑 동적 빌드
        # 채널 내 최신 20개 비디오 조회
        search_res = youtube.search().list(
            channelId=channel_id,
            part="snippet",
            type="video",
            maxResults=20,
            order="date"
        ).execute()
        
        video_code_map = {}  # {video_id: product_code}
        video_ids = [item["id"]["videoId"] for item in search_res.get("items", []) if "videoId" in item.get("id", {})]
        
        if video_ids:
            # 비디오 상세 정보(제목/설명란) 가져오기
            videos_res = youtube.videos().list(
                id=",".join(video_ids),
                part="snippet"
            ).execute()
            
            # 정규식 패턴 (O00001, T00002 등)
            code_pattern = re.compile(r'([O|T|P|D|S]\d{5})')
            
            for v_item in videos_res.get("items", []):
                vid = v_item["id"]
                title = v_item["snippet"].get("title", "")
                desc = v_item["snippet"].get("description", "")
                
                # 제목이나 설명란에서 상품코드 추출
                match = code_pattern.search(title + " " + desc)
                if match:
                    video_code_map[vid] = match.group(1)
                    
        logger.info(f"Dynamic video-to-product mapping: {video_code_map}")
        
        # 2. 채널의 최근 댓글 목록 조회
        comment_res = youtube.commentThreads().list(
            allThreadsRelatedToChannelId=channel_id,
            part="snippet,replies",
            maxResults=30
        ).execute()
        
        # 문의 의도 감지 키워드 리스트
        keywords = ["엄마", "정보", "링크", "얼마", "코드", "사이트", "주소", "어디", "어떻게", "구매", "가방", "신발", "바지", "원피스", "아우터"]
        
        reply_count = 0
        
        for thread in comment_res.get("items", []):
            top_comment = thread["snippet"]["topLevelComment"]
            comment_id = top_comment["id"]
            author_channel_id = top_comment["snippet"].get("authorChannelId", {}).get("value")
            text = top_comment["snippet"].get("textOriginal", "")
            video_id = top_comment["snippet"].get("videoId")
            
            # 본인 댓글은 패스
            if author_channel_id == channel_id:
                continue
                
            # 비디오 매핑에 없는 영상의 댓글은 패스
            if not video_id or video_id not in video_code_map:
                continue
                
            product_code = video_code_map[video_id]
            
            # 문의 의도 감지
            has_intent = any(keyword in text for keyword in keywords)
            if not has_intent:
                continue
                
            # 이미 내가 대댓글을 달았는지 중복 검사
            already_replied = False
            if "replies" in thread:
                for reply in thread["replies"].get("comments", []):
                    reply_author_id = reply["snippet"].get("authorChannelId", {}).get("value")
                    if reply_author_id == channel_id:
                        already_replied = True
                        break
            
            if already_replied:
                continue
                
            # DB에서 상품 코드로 정보 조회
            item = database.get_item_by_code(product_code)
            if not item:
                logger.warning(f"Product code {product_code} found in video {video_id} but not in database.")
                continue
                
            # 유튜브 대댓글 템플릿: 한눈에 보이는 3줄 초간단 포맷 (더보기 접힘 방지)
            reply_text = (
                f"어머님 안녕하세요! 💕 문의하신 {product_code}번 상품 안내입니다!\n"
                f"👉 쇼핑몰: 6080.piella.shop\n"
                f"(채널 메인 프로필 홈을 누르시면 바로 연결됩니다! ✨)"
            )



            
            # 대댓글 작성 API 호출
            youtube.comments().insert(
                part="snippet",
                body={
                    "snippet": {
                        "parentId": comment_id,
                        "textOriginal": reply_text
                    }
                }
            ).execute()
            
            logger.info(f"Successfully replied to comment {comment_id} on video {video_id} with product {product_code}")
            
            # 에이전트 로그 작성
            database.create_agent_log(
                task_type="comment_monitor",
                status="success",
                message=f"💬 [유튜브 대댓글 자동 작성] @{top_comment['snippet'].get('authorDisplayName')}: \"{text[:20]}\" -> 대댓글 작성 완료 ({product_code})",
                details=json.dumps({
                    "comment_id": comment_id,
                    "video_id": video_id,
                    "product_code": product_code,
                    "reply_text": reply_text
                }, ensure_ascii=False)
            )
            reply_count += 1
            
        logger.info(f"YouTube comment check finished. Replied to {reply_count} comments.")
        
    except Exception as e:
        logger.error(f"Error checking and replying to YouTube comments: {e}", exc_info=True)
