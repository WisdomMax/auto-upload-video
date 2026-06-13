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
import youtube_comments

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# 현재 프로젝트 .env 로드
load_dotenv()


app = FastAPI(title="SNS Automation & Video Auto-Publisher")

@app.on_event("startup")
async def startup_event():
    try:
        from agent_engine import agent_engine
        agent_engine.start()
        logger.info("AI Agent Scheduler Engine started in background.")
    except Exception as e:
        logger.error(f"Failed to start AI Agent Engine: {e}")

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
    path = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
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

async def generate_ai_sns_content(item_id: int):
    from agent_engine import agent_engine
    await agent_engine._generate_intelligent_caption(item_id)

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
def publish_post_via_buffer(profile_id: str, text: str, video_url: str, service_type: str, title: str = None, scheduled_at: str = None) -> dict:
    access_token = os.getenv("BUFFER_ACCESS_TOKEN") or database.get_setting("BUFFER_ACCESS_TOKEN")
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
    }

    if scheduled_at:
        post_input["schedulingType"] = "automatic"
        post_input["mode"] = "customScheduled"
        post_input["dueAt"] = scheduled_at
    else:
        post_input["schedulingType"] = "automatic"
        post_input["mode"] = "shareNow"

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
            "privacy": "public",
            "categoryId": "22"
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
    access_token = os.getenv("BUFFER_ACCESS_TOKEN") or database.get_setting("BUFFER_ACCESS_TOKEN")
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

    fixed_yt_id = database.get_setting("YOUTUBE_PROFILE_ID") or os.getenv("YOUTUBE_PROFILE_ID")
    fixed_tt_id = database.get_setting("TIKTOK_PROFILE_ID") or os.getenv("TIKTOK_PROFILE_ID")
    fixed_ig_id = database.get_setting("INSTAGRAM_PROFILE_ID") or os.getenv("INSTAGRAM_PROFILE_ID")

    for platform in platforms:
        # 대응되는 Buffer 채널 탐색
        target_channel = None
        
        # 1. 고정 ID 매칭 시도
        if platform == 'youtube' and fixed_yt_id:
            for p in profiles:
                if p['id'] == fixed_yt_id:
                    target_channel = p
                    break
        elif platform == 'tiktok' and fixed_tt_id:
            for p in profiles:
                if p['id'] == fixed_tt_id:
                    target_channel = p
                    break
        elif platform == 'instagram' and fixed_ig_id:
            for p in profiles:
                if p['id'] == fixed_ig_id:
                    target_channel = p
                    break
                    
        # 2. 고정 ID 매칭 실패 혹은 미설정 시 기본 서비스명 매칭
        if not target_channel:
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
        elif platform == 'tiktok':
            text = item['sns_caption'] + "\n\n(채널 프로필 홈에 연결된 링크를 클릭하시면 모든 제품의 구매 링크를 편리하게 확인하실 수 있습니다)"
        elif platform == 'instagram':
            text = item['sns_caption'] + "\n\n(전체 제품 링크는 홈페이지: auto-upload-video.pages.dev 에서 확인하실 수 있습니다)"

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

# 완전 자동화 백그라운드 파이프라인 함수
async def auto_process_pipeline_task(item_id: int, auto_publish: bool):
    logger.info(f"Starting auto-processing pipeline for item {item_id}")
    
    # DB에서 최신 아이템 획득
    item = database.get_item(item_id)
    if not item:
        logger.error(f"Item {item_id} not found in database.")
        return
        
    product_no = item['product_no']
    coupang_url = item['coupang_url']
    current_title = item.get('title')
    
    # 기존에 유효한 상품명이 지정되어 있는지 검사
    is_default_title = current_title in ["엄마아빠 패션다이어리 추천 상품", "쿠팡 추천 상품", None, ""]
    
    if is_default_title:
        # Step 1: 쿠팡 크롤링 상품명 추출 (기본 타이틀 상태인 경우에만 1회 시도)
        from coupang_scraper import scrape_coupang_product
        scraped_title = await scrape_coupang_product(coupang_url)
        
        # DB에 크롤링한 상품명 및 설명 업데이트 (디폴트 타이틀이 아닐 때만)
        if scraped_title and scraped_title not in ["엄마아빠 패션다이어리 추천 상품", "쿠팡 추천 상품"]:
            scraped_description = f"{scraped_title}의 솔직 후기 및 가성비 추천 정보입니다."
            try:
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE items SET title = ?, description = ? WHERE id = ?", (scraped_title, scraped_description, item_id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to update title/desc for item {item_id}: {e}")
        else:
            logger.info(f"Using existing title for item {item_id}: {current_title} (Scraping skipped in auto_process)")
            
        # 최신화된 아이템 정보 다시 가져오기 및 NameError 방지 바인딩
        item = database.get_item(item_id)
        scraped_title = item.get('title')
        scraped_description = item.get('description') or f"{scraped_title}의 솔직 후기 및 가성비 추천 정보입니다."

    # Step 2: 쿠팡 파트너스 링크 단축 시도
    coupang_access = database.get_setting("COUPANG_ACCESS_KEY") or os.getenv("COUPANG_ACCESS_KEY")
    coupang_secret = database.get_setting("COUPANG_SECRET_KEY") or os.getenv("COUPANG_SECRET_KEY")
    
    short_url = ""
    if coupang_access and coupang_secret:
        short_url = get_coupang_short_link(coupang_url, coupang_access, coupang_secret)
        if short_url:
            database.update_item_coupang_urls(item_id, coupang_url, short_url)
            
    # Step 3: 지능형 캡션/콘텐츠 자동 완성 호출 (agent_engine의 일관된 로직 활용)
    from agent_engine import agent_engine
    await agent_engine._generate_intelligent_caption(item_id)
    
    # 에이전트 로그 작성
    database.create_agent_log(
        task_type="system",
        status="success",
        message=f"🤖 [자동 정보 수집 완료] No. {product_no} 상품의 크롤링 및 유튜브/SNS 캡션 자동 생성이 완료되었습니다."
    )
    
    # Step 4: 자동 배포 예약이 켜진 경우 R2 업로드 및 Buffer 배포 즉시 가동
    if auto_publish:
        logger.info(f"Triggering auto-publishing for item {item_id}")
        distribute_video_task(item_id, ["youtube", "tiktok", "instagram"])


@app.post("/api/items")
async def add_item(
    coupang_url: str = Form(...),
    video: UploadFile = File(...),
    auto_publish: bool = Form(False),
    title: str = Form(None),
    background_tasks: BackgroundTasks = None
):
    # product_no 자동 발급
    product_no = database.get_next_product_no()
    
    # 임시 제목 및 설명으로 업로드 우선 완료 처리
    temp_title = title if title else f"No. {product_no} 쿠팡 상품 (정보 수집 중...)"
    temp_desc = "백엔드에서 쿠팡 상품 상세 페이지 크롤링이 진행 중입니다."
    
    original_filename = f"prod_{product_no}_{video.filename}"
    original_path = os.path.join(ORIGINALS_DIR, original_filename)
    
    with open(original_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
        
    # DB 아이템 생성
    item_id = database.create_item(
        product_no=product_no,
        title=temp_title,
        description=temp_desc,
        coupang_url=coupang_url,
        original_video_path=original_path
    )
    
    # 크롤링, 캡션빌드, 자동 업로드/배포 전체 프로세스를 백그라운드에서 논스톱 실행
    background_tasks.add_task(auto_process_pipeline_task, item_id, auto_publish)
    
    return {"status": "success", "item_id": item_id, "product_no": product_no}

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
async def update_short_link(item_id: int, payload: dict, background_tasks: BackgroundTasks = None):
    short_url = payload.get("short_url", "")
    coupang_url = payload.get("coupang_url", "")
    description = payload.get("description", "")
    title = payload.get("title", "")
    
    item = database.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    new_coupang_url = coupang_url if coupang_url else item['coupang_url']
    
    # 쿠팡 원본 주소 사후 입력 시 단축 링크 자동 생성
    if new_coupang_url and not short_url:
        coupang_access = database.get_setting("COUPANG_ACCESS_KEY") or os.getenv("COUPANG_ACCESS_KEY")
        coupang_secret = database.get_setting("COUPANG_SECRET_KEY") or os.getenv("COUPANG_SECRET_KEY")
        if coupang_access and coupang_secret:
            short_url = get_coupang_short_link(new_coupang_url, coupang_access, coupang_secret)
            
    database.update_item_coupang_urls(item_id, new_coupang_url, short_url)
    
    # 링크가 등록/수정되었으므로 배포 상태를 대기(pending)로 초기화하고 이전 실패 로그를 제거합니다.
    database.update_item_publish_results(item_id, 'pending', None)
    
    # 상품 제목(title) 업데이트
    if title:
        try:
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE items SET title = ? WHERE id = ?", (title, item_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update title for item {item_id}: {e}")

    # 추가 설명(description) 업데이트
    if description is not None:
        try:
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE items SET description = ? WHERE id = ?", (description, item_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update description for item {item_id}: {e}")
            
    # 링크 변경 시 콘텐츠 자동 재생성
    await generate_ai_sns_content(item_id)
    
    # 정적 웹 카탈로그 즉시 갱신
    import importlib
    import catalog_builder
    importlib.reload(catalog_builder)
    catalog_builder.build_catalog()
    
    # Cloudflare Pages 원격 배포 가동 (git push)
    if background_tasks:
        background_tasks.add_task(publish_catalog)
    
    return {"status": "success"}

@app.post("/api/items/{item_id}/regenerate")
async def regenerate_contents(item_id: int):
    item = database.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    await generate_ai_sns_content(item_id)
    return {"status": "success", "item": database.get_item(item_id)}

@app.get("/api/coupang/preview")
async def coupang_preview(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL을 입력해 주세요.")
        
    import coupang_scraper
    try:
        scraped_title = await coupang_scraper.scrape_coupang_product(url)
        if scraped_title == "엄마아빠 패션다이어리 추천 상품":
            return {"status": "error", "message": "상품 정보를 자동으로 가져오지 못했습니다. 직접 입력해 주세요."}
        return {"status": "success", "title": scraped_title}
    except Exception as e:
        logger.error(f"Failed to preview Coupang product: {e}")
        return {"status": "error", "message": str(e)}

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
    return {
        "PUBLISH_YOUTUBE": settings.get("PUBLISH_YOUTUBE", "true"),
        "PUBLISH_TIKTOK": settings.get("PUBLISH_TIKTOK", "true"),
        "PUBLISH_INSTAGRAM": settings.get("PUBLISH_INSTAGRAM", "true")
    }

@app.post("/api/settings")
async def update_settings(payload: dict):
    for k, v in payload.items():
        if k in ["PUBLISH_YOUTUBE", "PUBLISH_TIKTOK", "PUBLISH_INSTAGRAM"]:
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
    import importlib
    from datetime import datetime, timezone
    import catalog_builder

    try:
        # 정적 웹 카탈로그 갱신 빌드 실행 (index.html 및 products.json 정상 포맷 출력)
        importlib.reload(catalog_builder)
        catalog_builder.build_catalog()
        
        items = database.get_items()

        # git add → commit → push
        subprocess.run(["git", "add", "dist/products.json", "dist/index.html", "static/thumbnails/", "dist/static/thumbnails/"], cwd=BASE_DIR, check=True)
        commit_msg = f"🛍️ catalog: 상품 목록 업데이트 ({len(items)}개) — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=BASE_DIR, capture_output=True, text=True
        )
        
        # 변경사항이 없으면 commit이 실패할 수 있음 (정상)
        if result.returncode not in (0, 1):
            logger.error(f"Git commit error: {result.stderr}")

        # GITHUB_TOKEN이 있으면 인증 주입하여 백그라운드 푸시 실행
        github_token = os.getenv("GITHUB_TOKEN") or database.get_setting("GITHUB_TOKEN")
        if github_token:
            try:
                get_url = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=BASE_DIR, capture_output=True, text=True, check=True
                )
                origin_url = get_url.stdout.strip()
                if "github.com" in origin_url and "@" not in origin_url:
                    auth_url = origin_url.replace("https://", f"https://{github_token}@")
                    push_result = subprocess.run(
                        ["git", "push", auth_url, "main"],
                        cwd=BASE_DIR, capture_output=True, text=True, timeout=30
                    )
                else:
                    push_result = subprocess.run(
                        ["git", "push"],
                        cwd=BASE_DIR, capture_output=True, text=True, timeout=30
                    )
            except Exception as e_git:
                logger.error(f"Git push token insertion failed: {e_git}")
                push_result = subprocess.run(
                    ["git", "push"],
                    cwd=BASE_DIR, capture_output=True, text=True, timeout=30
                )
        else:
            push_result = subprocess.run(
                ["git", "push"],
                cwd=BASE_DIR, capture_output=True, text=True, timeout=30
            )
        
        if push_result.returncode != 0:
            return {
                "status": "error",
                "message": f"Git push 실패: {push_result.stderr}",
                "products_count": len(items)
            }

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        return {
            "status": "success",
            "message": f"{len(items)}개 상품이 배포됐습니다. Cloudflare Pages가 자동으로 업데이트됩니다.",
            "products_count": len(items),
            "updated_at": now_str
        }

    except Exception as e:
        logger.error(f"Catalog publish error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- User & Agent integration routes ---

@app.get("/p/{product_no}", response_class=HTMLResponse)
async def get_user_product_catalog(product_no: int, request: Request):
    # DB에서 product_no를 가진 아이템 탐색
    items = database.get_items()
    item = None
    for it in items:
        if it.get("product_no") == product_no:
            item = it
            break
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # 비디오 경로 파싱 (R2 우선, 로컬 uploads 차선)
    video_src = item.get("r2_video_url")
    if not video_src and item.get("original_video_path"):
        import re
        # 로컬 경로 절대/상대 매핑 변환
        video_src = re.sub(r'^.*uploads/', '/uploads/', item["original_video_path"])
        if not video_src.startswith("/uploads/"):
            video_src = "/uploads/originals/" + os.path.basename(item["original_video_path"])
    
    # 쿠팡 구매 링크 (단축 링크 우선, 원본 차선)
    purchase_link = item.get("short_url") or item.get("coupang_url") or "#"
    
    return templates.TemplateResponse("catalog_detail.html", {
        "request": request,
        "item": item,
        "video_src": video_src,
        "purchase_link": purchase_link
    })


@app.post("/api/manychat/webhook")
async def manychat_webhook(payload: dict):
    logger.info(f"ManyChat Webhook received payload: {payload}")
    
    subscriber_id = payload.get("subscriber_id") or payload.get("subscriber", {}).get("id")
    username = payload.get("username") or payload.get("subscriber", {}).get("username") or payload.get("subscriber", {}).get("first_name", "고객")
    product_no = payload.get("product_no")
    platform = payload.get("platform") or "instagram"
    
    if not subscriber_id:
        return {"status": "error", "message": "subscriber_id가 누락되었습니다."}
        
    item = None
    if product_no:
        item = database.get_item_by_product_no(product_no)
        
    token = os.getenv("MANYCHAT_API_TOKEN") or database.get_setting("MANYCHAT_API_TOKEN")
    
    if not token or token == "your_manychat_api_token_here":
        logger.warning("ManyChat API Token이 설정되어 있지 않아 실제 DM 발송을 스킵합니다.")
        database.create_agent_log(
            task_type="manychat_event",
            status="warning",
            message=f"ManyChat 토큰 미설정으로 실제 DM 발송 실패: {platform.upper()} 유저 @{username} (No. {product_no})",
            details=json.dumps(payload, ensure_ascii=False)
        )
        return {"status": "success", "message": "ManyChat API Token is not set."}
        
    dm_text = ""
    target_link = ""
    
    if item:
        target_link = item.get("short_url") or item.get("coupang_url")
        if not target_link:
            target_link = f"http://localhost:18888/p/{item['product_no']}"
            
        template = item.get("dm_template") or ""
        if template:
            if "👇 쿠팡 즉시구매 링크" in template and target_link not in template:
                dm_text = template.strip() + "\n" + target_link
            else:
                dm_text = template.replace("[쿠팡 링크]", target_link).replace("구매 링크:", f"구매 링크: {target_link}").strip()
                if target_link not in dm_text:
                    dm_text += f"\n\n👇 제품 링크:\n{target_link}"
        else:
            dm_text = f"요청하신 제품 상세 정보 및 구매 링크입니다.\n\n👇 제품 링크:\n{target_link}"
    else:
        dm_text = f"안녕하세요! 요청하신 상품 정보를 찾지 못했습니다. 번호를 다시 한번 확인해 주세요."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    api_payload = {
        "subscriber_id": subscriber_id,
        "data": {
            "version": "v2",
            "content": {
                "messages": [
                    {
                        "type": "text",
                        "text": dm_text
                    }
                ]
            }
        }
    }
    
    try:
        res = requests.post("https://api.manychat.com/fb/sending/sendContent", json=api_payload, headers=headers, timeout=10)
        
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("status") == "success":
                message = f"{platform.upper()} 유저 @{username} 님께 DM 전송 성공"
                if product_no:
                    message += f" (No. {product_no} 상품)"
                
                database.create_agent_log(
                    task_type="manychat_event",
                    status="success",
                    message=message,
                    details=json.dumps(payload, ensure_ascii=False)
                )
                return {"status": "success"}
            else:
                error_msg = res_data.get("message", "알 수 없는 오류")
                logger.error(f"ManyChat API Send Failed: {error_msg}")
        else:
            logger.error(f"ManyChat API HTTP Error: {res.status_code} - {res.text}")
            
        database.create_agent_log(
            task_type="manychat_event",
            status="failed",
            message=f"ManyChat API 전송 실패: @{username} (No. {product_no})",
            details=json.dumps({"payload": payload, "response": res.text}, ensure_ascii=False)
        )
        return {"status": "failed", "message": "ManyChat API sending failed."}
        
    except Exception as e:
        logger.error(f"ManyChat webhook execution error: {e}")
        database.create_agent_log(
            task_type="manychat_event",
            status="failed",
            message=f"ManyChat 연동 중 예외 발생: {str(e)}",
            details=json.dumps(payload, ensure_ascii=False)
        )
        return {"status": "error", "detail": str(e)}


@app.get("/api/youtube/auth")
async def youtube_auth():
    flow = youtube_comments.get_oauth_flow()
    if not flow:
        raise HTTPException(status_code=400, detail="YouTube OAuth설정이 누락되었습니다. 클라이언트 ID와 Secret 또는 client_secrets.json을 준비해 주세요.")
    
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    
    # 생성된 일회용 PKCE 검증 키를 글로벌 메모리에 캐시
    youtube_comments._oauth_code_verifier = flow.code_verifier
    
    return JSONResponse({"url": authorization_url})


@app.get("/api/youtube/callback")
async def youtube_callback(request: Request, code: str = None, error: str = None):
    if error:
        return HTMLResponse(f"<h3>인증 실패: {error}</h3>")
    if not code:
        raise HTTPException(status_code=400, detail="Code parameter is missing")
        
    try:
        flow = youtube_comments.get_oauth_flow()
        if not flow:
            return HTMLResponse("<h3>유튜브 설정 로드 실패</h3>")
            
        # 캐싱된 PKCE 검증 키 주입
        if youtube_comments._oauth_code_verifier:
            flow.code_verifier = youtube_comments._oauth_code_verifier
            
        flow.fetch_token(code=code)
        credentials = flow.credentials
        youtube_comments.save_credentials(credentials)
        
        # 채널 ID가 아직 설정 안 되어 있으면 가져와서 자동 등록 시도
        try:
            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", credentials=credentials)
            ch_res = youtube.channels().list(part="id,snippet", mine=True).execute()
            if ch_res.get("items"):
                channel_id = ch_res["items"][0]["id"]
                database.set_setting("YOUTUBE_CHANNEL_ID", channel_id)
        except Exception as ex:
            logger.error(f"Failed to auto-save channel id: {ex}")
            
        return HTMLResponse("""
            <html>
            <body onload="window.close(); window.opener.location.reload();">
                <h2>유튜브 연동 성공!</h2>
                <p>창이 자동으로 닫힙니다...</p>
            </body>
            </html>
        """)
    except Exception as e:
        logger.error(f"Callback processing failed: {e}", exc_info=True)
        return HTMLResponse(f"<h3>콜백 처리 중 오류 발생: {str(e)}</h3>")


@app.get("/api/youtube/status")
async def youtube_status():
    creds = youtube_comments.get_credentials()
    has_token = creds is not None
    channel_id = database.get_setting("YOUTUBE_CHANNEL_ID") or ""
    return {
        "connected": has_token,
        "channel_id": channel_id,
        "token_expired": creds.expired if creds else False
    }


@app.get("/api/agent/logs")
async def get_agent_activity_logs():
    logs = database.get_agent_logs(limit=30)
    return logs


@app.post("/api/agent/trigger")
async def trigger_agent_manually(background_tasks: BackgroundTasks):
    try:
        from agent_engine import agent_engine
        # BackgroundTasks를 사용하여 가비지 컬렉션 위험 방지 및 안전한 백그라운드 구동
        background_tasks.add_task(agent_engine.run_once)
        return {"status": "success", "message": "에이전트 루틴 즉시 실행이 예약되었습니다."}
    except Exception as e:
        logger.error(f"Manual agent trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/scan")
async def trigger_scan_manually(background_tasks: BackgroundTasks):
    try:
        from agent_engine import agent_engine
        # 백그라운드 태스크로 input 디렉토리 비디오 스캔만 1회 강제 실행 기동
        background_tasks.add_task(agent_engine._scan_input_directory)
        return {"status": "success", "message": "비디오 스캔 즉시 실행이 예약되었습니다."}
    except Exception as e:
        logger.error(f"Manual scan trigger error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=18888, reload=False)

