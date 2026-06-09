import asyncio
import logging
import json
import os
import requests
from datetime import datetime, timedelta, timezone
import database
import youtube_comments

logger = logging.getLogger("agent_engine")

class AIAgentEngine:
    def __init__(self):
        # 10분(600초) 주기로 깨어나서 시간 조건을 매칭
        self.interval = 600
        self.task = None
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._loop())
            logger.info("AI Agent Scheduler loop started.")

    def stop(self):
        if self.is_running and self.task:
            self.task.cancel()
            self.is_running = False
            logger.info("AI Agent Scheduler loop stopped.")

    async def _loop(self):
        # 서버 시작 시 유예 시간
        await asyncio.sleep(5)
        
        # 정밀 스케줄링을 위한 당일 실행 체크 상태값
        last_yt_check_date = None       # 예: "2026-06-08"
        last_scan_date_hour = None      # 예: "2026-06-08 05" 또는 "2026-06-08 17"
        last_manychat_brief_hour = None # 예: "2026-06-08 09"
        last_publish_date = None        # 예: "2026-06-08"
        
        while self.is_running:
            try:
                # KST (UTC+9) 기준 현재 시각 구하기
                kst_tz = timezone(timedelta(hours=9))
                now_kst = datetime.now(kst_tz)
                today_str = now_kst.strftime("%Y-%m-%d")
                hour = now_kst.hour
                
                # 1. 유튜브 댓글 검사 및 대댓글 답글: 매일 오후 8시 (20:00 KST)에 1회 구동
                if hour == 20:
                    if last_yt_check_date != today_str:
                        logger.info("[오후 8시 정기 유튜브 점검] 댓글 검사 및 자동 대댓글 작성 실행...")
                        database.create_agent_log(
                            task_type="system",
                            status="success",
                            message="[오후 8시 정기 유튜브 댓글 검사] 자동 대댓글 대응 프로세스를 가동합니다."
                        )
                        await self._monitor_youtube_comments()
                        last_yt_check_date = today_str
                
                # 2. input 폴더 비디오 스캔 및 등록: 매일 오전 5시 (05:00 KST) & 오후 5시 (17:00 KST) 각각 1회 구동
                if hour in [5, 17]:
                    hour_key = f"{today_str} {hour:02d}"
                    if last_scan_date_hour != hour_key:
                        logger.info(f"[정기 비디오 스캔] KST {hour:02d}시 비디오 input 폴더 스캔 실행...")
                        database.create_agent_log(
                            task_type="system",
                            status="success",
                            message=f"[KST {hour:02d}시 정기 비디오 스캔] /input 폴더 내 새로운 영상 처리를 개시합니다."
                        )
                        await self._scan_input_directory()
                        last_scan_date_hour = hour_key
                        
                # 3. ManyChat 실적 브리핑: 1시간에 1번씩 로그 체크하여 처리
                manychat_hour_key = f"{today_str} {hour:02d}"
                if last_manychat_brief_hour != manychat_hour_key:
                    await self._summarize_manychat_events()
                    last_manychat_brief_hour = manychat_hour_key
                    
                # 4. 정기 배포 대기열 예약 동기화 실행: 매일 오후 6시 (18:00 KST)에 1회 구동
                if hour == 18:
                    if last_publish_date != today_str:
                        logger.info("[오후 6시 정기 배포 실행] 대기 중인 상품 일괄 배포 예약 개시...")
                        database.create_agent_log(
                            task_type="system",
                            status="success",
                            message="[오후 6시 정기 배포 가동] 쿠팡 링크가 등록된 대기 영상을 순차적으로 Buffer에 예약 등록합니다."
                        )
                        await self._check_and_publish_pending_items()
                        last_publish_date = today_str

            except Exception as e:
                logger.error(f"Error in Agent Scheduler loop: {e}", exc_info=True)
                
            await asyncio.sleep(self.interval)

    async def _scan_input_directory(self):
        import time
        base_dir = os.path.dirname(os.path.abspath(__file__))
        input_dir = os.path.join(base_dir, "input")
        if not os.path.exists(input_dir):
            os.makedirs(input_dir, exist_ok=True)
            return

        # 1. DB settings에서 이미 처리 완료된 파일명 캐시 로드
        processed_files_str = database.get_setting("processed_input_files", "[]")
        try:
            processed_files = json.loads(processed_files_str)
        except Exception:
            processed_files = []

        # 2. 파일 리스트 중 아직 스캔 처리되지 않은 신규 파일만 선별
        all_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.mp4', '.mov', '.avi'))]
        new_files = [f for f in all_files if f not in processed_files]

        if not new_files:
            logger.info("No new video files found in /input directory.")
        else:
            import video_agent
            import catalog_builder

            for file_name in new_files:
                video_path = os.path.join(input_dir, file_name)
                logger.info(f"New video detected in input: {video_path}")
                
                try:
                    # 1) 비디오 파이프라인 실행 (Gemini 분석, 코드 발급, 자막 오버레이, webp 썸네일 캡처)
                    result = await video_agent.process_video_pipeline(video_path)
                    
                    # 2) DB에 아이템 최초 인서트 (쿠팡 주소는 빈 상태)
                    item_id = database.create_item(
                        product_no=result["product_no"],
                        title=result["title"],
                        description=result["description"],
                        coupang_url="",
                        original_video_path=result["original_video_path"],
                        product_code=result["product_code"]
                    )
                    
                    # 3) SNS 본문 글 및 유튜브 캡션 자동 생성 (Fallback 자동완성)
                    from main import generate_ai_sns_content
                    generate_ai_sns_content(item_id)
                    
                    # 4) 처리 완료 목록에 추가 및 DB 캐시 갱신 (즉시 영상 파일을 지우지 않음!)
                    processed_files.append(file_name)
                    database.set_setting("processed_input_files", json.dumps(processed_files))
                    logger.info(f"Marked input file as processed: {file_name} (Preserving for 7 days)")
                    
                    # 5) 정적 카탈로그 index.html 빌더 실행
                    catalog_builder.build_catalog()
                    
                    database.create_agent_log(
                        task_type="video_scan",
                        status="success",
                        message=f"📹 [비디오 감지 완료] 코드 {result['product_code']} 상품의 자막 합성 및 webp 썸네일 생성이 완료되었습니다. 대시보드에서 쿠팡 링크 입력을 기다리는 대기 상태로 등록되었습니다."
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing input file {file_name}: {e}", exc_info=True)
                    database.create_agent_log(
                        task_type="video_scan",
                        status="failed",
                        message=f"❌ [비디오 처리 실패] 파일 {file_name} 처리 중 오류 발생: {str(e)}"
                    )

        # 3. 보관 기간이 7일 이상 경과한 오래된 영상 파일만 안전하게 순차 정리
        try:
            now_sec = time.time()
            limit_sec = 7 * 24 * 3600  # 7일 초 단위
            updated_processed_files = processed_files.copy()
            
            for file_name in all_files:
                file_path = os.path.join(input_dir, file_name)
                if os.path.exists(file_path):
                    mtime = os.path.getmtime(file_path)
                    age_sec = now_sec - mtime
                    if age_sec >= limit_sec:
                        os.remove(file_path)
                        logger.info(f"🗑️ Removed input file older than 7 days: {file_name}")
                        if file_name in updated_processed_files:
                            updated_processed_files.remove(file_name)
                            
            if updated_processed_files != processed_files:
                database.set_setting("processed_input_files", json.dumps(updated_processed_files))
        except Exception as cleanup_err:
            logger.error(f"Failed to cleanup older input files: {cleanup_err}")

    async def _schedule_item_on_buffer(self, item_id):
        item = database.get_item(item_id)
        if not item:
            return

        # 쿠팡 원본 URL 정보가 비어 있는 경우 배포 예약을 강제 스킵 (링크 미등록 방지)
        if not item.get("coupang_url") or item.get("coupang_url") == "":
            logger.warning(f"Coupang URL is missing for item {item_id}. Skipping Buffer scheduling.")
            return

        r2_url = item.get('r2_video_url')
        if not r2_url:
            try:
                from main import upload_video_to_r2
                r2_url = upload_video_to_r2(item['original_video_path'], item['product_no'])
                database.update_item_r2_url(item_id, r2_url)
            except Exception as e:
                logger.error(f"R2 Upload Exception: {e}")
                database.update_item_publish_results(item_id, "failed", json.dumps({"error": f"R2 업로드 실패: {str(e)}"}))
                return

        access_token = os.getenv("BUFFER_ACCESS_TOKEN") or database.get_setting("BUFFER_ACCESS_TOKEN")
        if not access_token:
            logger.warning("Buffer Access Token is missing. Skipping Buffer scheduling.")
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
            return

        # 예약 타임슬롯 계산 (매일 저녁 6시 KST = 18:00 KST = 09:00 UTC)
        items = database.get_items()
        future_scheduled = []
        now_utc = datetime.now(timezone.utc)
        
        for it in items:
            if it.get("publish_status") not in ("scheduled", "partial_failed"):
                continue
            sch_str = it.get("scheduled_at")
            if sch_str:
                try:
                    sch_dt = datetime.fromisoformat(sch_str.replace("Z", "+00:00"))
                    if sch_dt > now_utc:
                        future_scheduled.append(sch_dt)
                except Exception:
                    pass
                    
        future_scheduled.sort()
        
        if future_scheduled:
            last_sch = future_scheduled[-1]
            next_sch = last_sch + timedelta(days=1)
        else:
            kst_tz = timezone(timedelta(hours=9))
            now_kst = datetime.now(kst_tz)
            today_18_kst = now_kst.replace(hour=18, minute=0, second=0, microsecond=0)
            
            if now_kst < today_18_kst:
                next_sch = today_18_kst.astimezone(timezone.utc)
            else:
                next_sch = (today_18_kst + timedelta(days=1)).astimezone(timezone.utc)
                
        scheduled_at_str = next_sch.strftime("%Y-%m-%dT%H:%M:%SZ")

        results = {}
        success_count = 0
        failed_count = 0
        enabled_platforms = []
        if database.get_setting("PUBLISH_YOUTUBE", "true") == "true":
            enabled_platforms.append("youtube")
        if database.get_setting("PUBLISH_TIKTOK", "true") == "true":
            enabled_platforms.append("tiktok")
        if database.get_setting("PUBLISH_INSTAGRAM", "true") == "true":
            enabled_platforms.append("instagram")

        platforms = enabled_platforms if enabled_platforms else ["youtube", "tiktok", "instagram"]


        for platform in platforms:
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

            text = item.get('sns_caption', '')
            title = item.get('title', '')
            if platform == 'youtube':
                text = item.get('youtube_description', '')
                title = item.get('youtube_title') or item.get('title', '')

            try:
                from main import publish_post_via_buffer
                res_val = publish_post_via_buffer(
                    profile_id=target_channel['id'],
                    text=text,
                    video_url=r2_url,
                    service_type=target_channel['service'],
                    title=title,
                    scheduled_at=scheduled_at_str
                )
                results[platform] = res_val
                if res_val["status"] == "success":
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                results[platform] = {"status": "error", "message": str(e)}
                failed_count += 1

        final_status = "scheduled" if success_count > 0 else "failed"
        if failed_count > 0 and success_count > 0:
            final_status = "partial_failed"
            
        database.update_item_publish_results(item_id, final_status, json.dumps(results))
        database.update_item_scheduled_at(item_id, scheduled_at_str)
        
        kst_time_str = next_sch.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
        database.create_agent_log(
            task_type="buffer_schedule",
            status="success" if final_status == "scheduled" else "failed",
            message=f"📅 [Buffer 배포 예약 완료] 상품 코드: {item.get('product_code') or ('No.'+str(item['product_no']))} -> 예약 시간: {kst_time_str} KST (채널 {success_count}개 예약 완료)"
        )

    async def _check_and_publish_pending_items(self):
        items = database.get_items()
        
        # 중요: publish_status가 pending이면서 coupang_url이 채워진 항목들만 필터링해서 예약을 수행
        pending_items = [
            it for it in items 
            if it.get("publish_status") == "pending" 
            and it.get("coupang_url") 
            and it.get("coupang_url") != ""
        ]

        if not pending_items:
            return

        # ID 오름차순(오래된 상품 순)으로 정렬하여 먼저 등록된 상품이 빠른 날짜에 배포 예약되게 함
        pending_items.sort(key=lambda x: x["id"])

        for item in pending_items:
            await self._schedule_item_on_buffer(item["id"])

    async def _monitor_youtube_comments(self):
        try:
            logger.info("Running OAuth2 YouTube comment check...")
            await asyncio.to_thread(youtube_comments.check_and_reply_to_comments)
        except Exception as e:
            logger.error(f"Failed to run OAuth2 comment check: {e}")

        # Fallback API Key 모니터링 로그 기록
        from dotenv import dotenv_values
        import pathlib
        project_env = pathlib.Path(__file__).parent / ".env"
        env_vars = dotenv_values(project_env) if project_env.exists() else {}

        api_key = os.getenv("YOUTUBE_API_KEY") or env_vars.get("YOUTUBE_API_KEY") or database.get_setting("YOUTUBE_API_KEY")
        channel_id = os.getenv("YOUTUBE_CHANNEL_ID") or env_vars.get("YOUTUBE_CHANNEL_ID") or database.get_setting("YOUTUBE_CHANNEL_ID")

        if not api_key or not channel_id:
            return

        url = f"https://www.googleapis.com/youtube/v3/commentThreads?allThreadsRelatedToChannelId={channel_id}&key={api_key}&part=snippet&maxResults=10"
        try:
            res = await asyncio.to_thread(requests.get, url, timeout=10)
            if res.status_code != 200:
                logger.error(f"YouTube API Error during agent monitoring: {res.text}")
                return

            data = res.json()
            now = datetime.now(timezone.utc)
            new_comment_count = 0

            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                top_comment = snippet.get("topLevelComment", {}).get("snippet", {})
                published_at_str = top_comment.get("publishedAt")
                
                if not published_at_str:
                    continue

                published_at = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                time_threshold = now - timedelta(days=1)
                if published_at > time_threshold:
                    author = top_comment.get("authorDisplayName", "고객")
                    text = top_comment.get("textOriginal", "")
                    
                    database.create_agent_log(
                        task_type="comment_monitor",
                        status="warning",
                        message=f"💬 [유튜브 신규 댓글] @{author}: \"{text[:40]}{( '...' if len(text) > 40 else '' )}\"",
                        details=json.dumps({
                            "comment_id": item.get("id"),
                            "author": author,
                            "text": text,
                            "published_at": published_at_str,
                            "video_id": snippet.get("videoId")
                        }, ensure_ascii=False)
                    )
                    new_comment_count += 1
            
            logger.info(f"YouTube comment monitoring finished. Found {new_comment_count} new comments.")
        except Exception as e:
            logger.error(f"YouTube comment monitoring exception: {e}")

    async def _summarize_manychat_events(self):
        logs = database.get_agent_logs(limit=100)
        recent_count = 0
        now = datetime.now()
        
        for log in logs:
            if log["task_type"] == "manychat_event":
                try:
                    created_at = datetime.strptime(log["created_at"], "%Y-%m-%d %H:%M:%S")
                    if (now - created_at).total_seconds() <= 3600:
                        recent_count += 1
                except Exception:
                    pass

        if recent_count > 0:
            database.create_agent_log(
                task_type="manychat_event",
                status="success",
                message=f"📈 [ManyChat 연동 브리핑] 지난 1시간 동안 인스타그램/틱톡에서 총 {recent_count}건의 DM 단축 링크가 고객들에게 자동으로 성공적으로 발송되었습니다."
            )
            logger.info(f"ManyChat event summary written. Count: {recent_count}")

    async def run_once(self):
        logger.info("Manual trigger of AI Agent Engine run_once sequence.")
        database.create_agent_log(
            task_type="system",
            status="success",
            message="⚡ [수동 기동] AI 에이전트 수동 즉시 실행 시퀀스를 개시합니다."
        )
        try:
            # 1. 비디오 스캔
            await self._scan_input_directory()
            # 2. 유튜브 댓글 점검
            await self._monitor_youtube_comments()
            # 3. ManyChat 브리핑
            await self._summarize_manychat_events()
            # 4. 배포 예약 체크
            await self._check_and_publish_pending_items()
            
            database.create_agent_log(
                task_type="system",
                status="success",
                message="✨ [수동 기동 완료] AI 에이전트 수동 즉시 실행 시퀀스가 성공적으로 마쳤습니다."
            )
        except Exception as e:
            logger.error(f"Manual run_once exception: {e}", exc_info=True)
            database.create_agent_log(
                task_type="system",
                status="failed",
                message=f"❌ [수동 기동 실패] 실행 중 오류 발생: {str(e)}"
            )

# 싱글톤 인스턴스 노출
agent_engine = AIAgentEngine()
