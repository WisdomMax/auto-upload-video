import asyncio
import logging
import json
import os
import requests
from datetime import datetime, timedelta, timezone
import database
import youtube_comments

logger = logging.getLogger("agent_engine")

def calculate_file_hash(file_path):
    import hashlib
    if not file_path or not os.path.exists(file_path):
        return None
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return None

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
        last_recommend_date = None      # 예: "2026-06-08"
        
        # [최초 기동 대응] 추천 대기 상품 목록이 비어있다면 즉시 최초 1회 수집 진행
        try:
            import recommendation_agent
            recs = database.get_recommended_items(status="pending")
            if not recs:
                logger.info("[서버 기동 최초 실행] AI 추천 상품 대기 목록이 비어있어 최초 수집을 시작합니다...")
                await recommendation_agent.run_recommendation_batch(max_items_to_add=2)
        except Exception as startup_rec_err:
            logger.error(f"Failed to run startup recommendation batch: {startup_rec_err}")
        
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
                        
                # 5. AI 추천 상품 정기 발굴: 매일 오전 4시 (04:00 KST)에 1회 구동
                if hour == 4:
                    if last_recommend_date != today_str:
                        logger.info("[오전 4시 정기 AI 추천 상품 발굴] 상품 탐색 가동...")
                        try:
                            import recommendation_agent
                            await recommendation_agent.run_recommendation_batch(max_items_to_add=2)
                        except Exception as e_rec:
                            logger.error(f"Failed to run recommendation batch: {e_rec}")
                        last_recommend_date = today_str

            except Exception as e:
                logger.error(f"Error in Agent Scheduler loop: {e}", exc_info=True)
                
            await asyncio.sleep(self.interval)

    async def _scan_input_directory(self):
        import time
        import shutil
        import re
        base_dir = os.path.dirname(os.path.abspath(__file__))
        input_dir = os.path.join(base_dir, "input")
        processed_dir = os.path.join(input_dir, "processed")
        
        if not os.path.exists(input_dir):
            os.makedirs(input_dir, exist_ok=True)
            
        os.makedirs(processed_dir, exist_ok=True)

        # 1. DB settings에서 이미 처리 완료된 파일명 캐시 로드
        processed_files_str = database.get_setting("processed_input_files", "[]")
        try:
            processed_files = json.loads(processed_files_str)
        except Exception:
            processed_files = []

        # 2. 파일 리스트 중 아직 스캔 처리되지 않은 신규 파일만 선별
        all_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.mp4', '.mov', '.avi'))]
        new_files = [f for f in all_files if f not in processed_files]

        # [방치 파일 자동 정리 가드]
        # 이미 스캔이 끝났으나 어떤 이유로 input/ 폴더에 방치된 파일들을 processed/ 폴더로 자동 격리시킵니다.
        stray_files = [f for f in all_files if f in processed_files]
        for file_name in stray_files:
            video_path = os.path.join(input_dir, file_name)
            dest_file_name = file_name
            dest_path = os.path.join(processed_dir, dest_file_name)
            if os.path.exists(dest_path):
                name_part, ext_part = os.path.splitext(file_name)
                dest_file_name = f"{name_part}_{int(time.time())}{ext_part}"
                dest_path = os.path.join(processed_dir, dest_file_name)
            try:
                shutil.move(video_path, dest_path)
                logger.info(f"🧹 Auto-cleared stray processed file from input/: {file_name}")
            except Exception as e_stray:
                logger.error(f"Failed to move stray file {file_name}: {e_stray}")

        if not new_files:
            logger.info("No new video files found in /input directory.")
        else:
            import video_agent
            import catalog_builder

            for file_name in new_files:
                video_path = os.path.join(input_dir, file_name)
                logger.info(f"New video detected in input: {video_path}")
                
                try:
                    # 비디오 파일 해시 계산을 통한 중복 스캔 방지
                    file_hash = calculate_file_hash(video_path)
                    if file_hash:
                        dup_item = database.get_item_by_video_hash(file_hash)
                        if dup_item:
                            logger.warning(f"Duplicate video file detected! File '{file_name}' matches product {dup_item['product_code']} (ID: {dup_item['id']})")
                            database.create_agent_log(
                                task_type="video_scan",
                                status="warning",
                                message=f"⚠️ [중복 스캔 방지] 파일 '{file_name}'의 내용이 이미 등록된 {dup_item['product_code']}번 상품과 동일하여 등록을 건너뛰었습니다."
                            )
                            # 중복 파일도 처리 완료 목록에 넣어 다시 스캔 안 되도록 함
                            processed_files.append(file_name)
                            database.set_setting("processed_input_files", json.dumps(processed_files))
                            
                            # processed/ 폴더로 이동하여 격리
                            dest_file_name = file_name
                            dest_path = os.path.join(processed_dir, dest_file_name)
                            if os.path.exists(dest_path):
                                name_part, ext_part = os.path.splitext(file_name)
                                dest_file_name = f"{name_part}_{int(time.time())}{ext_part}"
                                dest_path = os.path.join(processed_dir, dest_file_name)
                            try:
                                shutil.move(video_path, dest_path)
                                logger.info(f"Moved duplicate file to processed: {dest_path}")
                            except Exception as e_move:
                                logger.error(f"Failed to move duplicate file {file_name}: {e_move}")
                            continue

                    # 파일명이 숫자로만 되어있는지 체크 (예: 14.mp4)
                    num_match = re.match(r'^(\d+)\.(mp4|mov|avi)$', file_name, re.IGNORECASE)
                    
                    if num_match:
                        target_no = int(num_match.group(1))
                        # DB에서 매칭되는 'waiting_video' 아이템 조회
                        waiting_item = database.get_item_by_product_no(target_no)
                        
                        if waiting_item and waiting_item.get("publish_status") == "waiting_video":
                            logger.info(f"Matching 'waiting_video' item found: {waiting_item['product_code']} (ID: {waiting_item['id']})")
                            
                            # 1) 기존 예약 코드로 비디오 파이프라인 실행
                            result = await video_agent.process_video_pipeline(
                                video_path, 
                                product_code=waiting_item['product_code'], 
                                product_no=waiting_item['product_no']
                            )
                            
                            # 2) 기존 DB 아이템 업데이트
                            item_id = waiting_item["id"]
                            conn = database.get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE items SET publish_status = 'pending', original_video_path = ?, video_hash = ? WHERE id = ?", (result["original_video_path"], file_hash, item_id))
                            conn.commit()
                            conn.close()
                            
                            log_msg = f"📹 [비디오 자동 결합 완료] 대기 상품 {waiting_item['product_code']}번에 {file_name} 비디오가 매핑 결합되어 배포 준비 상태로 전환되었습니다."
                        else:
                            logger.warning(f"Number format filename '{file_name}' skipped. No corresponding 'waiting_video' item for product_no: {target_no}")
                            database.create_agent_log(
                                task_type="video_scan",
                                status="warning",
                                message=f"⚠️ [비디오 매핑 대기] 파일명이 {file_name}(숫자)이지만 대시보드에 [동영상 대기]로 등록된 {target_no}번 상품이 없습니다. 승인을 먼저 진행해 주세요."
                            )
                            continue  # 처리 완료 목록에 넣지 않고 보류
                    else:
                        # 기존 방식: 일반 텍스트 파일명 -> 신규 아이템 생성
                        # 1) 비디오 파이프라인 실행 (Gemini 분석, 코드 발급, 자막 오버레이, webp 썸네일 캡처)
                        result = await video_agent.process_video_pipeline(video_path)
                        
                        # 2) DB에 아이템 최초 인서트 (쿠팡 주소는 빈 상태)
                        item_id = database.create_item(
                            product_no=result["product_no"],
                            title=result["title"],
                            description=result["description"],
                            coupang_url="",
                            original_video_path=result["original_video_path"],
                            product_code=result["product_code"],
                            video_hash=file_hash
                        )
                        log_msg = f"📹 [비디오 감지 완료] 코드 {result['product_code']} 상품의 자막 합성 및 webp 썸네일 생성이 완료되었습니다. 대시보드에서 쿠팡 링크 입력을 기다리는 대기 상태로 등록되었습니다."
                    
                    # 3) SNS 본문 글 및 유튜브 캡션 자동 생성 (Fallback 자동완성)
                    from main import generate_ai_sns_content
                    await generate_ai_sns_content(item_id)
                    
                    # 4) 처리 완료 목록에 추가 및 DB 캐시 갱신
                    processed_files.append(file_name)
                    database.set_setting("processed_input_files", json.dumps(processed_files))
                    logger.info(f"Marked input file as processed: {file_name}")

                    # 5) 원본 비디오 파일을 processed 디렉토리로 이동 (중복 스캔 방지)
                    dest_file_name = file_name
                    dest_path = os.path.join(processed_dir, dest_file_name)
                    if os.path.exists(dest_path):
                        name_part, ext_part = os.path.splitext(file_name)
                        dest_file_name = f"{name_part}_{int(time.time())}{ext_part}"
                        dest_path = os.path.join(processed_dir, dest_file_name)
                    
                    shutil.move(video_path, dest_path)
                    logger.info(f"Successfully moved processed file to: {dest_path}")
                    
                    # 6) 정적 카탈로그 index.html 빌더 실행
                    catalog_builder.build_catalog()
                    
                    # 7) Cloudflare Pages 자동 배포 트리거
                    try:
                        requests.post("http://localhost:18888/api/publish-catalog", timeout=30)
                    except Exception as e_pub:
                        logger.error(f"Failed to auto-trigger catalog publish: {e_pub}")
                    
                    database.create_agent_log(
                        task_type="video_scan",
                        status="success",
                        message=log_msg
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing input file {file_name}: {e}", exc_info=True)
                    database.create_agent_log(
                        task_type="video_scan",
                        status="failed",
                        message=f"❌ [비디오 처리 실패] 파일 {file_name} 처리 중 오류 발생: {str(e)}"
                    )

        # 3. 보관 기간이 30일 이상 경과한 영상 중, 업로드 배포가 완료된 건들만 안전하게 순차 정리
        try:
            now_sec = time.time()
            limit_sec = 30 * 24 * 3600  # 30일 초 단위
            updated_processed_files = processed_files.copy()
            
            if os.path.exists(processed_dir):
                processed_all_files = [f for f in os.listdir(processed_dir) if os.path.isfile(os.path.join(processed_dir, f))]
                for file_name in processed_all_files:
                    file_path = os.path.join(processed_dir, file_name)
                    mtime = os.path.getmtime(file_path)
                    age_sec = now_sec - mtime
                    if age_sec >= limit_sec:
                        # 타임스탬프 접미사 등을 정규식으로 걸러서 원본 파일명 매칭
                        name_part, ext_part = os.path.splitext(file_name)
                        orig_name = re.sub(r'_\d+$', '', name_part) + ext_part
                        
                        # DB 연계 조회: 이 원본 파일명과 관련된 모든 상품 정보의 업로드 완료 상태 점검
                        conn = database.get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT publish_status FROM items WHERE original_video_path LIKE ?", (f"%{orig_name}",))
                        related_items = cursor.fetchall()
                        conn.close()
                        
                        should_delete = True
                        if related_items:
                            for row in related_items:
                                status = row['publish_status']
                                # 하나라도 업로드 완료(success)가 아니면 삭제 유예
                                if status != 'success':
                                    should_delete = False
                                    break
                                    
                        if not should_delete:
                            logger.info(f"⏳ Postponed deletion of {file_name}: associated item upload is not yet completed.")
                            continue
                            
                        os.remove(file_path)
                        logger.info(f"🗑️ Removed processed input file older than 7 days (Upload complete): {file_name}")
                        
                        if orig_name in updated_processed_files:
                            updated_processed_files.remove(orig_name)
                        elif file_name in updated_processed_files:
                            updated_processed_files.remove(file_name)
                            
            if updated_processed_files != processed_files:
                database.set_setting("processed_input_files", json.dumps(updated_processed_files))
        except Exception as cleanup_err:
            logger.error(f"Failed to cleanup older input files: {cleanup_err}")

    async def _schedule_item_on_buffer(self, item_id, scheduled_at_dt):
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

        scheduled_at_str = scheduled_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

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


        fixed_yt_id = database.get_setting("YOUTUBE_PROFILE_ID") or os.getenv("YOUTUBE_PROFILE_ID")
        fixed_tt_id = database.get_setting("TIKTOK_PROFILE_ID") or os.getenv("TIKTOK_PROFILE_ID")
        fixed_ig_id = database.get_setting("INSTAGRAM_PROFILE_ID") or os.getenv("INSTAGRAM_PROFILE_ID")

        for platform in platforms:
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

            text = item.get('sns_caption', '')
            title = item.get('title', '')
            if platform == 'youtube':
                text = item.get('youtube_description', '')
                title = item.get('youtube_title') or item.get('title', '')
            elif platform == 'tiktok':
                text = item.get('sns_caption', '') + "\n\n(채널 프로필 홈에 연결된 링크를 클릭하시면 모든 제품의 구매 링크를 편리하게 확인하실 수 있습니다)"
            elif platform == 'instagram':
                text = item.get('sns_caption', '') + "\n\n(전체 제품 링크는 홈페이지: auto-upload-video.pages.dev 에서 확인하실 수 있습니다)"

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
        
        kst_time_str = scheduled_at_dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
        database.create_agent_log(
            task_type="buffer_schedule",
            status="success" if final_status == "scheduled" else "failed",
            message=f"[Buffer 배포 예약 완료] 상품 코드: {item.get('product_code') or ('No.'+str(item['product_no']))} -> 예약 시간: {kst_time_str} KST (채널 {success_count}개 예약 완료)"
        )

    async def _generate_intelligent_caption(self, item_id):
        import coupang_scraper
        item = database.get_item(item_id)
        if not item:
            return
            
        url = item.get("coupang_url")
        if not url:
            return
            
        # 기존 title이 유효한 값(디폴트나 빈값이 아님)인지 확인하여 중복 크롤링 방지
        current_title = item.get("title")
        is_default_title = current_title in ["엄마아빠 패션다이어리 추천 상품", "쿠팡 추천 상품", None, ""]
        
        if is_default_title:
            # 1. Playwright Stealth 모드로 쿠팡 제품명 긁어오기 (기본값인 경우에만 1회 시도)
            logger.info(f"Stealth scraping product info for item {item_id} from Coupang...")
            scraped_title = await coupang_scraper.scrape_coupang_product(url)
            
            # 상품의 실제 제목을 DB에 업데이트 (디폴트 타이틀이 아닐 때만)
            if scraped_title and scraped_title not in ["엄마아빠 패션다이어리 추천 상품", "쿠팡 추천 상품"]:
                try:
                    conn = database.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE items SET title = ? WHERE id = ?", (scraped_title, item_id))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Failed to update title for item {item_id}: {e}")
        else:
            logger.info(f"Using existing title for item {item_id}: {current_title} (Scraping skipped)")
            
        # 최신화된 상품 정보 다시 획득
        item = database.get_item(item_id)
        product_no = item.get("product_no")
        title = item.get("title")
        description = item.get("description", "") # 사용자가 대시보드 추가설명 란에 적은 내용
        
        # 2. 쿠팡 단축 링크 생성 (아직 없는 경우에만)
        short_url = item.get("short_url")
        if not short_url:
            coupang_access = database.get_setting("COUPANG_ACCESS_KEY") or os.getenv("COUPANG_ACCESS_KEY")
            coupang_secret = database.get_setting("COUPANG_SECRET_KEY") or os.getenv("COUPANG_SECRET_KEY")
            if coupang_access and coupang_secret:
                from main import get_coupang_short_link
                short_url = get_coupang_short_link(url, coupang_access, coupang_secret)
                if short_url:
                    database.update_item_coupang_urls(item_id, url, short_url)
                    
        link = short_url if short_url else url
        
        # 2.5 SEO 완료 상태 체크 (가드 로직)
        current_yt_title = item.get("youtube_title") or ""
        current_yt_desc = item.get("youtube_description") or ""
        
        default_prefixes = ["60대 이후 옷 잘 입는", "60대 어머님들", "60대 이후 입으면", "60대 70대 어머님들"]
        
        is_empty = not current_yt_title or not current_yt_desc
        is_default_title = any(current_yt_title.startswith(p) for p in default_prefixes) or "엄마아빠 패션다이어리" in current_yt_title or "추천 상품" in current_yt_title
        is_default_desc = "에이전트가 영상 분석을 통해" in current_yt_desc or "에이전트가 추천한" in current_yt_desc or not current_yt_desc
        
        is_seo_completed = not is_empty and not is_default_title and not is_default_desc
        
        if is_seo_completed:
            logger.info(f"SEO caption is already customized for item {item_id}. Overwrite skipped by SEO Guard.")
            return

        
        # 3. 제품 카테고리 판별 및 태그/문구 고도화 셋업
        import random
        
        # 카테고리별 풍부한 태그 풀 정의 (검색 노출 최적화용)
        tag_pools = {
            "원피스": ["시니어패션", "60대여성의류", "동안코디", "엄마옷추천", "중년여성패션", "원피스코디", "5060패션", "6070패션", "7080코디", "시니어룩", "중년코디", "우아한룩", "여름원피스", "체형커버코디", "귀티나는코디", "엄마선물", "편안한원피스", "세련된코디"],
            "아우터": ["시니어룩", "중년패션", "아우터추천", "귀티나는코디", "60대패션", "가디건코디", "엄마옷선물", "6080패션", "5060의류", "시니어자켓", "가벼운아우터", "중년의일상", "모임룩추천", "세련된코디", "동안코디", "체형보정"],
            "바지": ["60대여성코디", "밴딩바지", "중년여성패션", "세련된코디", "시니어패션", "바지추천", "6070패션", "7080패션", "발편한코디", "일상데일리룩", "편한바지", "체형커버바지", "중년의일상", "5060바지", "엄마옷"],
            "상의": ["5060패션", "동안스타일링", "엄마옷", "상의코디", "세련된코디", "60대여성의류", "7080코디", "6070패션", "린넨티셔츠", "시원한여름옷", "중년코디", "모임룩추천", "귀티나는룩", "이지웨어"],
            "신발": ["발편한신발", "효도신발", "시니어룩", "기능성슈즈", "60대여성코디", "중년여성패션", "6080패션", "발편한로퍼", "걷기좋은신발", "엄마신발추천", "5060패션", "데일리슈즈", "편안한구두"],
            "의류": ["시니어패션", "동안코디", "귀티나는코디", "중년여성패션", "5060패션", "엄마옷추천", "6070패션", "7080패션", "6080코디", "시니어룩", "세련된코디", "중년스타일링", "엄마선물룩", "데일리룩"]
        }

        title_lower = title.lower()
        category = "의류"
        intro_phrase = f"어머님들이 입으시기 딱 좋은 편안하고 세련된 {title} 소개해 드려요"
        
        if any(x in title_lower for x in ["원피스", "드레스"]):
            category = "원피스"
            intro_phrase = f"편안하면서도 고상한 멋이 느껴지는 {title} 소개해 드립니다"
            youtube_title = f"60대 이후 옷 잘 입는 분들은 절대 안 입는 원피스? {title} 코디법! #동안코디 #원피스코디"
        elif any(x in title_lower for x in ["가디건", "카디건", "아우터", "재킷", "점퍼", "코트", "조끼", "베스트"]):
            category = "아우터"
            intro_phrase = f"가볍게 툭 걸치기만 해도 스타일이 사는 외출용 {title} 준비했습니다"
            youtube_title = f"60대 어머님들 외출하실 때 일반 가디건보다 이 {title}이 훨씬 귀티나고 세련돼요! #귀티나는코디 #아우터추천"
        elif any(x in title_lower for x in ["바지", "팬츠", "슬랙스", "청바지"]):
            category = "바지"
            intro_phrase = f"하루 종일 입어도 정말 편안하고 활동성 최고인 {title} 추천해 드려요"
            youtube_title = f"60대 이후 입으면 20년 젊어보이는 {title} 코디 추천 #중년여성패션 #바지코디"
        elif any(x in title_lower for x in ["티셔츠", "블라우스", "셔츠", "남방", "니트"]):
            category = "상의"
            intro_phrase = f"시원하고 부드러운 촉감으로 매일 손이 가는 {title} 소개해 드립니다"
            youtube_title = f"60대 어머님들 {title} 하나로 키 5cm는 더 커 보이고 젊어지는 코디법! #세련된코디 #상의코디"
        elif any(x in title_lower for x in ["샌들", "샌달", "구두", "신발", "슬리퍼", "스니커즈", "로퍼"]):
            category = "신발"
            intro_phrase = f"발이 정말 편안해서 외출하실 때 걷기 좋은 기능성 {title} 소개해 드려요"
            youtube_title = f"60대 이후 촌스럽지 않고 발 편해서 하루 만 보 걷기 좋은 {title} 추천 #발편한신발 #시니어룩"
        else:
            youtube_title = f"60대 70대 어머님들 비싼 옷 안 입어도 20년 젊어 보이는 동안 {title} 코디 공식 #시니어패션 #동안코디"

        # 4. 사용자 추가 설명(description)이 기본 템플릿 문구가 아니고 존재한다면 적극 반영
        user_extra = ""
        is_default_desc = description == "에이전트가 영상 분석을 통해 추천하는 고품질 신상품 정보입니다."
        if description and not is_default_desc:
            user_extra = f"\n\n[제품 정보 및 구성 안내 📌]\n👉 {description}"
            
        # 5. 유튜브 내부 검색창에 적용될 메타데이터 태그 (콤마로 구분된 7개 무작위 태그 추출)
        pool = tag_pools.get(category, tag_pools["의류"])
        selected_tags = random.sample(pool, min(len(pool), 7))
        youtube_tags = ", ".join(selected_tags)

        # 6. 유튜브 설명 본문용 다이내믹 해시태그 (본문용으로 무작위 4개 추출하여 샵 기호 접두)
        desc_tags = random.sample(pool, min(len(pool), 4))
        desc_hashtags_str = " ".join([f"#{t}" for t in desc_tags])

        youtube_description = (
            f"영상 속 추천 아이템 정보입니다! 👇\n\n"
            f"구매 링크: {link}\n"
            f"(채널 프로필 홈에 연결된 링크를 클릭하시면 모든 제품의 구매 링크를 한눈에 편리하게 확인하실 수 있습니다)\n\n"
            f"[제품 설명]\n"
            f"- {intro_phrase}\n"
            f"- 상품명: {title}"
        )
        if user_extra:
            youtube_description += f"{user_extra}"
        youtube_description += f"\n\n* 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.\n\n{desc_hashtags_str}"
        
        sns_caption = (
            f"이거 하나로 고민 해결! 대박 꿀템 공유해 드립니다 ✨\n\n"
            f"No.{product_no} - {title}"
        )
        if user_extra:
            sns_caption += f"{user_extra}"
        sns_caption += (
            f"\n\n제품의 상세 정보와 단축 링크가 필요하시다면?\n"
            f"댓글로 '엄마'를 남겨주시면 DM으로 바로 링크를 보내드릴게요! 💌\n\n"
            f"#생활꿀팁 #살림템 #꿀템 #쿠팡추천"
        )
        
        comment_reply = f"유튜브 정책상 댓글 링크 클릭이 되지 않아서 네이버 검색을 유도해 드려요! 🔍 네이버 검색창에 '엄마아빠 패션다이어리 {title}'을 검색하시면 상세 정보와 쿠팡 링크를 바로 확인하실 수 있습니다!"
        dm_template = f"안녕하세요 크리에이터입니다! 😊\n요청하신 [No.{product_no} - {title}]의 상세 링크입니다.\n\n👇 쿠팡 즉시구매 링크\n{link}\n\n즐겁고 스마트한 쇼핑 되세요!"
        
        # DB 업데이트
        database.update_item_generated_contents(
            item_id,
            youtube_title,
            youtube_description,
            youtube_tags,
            sns_caption,
            dm_template,
            comment_reply
        )
        logger.info(f"Intelligent caption generation completed for item {item_id}")

    async def _check_and_publish_pending_items(self):
        # 자동 예약 배포 활성화 여부 검사 (사용자 지시 "지금 예약하지마" 대응 기본값: false)
        if database.get_setting("AUTO_PUBLISH_SCHEDULE", "false") != "true":
            logger.info("Buffer auto-scheduling is disabled by configuration (AUTO_PUBLISH_SCHEDULE is not 'true'). Skipping.")
            return

        items = database.get_items()
        
        # 0. 예약 시간이 만료된(이미 배포 완료된) scheduled 상태의 아이템들을 success로 자동 업데이트
        from datetime import datetime, timezone as dt_timezone
        now_utc = datetime.now(dt_timezone.utc)
        for it in items:
            if it.get("publish_status") == "scheduled" and it.get("scheduled_at"):
                try:
                    sched_time = datetime.fromisoformat(it["scheduled_at"].replace("Z", "+00:00"))
                    if sched_time <= now_utc:
                        database.update_item_publish_results(it["id"], "success", it.get("publish_results"))
                        logger.info(f"Auto-promoted item {it['id']} (No {it.get('product_no')}) from 'scheduled' to 'success' as scheduled time ({it['scheduled_at']}) has passed.")
                except Exception as ex_time:
                    logger.error(f"Failed to check/update status for scheduled item {it['id']}: {ex_time}")
                    
        # 갱신된 정보로 다시 가져옴
        items = database.get_items()
        
        # 1. 쿠팡 URL이 있고 대기(pending) 상태이거나, 실패(failed)했으나 예약 일정이 잡히지 않은 상품 추출
        raw_pending = [
            it for it in items 
            if (it.get("publish_status") == "pending" or (it.get("publish_status") == "failed" and (not it.get("scheduled_at") or it.get("scheduled_at") == "")))
            and it.get("coupang_url") 
            and it.get("coupang_url") != ""
        ]
        
        # 2. 각 대기 상품에 대해 Playwright 기반 쿠팡 제목 긁어오기 및 에이전트 지능형 캡션/원고 생성 가동
        for item in raw_pending:
            try:
                await self._generate_intelligent_caption(item["id"])
            except Exception as ex_gen:
                logger.error(f"Failed to generate intelligent caption for item {item['id']}: {ex_gen}")
                
        # 3. 갱신된 정보로 다시 가져온 뒤, 단축링크 처리가 완료되었고 예약 예정인 상품 필터링
        items = database.get_items()
        pending_items = [
            it for it in items 
            if (it.get("publish_status") == "pending" or (it.get("publish_status") == "failed" and (not it.get("scheduled_at") or it.get("scheduled_at") == "")))
            and it.get("coupang_url") 
            and it.get("coupang_url") != ""
            and it.get("short_url")
            and it.get("short_url") != ""
        ]

        if not pending_items:
            return

        # ID 오름차순(오래된 상품 순)으로 정렬하여 먼저 등록된 상품이 빠른 날짜에 배포 예약되게 함
        pending_items.sort(key=lambda x: x["id"])

        # 예약 타임슬롯 기준점 계산 (매일 저녁 6시 KST = 18:00 KST = 09:00 UTC)
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
        
        # 3. 이미 미래에 예약 완료된 활성 포스트 수 계산
        active_scheduled_count = len(future_scheduled)
        slots_available = 3 - active_scheduled_count
        
        if slots_available <= 0:
            logger.info(f"Buffer queue is already full with {active_scheduled_count} scheduled posts. Skipping scheduling for now.")
            return
            
        items_to_publish = pending_items[:slots_available]
        logger.info(f"Buffer queue has {active_scheduled_count} active posts. Scheduling {len(items_to_publish)} new post(s) to maintain 3 days of buffer.")
        
        if future_scheduled:
            # 기존 예약된 일정이 있는 경우, 마지막 예약 시점의 다음날부터 하루에 하나씩 추가 배정
            base_sch = future_scheduled[-1]
            for i, item in enumerate(items_to_publish):
                next_sch = base_sch + timedelta(days=i + 1)
                await self._schedule_item_on_buffer(item["id"], next_sch)
        else:
            # 기존 예약 일정이 없는 경우, 오늘 혹은 내일 18:00 KST 부터 하루에 하나씩 순차 배정
            kst_tz = timezone(timedelta(hours=9))
            now_kst = datetime.now(kst_tz)
            today_18_kst = now_kst.replace(hour=18, minute=0, second=0, microsecond=0)
            
            if now_kst < today_18_kst:
                base_sch = today_18_kst.astimezone(timezone.utc)
            else:
                base_sch = (today_18_kst + timedelta(days=1)).astimezone(timezone.utc)

            for i, item in enumerate(items_to_publish):
                next_sch = base_sch + timedelta(days=i)
                await self._schedule_item_on_buffer(item["id"], next_sch)

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