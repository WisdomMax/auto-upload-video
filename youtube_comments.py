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
        # 1. 채널의 전체 업로드 비디오를 플레이리스트로 빠르게 조회
        ch_res = youtube.channels().list(id=channel_id, part="contentDetails").execute()
        if not ch_res.get("items"):
            logger.warning("Could not find YouTube channel details.")
            return
            
        uploads_playlist_id = ch_res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        playlist_res = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet",
            maxResults=50
        ).execute()
        
        # DB의 모든 상품 목록 조회
        import sqlite3
        conn = sqlite3.connect("db.sqlite")
        cur = conn.cursor()
        cur.execute("SELECT product_code, product_no, title, coupang_url FROM items;")
        db_items = cur.fetchall()
        conn.close()
        
        video_code_map = {}  # {video_id: (product_code, product_no, title)}
        code_pattern = re.compile(r'([O|T|P|D|S]\d{5})')
        
        for p_item in playlist_res.get("items", []):
            snippet = p_item["snippet"]
            vid = snippet["resourceId"]["videoId"]
            title = snippet.get("title", "")
            desc = snippet.get("description", "")
            
            matched = None
            
            # (1) 쿠팡 링크 내 itemId / pageKey 매칭 (가장 정확함)
            for pcode, pno, dbtitle, curl in db_items:
                if curl:
                    # itemId 추출
                    item_id_match = re.search(r'itemId=(\d+)', curl)
                    if item_id_match and item_id_match.group(1) in desc:
                        matched = (pcode, pno, dbtitle)
                        break
                    # pageKey 추출
                    page_key_match = re.search(r'pageKey=(\d+)', curl)
                    if page_key_match and page_key_match.group(1) in desc:
                        matched = (pcode, pno, dbtitle)
                        break
            
            # (2) 설명란/제목의 T000XX 코드 매칭
            if not matched:
                m = code_pattern.search(title + " " + desc)
                if m:
                    matched_code = m.group(1)
                    matched = (matched_code, int(matched_code[1:]), title)
                    
            # (3) 제목 단어 유사도 매칭
            if not matched:
                for pcode, pno, dbtitle, curl in db_items:
                    words = [w for w in dbtitle.split() if len(w) >= 3]
                    if any(w in title for w in words[:3]):
                        matched = (pcode, pno, dbtitle)
                        break
                        
            if matched:
                video_code_map[vid] = matched
                
        logger.info(f"Dynamic video-to-product mapping count: {len(video_code_map)}")
        
        # 2. 채널의 최근 댓글 목록 조회 (50개)
        comment_res = youtube.commentThreads().list(
            allThreadsRelatedToChannelId=channel_id,
            part="snippet,replies",
            maxResults=50
        ).execute()
        
        # 문의 의도 감지 키워드 리스트 (시니어 오타/변형 지원)
        keywords = [
            "엄마", "엉마", "음마", "어마", "엄 마",
            "정보", "링크", "얼마", "코드", "사이트", "주소", "어디", "어떻게",
            "구매", "가방", "신발", "바지", "원피스", "아우터", "주문", "가격", "사고십"
        ]
        
        reply_count = 0
        
        for thread in comment_res.get("items", []):
            top_comment = thread["snippet"]["topLevelComment"]
            comment_id = top_comment["id"]
            author_channel_id = top_comment["snippet"].get("authorChannelId", {}).get("value")
            text = top_comment["snippet"].get("textOriginal", "")
            video_id = top_comment["snippet"].get("videoId")
            
            # 본인 채널의 댓글은 패스
            if author_channel_id == channel_id:
                continue
                
            # 비디오 매핑에서 상품 정보 조회
            v_info = video_code_map.get(video_id)
            product_code = v_info[0] if v_info else "T00050"
            
            # 텍스트 정규화 (공백/특수문자 제거 후 검사)
            clean_text = re.sub(r'[\s\W_]+', '', text)
            has_intent = any(keyword in text or keyword in clean_text for keyword in keywords)
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
                
            # 유튜브 대댓글 템플릿: 한눈에 보이는 3줄 초간단 포맷 (더보기 접힘 방지)
            reply_text = (
                f"어머님 안녕하세요! 💕 문의하신 {product_code}번 상품 안내입니다!\n"
                f"👉 쇼핑몰: 6070.piella.shop\n"
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
            
            author_name = top_comment['snippet'].get('authorDisplayName')
            logger.info(f"Successfully replied to comment {comment_id} by {author_name} on video {video_id} ({product_code})")
            
            # 에이전트 로그 작성
            database.create_agent_log(
                task_type="comment_monitor",
                status="success",
                message=f"💬 [유튜브 대댓글 자동 작성] @{author_name}: \"{text[:20]}\" -> 대댓글 작성 완료 ({product_code})",
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

