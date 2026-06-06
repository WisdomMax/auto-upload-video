import os
import shutil
import logging
import json
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

import database

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# 인접 프로젝트 .env 로드 시도
ADJACENT_ENV = "/Volumes/NVME/7.AI_vibe_coding/20260413 SNS_automation_writing/.env"
if os.path.exists(ADJACENT_ENV):
    logger.info(f"Adjacent .env found at {ADJACENT_ENV}. Loading configurations...")
    load_dotenv(dotenv_path=ADJACENT_ENV)
else:
    load_dotenv()

app = FastAPI(title="SNS Automation & Video Auto-Publisher")

# 디렉토리 생성
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
ORIGINALS_DIR = os.path.join(UPLOADS_DIR, "originals")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

for d in [UPLOADS_DIR, ORIGINALS_DIR, STATIC_DIR, TEMPLATES_DIR]:
    os.makedirs(d, exist_ok=True)

# 스태틱 파일 및 템플릿 마운트
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

class PublishPayload(BaseModel):
    platforms: List[str]

# 쿠팡 파트너스 API 단축 링크 발급
def get_coupang_short_link(original_url: str, access_key: str, secret_key: str) -> str:
    if not access_key or not secret_key:
        return ""
        
    import hmac
    import hashlib
    import time
    
    host = "api-gateway.coupang.com"
    path = "/v1/partners/domains/links"
    url = f"https://{host}{path}"
    method = "POST"
    
    payload = {
        "coupangUrls": [original_url]
    }
    
    gmt_time = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    message = gmt_time + method + path
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    authorization = f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={gmt_time}, signature={signature}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": authorization
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0].get("shortenUrl", "")
        logger.error(f"Coupang API Error: {res.status_code} - {res.text}")
    except Exception as e:
        logger.error(f"Coupang Link Shortening Exception: {e}")
        
    return ""

# AI SNS 원고 생성 함수
def generate_ai_sns_content(item_id: int):
    item = database.get_item(item_id)
    if not item:
        return
        
    api_key = database.get_setting("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    link = item['short_url'] if item['short_url'] else item['coupang_url']
    
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = f"""
            당신은 숏폼(유튜브 쇼츠, 틱톡, 인스타그램 릴스) 마케팅 전문가이자 크리에이터입니다.
            아래 제품 정보를 바탕으로 소셜 미디어 플랫폼별 최적화된 콘텐츠를 생성해 주세요.
            
            [제품 정보]
            - 브랜드/채널명: 엄마아빠 패션다이어리
            - 상품 번호: {item['product_no']}
            - 상품명: {item['title']}
            - 설명: {item['description']}
            - 쿠팡 링크: {link}
            
            [출력 요구 사항]
            반드시 아래 JSON 포맷을 준수하여 답변해 주세요. JSON 형식이 깨지지 않도록 백틱(```json) 없이 순수 JSON만 출력하거나 올바른 JSON 문자열로만 응답해 주세요.
            
            {{
                "youtube_title": "유튜브 쇼츠 전용 제목 (공백 포함 50자 내외, 클릭 유도형, 마지막에 #Shorts 포함)",
                "youtube_description": "유튜브 본문 설명란 텍스트 (제품 구매 링크 {link}를 포함하고, 해시태그와 쿠팡파트너스 안내 문구인 '이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.'가 꼭 들어가도록 작성)",
                "youtube_tags": "쉼표로 구분된 유튜브 해시태그 및 태그들 (예: #살림템, #쿠팡추천, #꿀템)",
                "sns_caption": "틱톡 및 인스타그램 릴스 배포용 본문 글 (후킹이 강하고 이모지를 적절히 사용한 3줄 이내의 짧은 캡션. 본문 끝에 시청자가 댓글로 '링크' 또는 '{item['product_no']}'를 남겨두면 DM으로 구매 링크를 발송하겠다는 안내 멘트를 포함해 주세요. 예: 댓글로 '1'을 적어주시면 단축 링크를 DM으로 쏴드려요! 💌)",
                "comment_reply": "유튜브 쇼츠 댓글 링크 비활성화 정책에 맞춰 작성하는 네이버 검색 유도용 대댓글 답변 템플릿 (예: 유튜브 쇼츠 정책상 링크 클릭이 되지 않아 편리한 검색을 도와드려요! 네이버에서 '엄마아빠 패션다이어리 {item['title']}'를 검색해 주시면 첫 번째 글에서 바로 링크를 확인하실 수 있습니다! 🔍)",
                "dm_template": "요청한 유저에게 실제로 보낼 인스타/틱톡 DM 템플릿 (인사말, 제품 설명 한 줄, 그리고 바로 쿠팡 단축 링크 {link}를 제공하는 레이아웃)"
            }}
            """
            
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            if response and response.text:
                data = json.loads(response.text.strip())
                database.update_item_generated_contents(
                    item_id,
                    data.get("youtube_title", ""),
                    data.get("youtube_description", ""),
                    data.get("youtube_tags", ""),
                    data.get("sns_caption", ""),
                    data.get("dm_template", ""),
                    data.get("comment_reply", "")
                )
                logger.info(f"AI content generated successfully for item {item_id}")
                return
        except Exception as e:
            logger.error(f"Gemini API Content Generation Exception: {e}")
            
    # Fallback 템플릿 처리
    logger.info(f"Using template fallback content for item {item_id}")
    youtube_title = f"[No.{item['product_no']}] {item['title']} 솔직 후기 및 추천! #Shorts"
    youtube_description = f"영상 속 추천 아이템 정보입니다! 👇\n\n구매 링크: {link}\n\n[제품 설명]\n{item['description']}\n\n* 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.\n\n#쿠팡추천템 #살림꿀템 #추천아이템"
    youtube_tags = f"#쿠팡추천, #꿀템, #살림꿀템, #살림템, #생활용품, #{item['title']}"
    
    sns_caption = f"이거 하나로 고민 해결! 대박 꿀템 공유해 드립니다 ✨\n\nNo.{item['product_no']} - {item['title']}\n\n👉 제품의 상세 정보와 단축 링크가 필요하시다면?\n댓글로 '링크' 또는 '{item['product_no']}'를 남겨주시면 DM으로 바로 링크를 쏴드릴게요! 💌\n\n#생활꿀팁 #살림템 #꿀템 #쿠팡추천"
    comment_reply = f"유튜브 정책상 댓글 링크 클릭이 되지 않아서 네이버 검색을 유도해 드려요! 🔍 네이버 검색창에 '엄마아빠 패션다이어리 {item['title']}'을 검색하시면 상세 정보와 쿠팡 링크를 바로 확인하실 수 있습니다!"
    dm_template = f"안녕하세요 크리에이터입니다! 😊\n요청하신 [No.{item['product_no']} - {item['title']}]의 상세 링크입니다.\n\n👇 쿠팡 즉시구매 링크\n{link}\n\n즐겁고 스마트한 쇼핑 되세요!"
    
    database.update_item_generated_contents(
        item_id,
        youtube_title,
        youtube_description,
        youtube_tags,
        sns_caption,
        dm_template,
        comment_reply
    )

# Cloudflare R2 동영상 업로드 함수
def upload_video_to_r2(file_path: str, product_no: int) -> str:
    account_id = database.get_setting("CLOUDFLARE_ACCOUNT_ID") or os.getenv("CLOUDFLARE_ACCOUNT_ID")
    api_token = database.get_setting("CLOUDFLARE_API_TOKEN") or os.getenv("CLOUDFLARE_API_TOKEN")
    bucket_name = database.get_setting("CLOUDFLARE_BUCKET_NAME") or os.getenv("CLOUDFLARE_BUCKET_NAME", "blog")
    public_url_base = database.get_setting("CLOUDFLARE_PUBLIC_URL") or os.getenv("CLOUDFLARE_PUBLIC_URL")

    if not account_id or not api_token or not public_url_base:
        raise Exception("Cloudflare R2 설정 정보(Account ID, API Token, Public URL Base)가 누락되었습니다.")

    import time
    import re
    
    timestamp = int(time.time())
    filename = os.path.basename(file_path)
    clean_filename = re.sub(r'[^a-zA-Z0-9._]', '_', filename)
    object_name = f"video_{product_no}_{timestamp}_{clean_filename}"

    base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/r2/buckets/{bucket_name}/objects"
    url = f"{base_url}/{object_name}"
    headers = {"Authorization": f"Bearer {api_token}"}

    logger.info(f"Starting Cloudflare R2 video upload: {object_name}...")
    with open(file_path, "rb") as f:
        # 비디오 파일 업로드이므로 timeout을 충분히 설정 (2분)
        response = requests.put(url, headers=headers, data=f, timeout=120)

    if response.status_code == 200:
        r2_url = f"{public_url_base.rstrip('/')}/{object_name}"
        logger.info(f"Cloudflare R2 video upload completed. URL: {r2_url}")
        return r2_url
    else:
        raise Exception(f"R2 업로드 HTTP 실패 ({response.status_code}): {response.text}")

# Buffer를 통한 개별 비디오 포스트 발행 함수
def publish_post_via_buffer(profile_id: str, text: str, video_url: str, service_type: str, title: str = None) -> dict:
    access_token = database.get_setting("BUFFER_ACCESS_TOKEN") or os.getenv("BUFFER_ACCESS_TOKEN")
    if not access_token:
        raise Exception("Buffer Access Token이 누락되었습니다.")

    endpoint = "https://api.buffer.com"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id text }
        }
        ... on MutationError {
          message
        }
      }
    }
    """

    post_input = {
        "channelId": profile_id,
        "text": text,
        "schedulingType": "automatic",
        "mode": "shareNow"
    }

    # 비디오 에셋 지정
    post_input["assets"] = [
        {
            "video": {
                "url": video_url,
                "metadata": {
                    "title": title or "Product Video"
                }
            }
        }
    ]

    # 플랫폼별 맞춤형 메타데이터 주입
    metadata = {}
    svc = service_type.lower()
    
    if "instagram" in svc:
        metadata["instagram"] = {
            "type": "reel",
            "shouldShareToFeed": True
        }
    elif "youtube" in svc:
        metadata["youtube"] = {
            "title": title[:100] if title else "Shorts Video", # 유튜브 제목 최대 100자 한도
            "privacy": "public"
        }
    elif "tiktok" in svc:
        metadata["tiktok"] = {
            "title": text[:150] if text else "TikTok Video"
        }

    if metadata:
        post_input["metadata"] = metadata

    variables = {"input": post_input}

    logger.info(f"Sending video post mutation to Buffer for profile {profile_id} ({service_type})...")
    response = requests.post(
        endpoint,
        json={"query": mutation, "variables": variables},
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"Buffer HTTP Error {response.status_code}: {response.text}")

    data = response.json()
    if "errors" in data:
        raise Exception(f"Buffer GraphQL errors: {data['errors']}")

    create_post_res = data.get("data", {}).get("createPost", {})
    if "message" in create_post_res:
        return {"status": "error", "message": create_post_res["message"]}
        
    return {"status": "success", "post_id": create_post_res.get("post", {}).get("id")}

# 백그라운드 일괄 배포 작업 함수
def distribute_video_task(item_id: int, platforms: List[str]):
    item = database.get_item(item_id)
    if not item:
        return

    database.update_item_publish_results(item_id, "publishing", json.dumps({"message": "동영상을 Cloudflare R2에 업로드 중..."}))

    # 1. R2 업로드 진행 (R2 URL이 아직 없으면 업로드 수행)
    r2_url = item['r2_video_url']
    if not r2_url:
        try:
            r2_url = upload_video_to_r2(item['original_video_path'], item['product_no'])
            database.update_item_r2_url(item_id, r2_url)
        except Exception as e:
            logger.error(f"R2 Upload Exception: {e}")
            database.update_item_publish_results(item_id, "failed", json.dumps({"error": f"R2 업로드 실패: {str(e)}"}))
            return

    # 2. Buffer 프로필 리스트 획득
    access_token = database.get_setting("BUFFER_ACCESS_TOKEN") or os.getenv("BUFFER_ACCESS_TOKEN")
    if not access_token:
        database.update_item_publish_results(item_id, "failed", json.dumps({"error": "Buffer Access Token이 누락되었습니다."}))
        return

    try:
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        query = """
        query {
          account {
            organizations {
              channels {
                id
                name
                service
              }
            }
          }
        }
        """
        res = requests.post("https://api.buffer.com", json={"query": query}, headers=headers, timeout=15)
        profiles = []
        if res.status_code == 200:
            orgs = res.json().get("data", {}).get("account", {}).get("organizations", [])
            for org in orgs:
                for channel in org.get("channels", []):
                    profiles.append(channel)
        else:
            raise Exception(f"Buffer HTTP {res.status_code}")
    except Exception as e:
        logger.error(f"Buffer Profiles Fetch Exception: {e}")
        database.update_item_publish_results(item_id, "failed", json.dumps({"error": f"Buffer 채널 목록 동기화 실패: {str(e)}"}))
        return

    # 3. 플랫폼 매핑 배포 실행
    results = {}
    success_count = 0
    failed_count = 0

    for platform in platforms:
        # 대응되는 Buffer 채널 탐색
        target_channel = None
        for p in profiles:
            svc = p['service'].lower()
            if platform == 'youtube' and 'youtube' in svc:
                target_channel = p
                break
            elif platform == 'tiktok' and 'tiktok' in svc:
                target_channel = p
                break
            elif platform == 'instagram' and 'instagram' in svc:
                target_channel = p
                break

        if not target_channel:
            results[platform] = {"status": "error", "message": "Buffer에 연동된 채널을 찾을 수 없습니다."}
            failed_count += 1
            continue

        # 플랫폼별 텍스트 및 제목 가공
        text = item['sns_caption']
        title = item['title']
        if platform == 'youtube':
            text = item['youtube_description']
            title = item['youtube_title'] or item['title']

        # 배포 요청
        try:
            res_val = publish_post_via_buffer(
                profile_id=target_channel['id'],
                text=text,
                video_url=r2_url,
                service_type=target_channel['service'],
                title=title
            )
            results[platform] = res_val
            if res_val["status"] == "success":
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            results[platform] = {"status": "error", "message": str(e)}
            failed_count += 1

    # 최종 배포 상태 결정 및 DB 업데이트
    if failed_count == 0:
        final_status = "completed"
    elif success_count == 0:
        final_status = "failed"
    else:
        final_status = "partial_failed"

    database.update_item_publish_results(item_id, final_status, json.dumps(results))
    logger.info(f"Platform batch distribution task finished for item {item_id} with status: {final_status}")

# --- FastAPI Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/items")
async def get_all_items():
    items = database.get_items()
    return items

@app.get("/api/items/{item_id}")
async def get_single_item(item_id: int):
    item = database.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/api/items")
async def add_item(
    product_no: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    coupang_url: str = Form(...),
    video: UploadFile = File(...)
):
    original_filename = f"prod_{product_no}_{video.filename}"
    original_path = os.path.join(ORIGINALS_DIR, original_filename)
    
    with open(original_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
        
    # DB 아이템 생성
    item_id = database.create_item(
        product_no=product_no,
        title=title,
        description=description,
        coupang_url=coupang_url,
        original_video_path=original_path
    )
    
    # 쿠팡 API 키 로드 후 링크 단축 시도
    coupang_access = database.get_setting("COUPANG_ACCESS_KEY") or os.getenv("COUPANG_ACCESS_KEY")
    coupang_secret = database.get_setting("COUPANG_SECRET_KEY") or os.getenv("COUPANG_SECRET_KEY")
    
    short_url = ""
    if coupang_access and coupang_secret:
        short_url = get_coupang_short_link(coupang_url, coupang_access, coupang_secret)
        if short_url:
            database.update_item_coupang_urls(item_id, coupang_url, short_url)
            
    # AI 멘트/캡션 즉시 생성
    generate_ai_sns_content(item_id)
    
    return {"status": "success", "item_id": item_id, "short_url": short_url}

@app.post("/api/items/{item_id}/publish")
async def publish_item(item_id: int, payload: PublishPayload, background_tasks: BackgroundTasks):
    item = database.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if not payload.platforms:
        raise HTTPException(status_code=400, detail="No platforms selected")
        
    # 백그라운드 배포 작업 시작
    background_tasks.add_task(distribute_video_task, item_id, payload.platforms)
    return {"status": "success", "message": "배포 작업이 예약되었습니다."}

@app.put("/api/items/{item_id}/short-link")
async def update_short_link(item_id: int, payload: dict):
    short_url = payload.get("short_url", "")
    coupang_url = payload.get("coupang_url", "")
    
    item = database.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    new_coupang_url = coupang_url if coupang_url else item['coupang_url']
    database.update_item_coupang_urls(item_id, new_coupang_url, short_url)
    
    # 링크 변경 시 콘텐츠 자동 재생성
    generate_ai_sns_content(item_id)
    
    return {"status": "success"}

@app.post("/api/items/{item_id}/regenerate")
async def regenerate_contents(item_id: int):
    item = database.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    generate_ai_sns_content(item_id)
    return {"status": "success", "item": database.get_item(item_id)}

@app.delete("/api/items/{item_id}")
async def delete_single_item(item_id: int):
    item = database.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if item['original_video_path'] and os.path.exists(item['original_video_path']):
        try:
            os.remove(item['original_video_path'])
        except Exception as e:
            logger.error(f"Failed to delete original video file: {e}")
            
    database.delete_item(item_id)
    return {"status": "success"}

@app.get("/api/settings")
async def get_settings():
    settings = database.get_all_settings()
    # Fallback값 병합하여 표시
    response_settings = {
        "GEMINI_API_KEY": settings.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or "",
        "COUPANG_ACCESS_KEY": settings.get("COUPANG_ACCESS_KEY") or os.getenv("COUPANG_ACCESS_KEY") or "",
        "COUPANG_SECRET_KEY": settings.get("COUPANG_SECRET_KEY") or os.getenv("COUPANG_SECRET_KEY") or "",
        "BUFFER_ACCESS_TOKEN": settings.get("BUFFER_ACCESS_TOKEN") or os.getenv("BUFFER_ACCESS_TOKEN") or "",
        "CLOUDFLARE_ACCOUNT_ID": settings.get("CLOUDFLARE_ACCOUNT_ID") or os.getenv("CLOUDFLARE_ACCOUNT_ID") or "",
        "CLOUDFLARE_API_TOKEN": settings.get("CLOUDFLARE_API_TOKEN") or os.getenv("CLOUDFLARE_API_TOKEN") or "",
        "CLOUDFLARE_BUCKET_NAME": settings.get("CLOUDFLARE_BUCKET_NAME") or os.getenv("CLOUDFLARE_BUCKET_NAME") or "blog",
        "CLOUDFLARE_PUBLIC_URL": settings.get("CLOUDFLARE_PUBLIC_URL") or os.getenv("CLOUDFLARE_PUBLIC_URL") or "",
        "MANYCHAT_API_TOKEN": settings.get("MANYCHAT_API_TOKEN") or os.getenv("MANYCHAT_API_TOKEN") or "",
        "YOUTUBE_API_KEY": settings.get("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY") or "",
        "YOUTUBE_CHANNEL_ID": settings.get("YOUTUBE_CHANNEL_ID") or os.getenv("YOUTUBE_CHANNEL_ID") or ""
    }
    
    # 마스킹 처리
    masked_settings = {}
    for k, v in response_settings.items():
        if v:
            if any(term in k for term in ["KEY", "SECRET", "TOKEN"]):
                masked_settings[k] = v[:4] + "*" * (len(v) - 4) if len(v) > 4 else "****"
            else:
                masked_settings[k] = v
        else:
            masked_settings[k] = ""
    return masked_settings

@app.post("/api/settings")
async def update_settings(payload: dict):
    for k, v in payload.items():
        # 마스킹 값은 스킵
        if v and (v.startswith("****") or (len(v) > 4 and "*" in v[4:])):
            continue
        database.set_setting(k, v)
    return {"status": "success"}

@app.get("/api/youtube/comments")
async def get_youtube_comments():
    api_key = database.get_setting("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY")
    channel_id = database.get_setting("YOUTUBE_CHANNEL_ID") or os.getenv("YOUTUBE_CHANNEL_ID")
    
    if not api_key or not channel_id:
        return {"status": "error", "message": "YouTube API Key 또는 Channel ID가 설정되지 않았습니다."}
        
    url = f"https://www.googleapis.com/youtube/v3/commentThreads?allThreadsRelatedToChannelId={channel_id}&key={api_key}&part=snippet&maxResults=20"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            comments = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                top_comment = snippet.get("topLevelComment", {}).get("snippet", {})
                comments.append({
                    "id": item.get("id"),
                    "videoId": snippet.get("videoId"),
                    "text": top_comment.get("textOriginal"),
                    "author": top_comment.get("authorDisplayName"),
                    "authorUrl": top_comment.get("authorChannelUrl"),
                    "avatar": top_comment.get("authorProfileImageUrl"),
                    "publishedAt": top_comment.get("publishedAt")
                })
            return {"status": "success", "comments": comments}
        else:
            return {"status": "error", "message": f"YouTube API Error ({res.status_code}): {res.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def format_view_count(views_str: str) -> str:
    if not views_str:
        return "0회"
    try:
        views = int(views_str)
        if views >= 100000000:
            return f"{views / 100000000:.1f}억회".replace(".0억회", "억회")
        elif views >= 10000:
            return f"{views / 10000:.1f}만회".replace(".0만회", "만회")
        else:
            return f"{views}회"
    except ValueError:
        return views_str

def fetch_youtube_trends_from_api(keyword: str, api_key: str) -> list:
    if not keyword or not api_key:
        return []
    
    # 1. search.list 호출 (10개 동영상)
    search_url = f"https://www.googleapis.com/youtube/v3/search?q={requests.utils.quote(keyword)}&part=snippet&type=video&maxResults=10&key={api_key}"
    try:
        search_res = requests.get(search_url, timeout=10)
        if search_res.status_code != 200:
            logger.error(f"YouTube Search API Error: {search_res.status_code} - {search_res.text}")
            return []
        
        search_data = search_res.json()
        items = search_data.get("items", [])
        if not items:
            return []
        
        video_ids = []
        channel_ids = set()
        for item in items:
            vid = item.get("id", {}).get("videoId")
            cid = item.get("snippet", {}).get("channelId")
            if vid:
                video_ids.append(vid)
            if cid:
                channel_ids.add(cid)
                
        if not video_ids:
            return []
            
        # 2. videos.list 호출 (조회수 획득)
        ids_str = ",".join(video_ids)
        videos_url = f"https://www.googleapis.com/youtube/v3/videos?id={ids_str}&part=snippet,statistics&key={api_key}"
        videos_res = requests.get(videos_url, timeout=10)
        if videos_res.status_code != 200:
            logger.error(f"YouTube Videos API Error: {videos_res.status_code} - {videos_res.text}")
            return []
            
        videos_data = videos_res.json()
        
        # 3. channels.list 호출 (구독자 수 획득)
        channels_info = {}
        if channel_ids:
            cids_str = ",".join(list(channel_ids))
            channels_url = f"https://www.googleapis.com/youtube/v3/channels?id={cids_str}&part=statistics&key={api_key}"
            channels_res = requests.get(channels_url, timeout=10)
            if channels_res.status_code == 200:
                channels_data = channels_res.json()
                for ch in channels_data.get("items", []):
                    ch_stats = ch.get("statistics", {})
                    channels_info[ch.get("id")] = ch_stats.get("subscriberCount", "0")
        
        trends = []
        for v in videos_data.get("items", []):
            snippet = v.get("snippet", {})
            stats = v.get("statistics", {})
            raw_views = stats.get("viewCount", "0")
            
            # 조회수 최소 1000회 이상 필터링
            try:
                views = int(raw_views)
                if views < 1000:
                    continue
            except Exception:
                continue
            
            # 기여도(효율) 알고리즘 적용
            cid = snippet.get("channelId")
            raw_subs = channels_info.get(cid, "0")
            
            efficiency = "Normal"
            efficiency_label = "보통"
            
            try:
                subs = int(raw_subs)
                # 분모가 0이 되는 제로 디비전만 방지
                effective_subs = max(subs, 1)
                ratio = views / effective_subs
                
                if ratio >= 1.0:
                    efficiency = "Great"
                    efficiency_label = "🔥 그레이트"
                elif ratio >= 0.25:
                    efficiency = "Good"
                    efficiency_label = "👍 굿"
                else:
                    efficiency = "Normal"
                    efficiency_label = "보통"
            except Exception:
                pass
            
            trends.append({
                "videoId": v.get("id"),
                "title": snippet.get("title"),
                "channelTitle": snippet.get("channelTitle"),
                "viewCount": format_view_count(raw_views),
                "publishedAt": snippet.get("publishedAt"),
                "thumbnailUrl": snippet.get("thumbnails", {}).get("medium", {}).get("url") or snippet.get("thumbnails", {}).get("default", {}).get("url"),
                "efficiency": efficiency,
                "efficiencyLabel": efficiency_label
            })
        return trends
    except Exception as e:
        logger.error(f"Error fetching YouTube trends: {e}")
        return []

@app.get("/api/items/{item_id}/youtube-trends")
async def get_item_youtube_trends(item_id: int):
    item = database.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # 캐싱된 정보가 있으면 반환
    if item.get("youtube_trends"):
        try:
            trends = json.loads(item["youtube_trends"])
            return {"status": "success", "cached": True, "trends": trends}
        except Exception:
            pass
            
    # 없으면 최초 1회 생성 시도
    api_key = database.get_setting("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return {"status": "error", "message": "YouTube API Key가 설정되지 않아 트렌드 조회가 불가능합니다."}
        
    keyword = item["title"]
    trends = fetch_youtube_trends_from_api(keyword, api_key)
    
    # DB 저장
    database.update_item_youtube_trends(item_id, json.dumps(trends))
    return {"status": "success", "cached": False, "trends": trends}

@app.post("/api/items/{item_id}/youtube-trends/refresh")
async def refresh_item_youtube_trends(item_id: int, payload: dict = None):
    item = database.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    api_key = database.get_setting("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return {"status": "error", "message": "YouTube API Key가 설정되지 않아 트렌드 조회가 불가능합니다."}
        
    # 명시적으로 전달받은 키워드가 있으면 사용, 없으면 상품명 사용
    keyword = (payload or {}).get("keyword") or item["title"]
    
    trends = fetch_youtube_trends_from_api(keyword, api_key)
    database.update_item_youtube_trends(item_id, json.dumps(trends))
    
    return {"status": "success", "trends": trends}

@app.post("/api/publish-catalog")
async def publish_catalog():
    """DB의 상품 목록을 dist/products.json에 저장하고 git push → Cloudflare 자동 배포"""
    import subprocess
    from datetime import datetime, timezone

    try:
        items = database.get_items()
        
        products = []
        for item in items:
            products.append({
                "id": item["id"],
                "name": item["title"],
                "description": item.get("description", ""),
                "short_url": item.get("short_url", ""),
                "coupang_url": item.get("coupang_url", ""),
                "video_url": item.get("r2_video_url", ""),
                "thumbnail_url": ""
            })

        catalog = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "store_name": "Momdad Fashion Diary",
            "store_description": "엄마아빠의 패션 일기 — 매일 새로운 스타일 추천",
            "products": products
        }

        dist_dir = os.path.join(BASE_DIR, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        products_path = os.path.join(dist_dir, "products.json")

        with open(products_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)

        # git add → commit → push
        subprocess.run(["git", "add", "dist/products.json"], cwd=BASE_DIR, check=True)
        commit_msg = f"🛍️ catalog: 상품 목록 업데이트 ({len(products)}개) — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=BASE_DIR, capture_output=True, text=True
        )
        
        # 변경사항이 없으면 commit이 실패할 수 있음 (정상)
        if result.returncode not in (0, 1):
            logger.error(f"Git commit error: {result.stderr}")

        push_result = subprocess.run(
            ["git", "push"],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=30
        )
        
        if push_result.returncode != 0:
            return {
                "status": "error",
                "message": f"Git push 실패: {push_result.stderr}",
                "products_count": len(products)
            }

        return {
            "status": "success",
            "message": f"{len(products)}개 상품이 배포됐습니다. Cloudflare Pages가 자동으로 업데이트됩니다.",
            "products_count": len(products),
            "updated_at": catalog["updated_at"]
        }

    except Exception as e:
        logger.error(f"Catalog publish error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=18888, reload=True)

