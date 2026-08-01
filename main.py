import os
import asyncio
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

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>개인정보 처리방침 - 엄마아빠 패션다이어리</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background: #f9f9f9; }
        .card { background: #fff; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { color: #111; border-bottom: 2px solid #eee; padding-bottom: 10px; font-size: 24px; }
        h2 { color: #444; font-size: 18px; margin-top: 25px; }
        p, li { font-size: 15px; color: #555; }
        .footer { margin-top: 30px; font-size: 13px; color: #888; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h1>개인정보 처리방침</h1>
        <p>엄마아빠 패션다이어리(이하 '회사')는 이용자의 개인정보를 중요시하며, 「개인정보 보호법」 등 관련 법령을 준수하고 있습니다.</p>
        <h2>1. 수집하는 개인정보 항목 및 목적</h2>
        <p>회사는 SNS 댓글 및 메시지 자동 응대 서비스를 제공하기 위해 최소한의 개인정보를 수집합니다.</p>
        <ul>
            <li><strong>수집 항목:</strong> 인스타그램/소셜 계정 아이디(Scoped ID), 프로필명, 댓글 텍스트 내용</li>
            <li><strong>이용 목적:</strong> 요청하신 상품 구매 링크(쿠팡 파트너스/카탈로그) 안내 및 1:1 메시지(DM) 발송</li>
        </ul>
        <h2>2. 개인정보의 보유 및 이용 기간</h2>
        <p>이용자의 개인정보는 서비스 제공 목적이 달성된 후 파기하거나, 관련 법령에 따라 일정 기간 안전하게 보관 후 파기됩니다.</p>
        <h2>3. 이용자의 권리와 행사 방법</h2>
        <p>이용자는 언제든지 자신의 개인정보 조회, 수정, 삭제(파기)를 요청할 수 있습니다.</p>
        <div class="footer">
            <p>최종 수정일: 2026년 7월 29일 | 엄마아빠 패션다이어리</p>
        </div>
    </div>
</body>
</html>"""

@app.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>서비스 이용약관 - 엄마아빠 패션다이어리</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background: #f9f9f9; }
        .card { background: #fff; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { color: #111; border-bottom: 2px solid #eee; padding-bottom: 10px; font-size: 24px; }
        h2 { color: #444; font-size: 18px; margin-top: 25px; }
        p, li { font-size: 15px; color: #555; }
        .footer { margin-top: 30px; font-size: 13px; color: #888; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h1>서비스 이용약관</h1>
        <p>본 약관은 엄마아빠 패션다이어리가 제공하는 SNS 쇼핑 카탈로그 및 자동 안내 서비스의 이용조건을 규정합니다.</p>
        <h2>1. 서비스의 목적 및 내용</h2>
        <p>본 서비스는 5060 중년층 패션 카탈로그 정보 및 쿠팡 파트너스 제휴 상품 단축 링크 안내를 목적으로 합니다.</p>
        <h2>2. 제휴 마케팅 안내</h2>
        <p>본 서비스에서 제공되는 일부 링크는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.</p>
        <div class="footer">
            <p>최종 수정일: 2026년 7월 29일 | 엄마아빠 패션다이어리</p>
        </div>
    </div>
</body>
</html>"""

@app.on_event("startup")
async def startup_event():
    try:
        from agent_engine import agent_engine
        agent_engine.start()
        logger.info("AI Agent Scheduler Engine started in background.")
    except Exception as e:
        logger.error(f"Failed to start AI Agent Engine: {e}")

    try:
        from scratch.ig_auto_responder_daemon import daemon_loop
        asyncio.create_task(daemon_loop())
        logger.info("Instagram Auto-Responder Daemon started automatically with npm run dev.")
    except Exception as e:
        logger.error(f"Failed to start IG Auto-Responder Daemon: {e}")

    try:
        from scratch.yt_auto_heart_daemon import run_yt_heart_and_like
        asyncio.create_task(run_yt_heart_and_like())
        logger.info("YouTube Auto Heart & Like Daemon started automatically with npm run dev.")
    except Exception as e:
        logger.error(f"Failed to start YouTube Auto Heart & Like Daemon: {e}")


from fastapi import Response

@app.get("/webhook/instagram")
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    verify_token = os.getenv("INSTAGRAM_VERIFY_TOKEN", "my_verify_token")
    
    if mode == "subscribe" and token == verify_token:
        logger.info(f"✅ Meta Webhook verification success! Returning challenge: {challenge}")
        return Response(content=str(challenge), media_type="text/plain")
    logger.warning(f"❌ Webhook verify token mismatch! Received: {token}, Expected: {verify_token}")
    return Response(content="Verification failed", status_code=403)

@app.post("/webhook/instagram")
@app.post("/webhook")
async def receive_webhook(request: Request):
    try:
        body = await request.json()
        logger.info(f"📩 Webhook Event Received: {json.dumps(body)}")
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook process error: {e}")
        return JSONResponse(content={"status": "error"}, status_code=400)



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

        # 이미 성공적으로 업로드된 채널인지 중복 게시 검증
        current_results_str = item.get('publish_results')
        if current_results_str:
            try:
                curr_res = json.loads(current_results_str)
                if isinstance(curr_res, dict) and curr_res.get(platform, {}).get('status') == 'success':
                    logger.info(f"Skipping {platform} for item {item_id} as it is already successfully published.")
                    results[platform] = curr_res[platform]
                    success_count += 1
                    continue
            except Exception:
                pass

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
            if res_val.get("status") == "success":
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
        # 만약 스크래핑에 실패하여 기본 대체 텍스트가 나왔거나 결과가 없는 경우 경고 상태로 리턴
        if not scraped_title or scraped_title == "엄마아빠 패션다이어리 추천 상품":
            return {
                "status": "warning", 
                "title": "", 
                "message": "상품 정보를 자동으로 가져오지 못했습니다. 아래 상품명 입력란에 직접 입력해 주세요."
            }
        return {"status": "success", "title": scraped_title}
    except Exception as e:
        logger.error(f"Failed to preview Coupang product: {e}")
        return {
            "status": "warning", 
            "title": "", 
            "message": "상품 정보를 자동으로 가져오지 못했습니다. 아래 상품명 입력란에 직접 입력해 주세요."
        }

# --- Coupang Product Recommendations APIs ---

@app.get("/api/coupang/recommendations")
async def get_coupang_recommendations():
    recs = database.get_recommended_items(status="pending")
    return {"status": "success", "recommendations": recs}

@app.post("/api/coupang/recommendations/{rec_id}/reject")
async def reject_coupang_recommendation(rec_id: int):
    database.update_recommendation_status(rec_id, "rejected")
    return {"status": "success"}

@app.post("/api/coupang/recommendations/{rec_id}/approve")
async def approve_coupang_recommendation(rec_id: int):
    rec = database.get_recommended_item(rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
        
    import recommendation_agent
    
    # 1. 쿠팡 파트너스 숏링크 실시간 생성
    logger.info(f"Generating Coupang Partners short url for: {rec['coupang_url']}")
    short_url = recommendation_agent.generate_partners_short_link(rec['coupang_url'])
    
    # 만약 발급에 실패했다면 원본 URL을 폴백으로 기입하되 숏링크 생성을 시도했다는 로그 남김
    if not short_url:
        logger.warning(f"Failed to generate Partners short link, fallback to original url.")
        short_url = rec['coupang_url']
        
    # 2. 다음 고유 상품 코드 및 번호 조회
    category = "T"
    product_code = database.get_next_product_code(category)
    product_no = database.get_next_product_no()
    
    # 3. items 테이블에 waiting_video 상태로 아이템 추가
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO items (
        product_no, title, description, coupang_url, short_url, 
        publish_status, product_code, original_video_path
    )
    VALUES (?, ?, ?, ?, ?, 'waiting_video', ?, NULL)
    """, (product_no, rec['product_name'], "에이전트가 추천한 고품질 신상품 정보입니다.", rec['coupang_url'], short_url, product_code))
    conn.commit()
    conn.close()
    
    # 4. 추천 항목 상태를 approved로 업데이트
    database.update_recommendation_status(rec_id, "approved")
    
    return {
        "status": "success", 
        "product_code": product_code, 
        "product_no": product_no,
        "item_title": rec['product_name']
    }

@app.get("/api/coupang/recommend-keywords")
async def get_recommend_keywords():
    import recommendation_agent
    kws = recommendation_agent.get_keywords_list()
    return {"status": "success", "keywords": ",".join(kws)}

@app.post("/api/coupang/recommend-keywords")
async def save_recommend_keywords(payload: dict):
    kws_str = payload.get("keywords", "").strip()
    database.set_setting("coupang_recommend_keywords", kws_str)
    return {"status": "success"}

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
        "PUBLISH_INSTAGRAM": settings.get("PUBLISH_INSTAGRAM", "true"),
        "OPENAI_API_KEY": settings.get("OPENAI_API_KEY", "")
    }

@app.post("/api/settings")
async def update_settings(payload: dict):
    for k, v in payload.items():
        if k in ["PUBLISH_YOUTUBE", "PUBLISH_TIKTOK", "PUBLISH_INSTAGRAM", "OPENAI_API_KEY"]:
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
async def manychat_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8")
        logger.info(f"Received Manychat webhook event: {body_str}")
        
        payload = {}
        if body_str:
            try:
                payload = json.loads(body_str)
            except Exception:
                # 폼 데이터 파싱 fallback
                from urllib.parse import parse_qs
                parsed = parse_qs(body_str)
                payload = {k: v[0] for k, v in parsed.items()}

        subscriber_id = payload.get("subscriber_id")
        if not subscriber_id:
            # Manychat API v1 payload 표준 subscriber.id 필드 파싱 감지
            sub_obj = payload.get("subscriber", {})
            if isinstance(sub_obj, dict):
                subscriber_id = sub_obj.get("id")
            
        post_id = payload.get("post_id")
        comment_text = payload.get("comment_text", "")
        
        logger.info(f"Parsed Manychat webhook: subscriber_id={subscriber_id}, post_id={post_id}, comment={comment_text}")
        
        if not subscriber_id:
            return JSONResponse({"status": "ignored", "reason": "No subscriber_id found in payload"})

        # 백그라운드 태스크로 연동 처리 실행 (FastAPI 응답 즉시 리턴하여 Manychat HTTP 타임아웃 방지)
        background_tasks.add_task(process_manychat_event, int(subscriber_id), post_id, comment_text)
        return {"status": "success", "message": "Webhook received and processing started in background."}
    except Exception as e:
        logger.error(f"Error processing Manychat webhook route: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def process_manychat_event(subscriber_id: int, post_id: str, comment_text: str):
    import manychat_api
    logger.info(f"Start processing Manychat event for subscriber {subscriber_id}")
    
    flow_id = os.getenv("MANYCHAT_FLOW_ID")
    if not flow_id:
        # DB 세팅값에서도 가져오기 시도
        flow_id = database.get_setting("MANYCHAT_FLOW_ID")
        
    if not flow_id:
        logger.error("MANYCHAT_FLOW_ID is not configured in .env or settings. Aborting DM dispatch.")
        database.create_agent_log(
            task_type="manychat_webhook",
            status="error",
            message="❌ [Manychat 자동화 실패] MANYCHAT_FLOW_ID 환경 변수가 구성되지 않아 메시지를 발송할 수 없습니다."
        )
        return

    # 1. 포스트 매핑 상품 조회
    matched_item = None
    if post_id:
        post_id_clean = str(post_id).strip()
        items = database.get_items()
        for it in items:
            results_str = it.get("publish_results")
            if results_str:
                try:
                    res_json = json.loads(results_str)
                    insta_res = res_json.get("instagram", {})
                    insta_post_id = str(insta_res.get("post_id", "")).strip()
                    if insta_post_id and (post_id_clean in insta_post_id or insta_post_id in post_id_clean):
                        matched_item = it
                        logger.info(f"Matched product {it['product_code']} (ID: {it['id']}) by instagram post_id: {post_id_clean}")
                        break
                except Exception:
                    continue

    # 2. 매칭 실패 시 최신 성공/예약 상품 폴백 처리
    if not matched_item:
        logger.warning(f"Failed to match product by post_id {post_id}. Fallback to latest successfully published product...")
        # success 또는 scheduled 상태인 제품 중 가장 번호가 높은 제품 1개 추출
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_no, short_url, coupang_url, product_code FROM items WHERE publish_status IN ('success', 'scheduled') ORDER BY product_no DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            matched_item = {
                "id": row[0],
                "product_no": row[1],
                "short_url": row[2],
                "coupang_url": row[3],
                "product_code": row[4]
            }
            logger.info(f"Fallback matched latest product {matched_item['product_code']} (ID: {matched_item['id']})")

    if not matched_item:
        logger.error("No product matched and fallback failed. Aborting DM dispatch.")
        database.create_agent_log(
            task_type="manychat_webhook",
            status="error",
            message="❌ [Manychat 자동화 실패] 댓글 대상 포스트에 매핑되는 상품이 없고 폴백 대상도 찾지 못했습니다."
        )
        return

    # 단축 링크 우선, 없으면 쿠팡 원본 URL 사용
    coupang_link = matched_item.get("short_url") or matched_item.get("coupang_url")
    if not coupang_link or coupang_link == "#":
        # 징검다리 주소 생성 (어르신 전용 piella 도메인 적용)
        coupang_link = f"https://6070.piella.shop/p/{matched_item['product_no']}"

    # 3. Manychat Custom User Field 갱신 API 호출
    success_field = await manychat_api.set_subscriber_custom_field(
        subscriber_id=subscriber_id,
        field_name="coupang_link",
        field_value=coupang_link
    )
    
    if not success_field:
        logger.error(f"Failed to set Custom User Field for subscriber {subscriber_id}")
        database.create_agent_log(
            task_type="manychat_webhook",
            status="error",
            message=f"❌ [Manychat 자동화 실패] 사용자 {subscriber_id}의 Custom Field(coupang_link) 갱신 API 호출이 실패했습니다."
        )
        return

    # 4. Manychat Flow 트리거 API 호출
    success_flow = await manychat_api.trigger_flow(
        subscriber_id=subscriber_id,
        flow_id=flow_id
    )
    
    if success_flow:
        logger.info(f"Manychat automation sequence successfully executed for subscriber {subscriber_id}")
        database.create_agent_log(
            task_type="manychat_webhook",
            status="success",
            message=f"💬 [Manychat 자동화 성공] 상품 {matched_item['product_code']} 링크를 사용자 {subscriber_id}의 DM으로 정상 동적 발송 완료했습니다.",
            details=json.dumps({
                "subscriber_id": subscriber_id,
                "product_code": matched_item['product_code'],
                "coupang_link": coupang_link,
                "flow_id": flow_id
            }, ensure_ascii=False)
        )
    else:
        logger.error(f"Failed to trigger Flow {flow_id} for subscriber {subscriber_id}")
        database.create_agent_log(
            task_type="manychat_webhook",
            status="error",
            message=f"❌ [Manychat 자동화 실패] 사용자 {subscriber_id}의 구매 링크 발송 Flow({flow_id}) 실행 API 호출이 실패했습니다."
        )


@app.get("/webhook/instagram")
async def instagram_webhook_verify(request: Request):
    """
    Meta Webhook 등록 시 검증용 챌린지 엔드포인트 (Hub Verification)
    """
    params = request.query_params
    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge")
    verify_token = params.get("hub.verify_token")
    
    expected_token = os.getenv("INSTAGRAM_VERIFY_TOKEN") or database.get_setting("INSTAGRAM_VERIFY_TOKEN") or "my_verify_token"
    
    if mode == "subscribe" and verify_token == expected_token:
        logger.info("Instagram Webhook verified successfully.")
        from fastapi.responses import Response
        return Response(content=challenge, media_type="text/plain")
    else:
        logger.warning("Instagram Webhook verification failed. Token mismatch.")
        raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhook/instagram")
async def instagram_webhook_event(request: Request, background_tasks: BackgroundTasks):
    """
    인스타그램 실시간 댓글 등록 이벤트를 수신하는 엔드포인트
    """
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8")
        logger.info(f"Received Instagram Webhook: {body_str}")
        
        payload = json.loads(body_str)
        
        if payload.get("object") == "instagram":
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") == "comments":
                        value = change.get("value", {})
                        comment_id = value.get("id")
                        comment_text = value.get("text", "")
                        from_user = value.get("from", {})
                        user_scoped_id = from_user.get("id")
                        media = value.get("media", {})
                        media_id = media.get("id")
                        
                        # 봇 본인이 작성한 댓글은 처리하지 않음 (무한루프 방지)
                        instagram_business_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID") or database.get_setting("INSTAGRAM_BUSINESS_ACCOUNT_ID")
                        if user_scoped_id == instagram_business_id:
                            logger.info("Ignoring comment written by the bot itself.")
                            continue
                            
                        if comment_id and user_scoped_id and media_id:
                            background_tasks.add_task(
                                process_instagram_comment_event,
                                media_id,
                                comment_id,
                                user_scoped_id,
                                comment_text
                            )
                            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error handling Instagram Webhook event: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


async def process_instagram_comment_event(media_id: str, comment_id: str, user_scoped_id: str, comment_text: str):
    """
    인스타그램 댓글 이벤트 비동기 처리 및 GPT 기반 작문/전송 프로세스
    """
    import instagram_api
    import gpt_agent
    import re
    
    logger.info(f"Start processing Instagram comment: ID={comment_id}, text='{comment_text}', media_id={media_id}")
    
    # 0. 특정 키워드 '엄마' 및 오타(엄 마, 엄머, 어마) 필터링 추가
    # 정규식 설명: '엄마', '엄 마', '엄머', '어마' 중 하나라도 포함되면 매칭
    if not re.search(r'엄\s*마|엄\s*머|어\s*마', comment_text):
        logger.info(f"Ignoring comment '{comment_text}' because it does not contain the target keywords.")
        return
        
    # 1. 미디어 캡션 조회 및 상품 번호 파싱
    caption = await instagram_api.get_media_caption(media_id)
    product_no = None
    
    if caption:
        # 본문에서 T00002, T2, No.28, No 28 등의 패턴 추출 (T 기호 또는 No. 기호 + 숫자)
        match = re.search(r'(?:[tT]|No\.?)\s*(\d+)', caption, re.IGNORECASE)
        if match:
            product_no = match.group(1)
            logger.info(f"Parsed product number {product_no} from caption: '{caption}'")
            
    # 2. DB 상품 조회
    matched_item = None
    if product_no:
        matched_item = database.get_item_by_product_no(product_no)
        
    if not matched_item:
        logger.warning(f"Failed to find product for number {product_no}. Falling back to latest published product...")
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_no, title, description, short_url, coupang_url, product_code FROM items WHERE publish_status IN ('success', 'scheduled') ORDER BY product_no DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            matched_item = {
                "id": row[0],
                "product_no": row[1],
                "title": row[2],
                "description": row[3],
                "short_url": row[4],
                "coupang_url": row[5],
                "product_code": row[6]
            }
            logger.info(f"Fallback matched latest product {matched_item['product_code']}")
            
    if not matched_item:
        logger.error("No product matched and fallback failed. Aborting comment auto-response.")
        database.create_agent_log(
            task_type="instagram_webhook",
            status="error",
            message="❌ [Instagram 자동화 실패] 댓글 대상 미디어에 매핑되는 상품이 없으며 폴백 대상도 찾지 못했습니다."
        )
        return
        
    # 3. 상품 정보 및 두 링크 구성
    title = matched_item.get("title", "인기 추천 상품")
    description = matched_item.get("description", "예쁜 코디 상품입니다.")
    
    # 1) 쿠팡 직접 구매 링크 (단축 우선, 없으면 원본)
    coupang_link = matched_item.get("short_url") or matched_item.get("coupang_url") or "https://www.coupang.com"
    # 2) 6070 전체 카탈로그 몰 메인 링크
    catalog_link = "https://6070.piella.shop"
    
    # 4. 하이브리드 비용 절감 발송 분기 (DB 템플릿 우선 사용)
    db_reply = matched_item.get("comment_reply")
    db_dm = matched_item.get("dm_template")
    
    # DB에 이미 작성된 템플릿 문구가 있다면 GPT 호출을 건너뛰어 API 비용을 0원으로 만듭니다.
    if db_reply and db_dm and db_reply.strip() != "" and db_dm.strip() != "":
        logger.info("Using pre-generated DB templates to save GPT API cost.")
        # 템플릿 내부의 플레이스홀더 치환
        reply_msg = db_reply.replace("{short_url}", coupang_link).replace("{catalog_url}", catalog_link)
        dm_msg = db_dm.replace("{short_url}", coupang_link).replace("{catalog_url}", catalog_link)
        # 인스타그램 스팸 방지를 위해 가변 조사/어투 처리 (기본 치환)
        if "{buyer_name}" in dm_msg:
            dm_msg = dm_msg.replace("{buyer_name}", "어머님")
    else:
        logger.info("DB template missing. Falling back to OpenAI GPT-4o-mini generation.")
        # 템플릿이 없는 경우에만 유료 GPT-4o-mini를 백업 가동합니다.
        gpt_result = await gpt_agent.generate_reply_and_dm_content(
            user_comment=comment_text,
            product_title=title,
            product_description=description,
            coupang_link=coupang_link,
            catalog_link=catalog_link
        )
        reply_msg = gpt_result.get("reply")
        dm_msg = gpt_result.get("dm")
    
    # 5. 인스타그램 답글 및 오피셜 Private DM 100% 즉시 발송
    success_reply = await instagram_api.send_comment_reply(comment_id, reply_msg)
    product_code = matched_item.get('product_code', '29')
    success_dm = await instagram_api.send_instagram_dm_by_comment(comment_id, str(product_code))

    
    if success_reply and success_dm:
        logger.info("Successfully replied and sent DM to user.")
        database.create_agent_log(
            task_type="instagram_webhook",
            status="success",
            message=f"💬 [Instagram 자동화 성공] 상품 {matched_item.get('product_code')} 관련 대댓글 및 DM 발송 완료.",
            details=json.dumps({
                "comment_id": comment_id,
                "user_scoped_id": user_scoped_id,
                "product_code": matched_item.get("product_code"),
                "reply": reply_msg,
                "dm": dm_msg
            }, ensure_ascii=False)
        )
    else:
        logger.error(f"Automation partial failure. Reply success: {success_reply}, DM success: {success_dm}")
        database.create_agent_log(
            task_type="instagram_webhook",
            status="error",
            message=f"⚠️ [Instagram 자동화 부분 실패] 대댓글 성공: {success_reply}, DM 성공: {success_dm}",
            details=json.dumps({
                "comment_id": comment_id,
                "user_scoped_id": user_scoped_id,
                "reply": reply_msg,
                "dm": dm_msg
            }, ensure_ascii=False)
        )


@app.get("/api/youtube/login")
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

