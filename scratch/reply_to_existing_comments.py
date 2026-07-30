import sys
import os
import asyncio
import re
import json
import logging
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import instagram_api
import gpt_agent

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("existing_comments_cleaner")

async def clean_existing_comments():
    load_dotenv()
    database.init_db()
    
    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    biz_account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    
    if not access_token or not biz_account_id:
        logger.error("INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID is not configured in .env!")
        print("❌ 실행 실패: .env 파일에 인스타그램 설정값(토큰 및 계정 ID)을 먼저 입력해 주세요.")
        return

    print("🚀 기존 댓글 일괄 자동화 소급 스캔을 시작합니다...")
    
    # 1. 최근 업로드한 미디어 목록 조회
    logger.info("Fetching recent media list...")
    media_list = await instagram_api.get_recent_media(limit=15)
    if not media_list:
        logger.warning("No media found or failed to fetch media list.")
        return
        
    print(f"-> 최근 업로드된 {len(media_list)}개의 비디오(릴스/피드)를 스캔합니다.")
    
    for media in media_list:
        media_id = media.get("id")
        # 캡션 조회
        caption = await instagram_api.get_media_caption(media_id)
        logger.info(f"Scanning Media ID: {media_id} (Caption: {caption[:20]}...)")
        
        # 릴스 캡션에서 상품 번호 추출 (T28, T00028, No.28, No 28 등 모두 대응)
        product_no = None
        if caption:
            match = re.search(r'(?:[tT]|No\.?)\s*(\d+)', caption, re.IGNORECASE)
            if match:
                product_no = match.group(1)
                
        # 상품 DB 조회
        matched_item = None
        if product_no:
            matched_item = database.get_item_by_product_no(product_no)
            
        # 매치되는 상품이 없으면 가장 최신 발행 성공/예약 상품 폴백
        if not matched_item:
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
                
        if not matched_item:
            logger.warning(f"No item available (even fallback). Skipping media {media_id}")
            continue

        # 2. 해당 미디어에 달린 댓글 목록 조회
        comments = await instagram_api.get_media_comments(media_id)
        if not comments:
            continue
            
        for comment in comments:
            comment_id = comment.get("id")
            comment_text = comment.get("text", "")
            from_user = comment.get("from", {})
            user_scoped_id = from_user.get("id")
            
            # '엄마' 및 오타(엄 마, 엄머, 어마) 키워드가 댓글 텍스트에 포함되어 있지 않으면 패스
            if not re.search(r'엄\s*마|엄\s*머|어\s*마', comment_text):
                continue

            # 본인이 쓴 댓글 패스
            if user_scoped_id == biz_account_id:
                continue
                
            # 이미 본인이 대댓글을 달아준 댓글인지 판별
            replies_data = comment.get("replies", {}).get("data", [])
            already_replied = False
            for rep in replies_data:
                rep_user = rep.get("from", {})
                if rep_user.get("id") == biz_account_id:
                    already_replied = True
                    break
                    
            if already_replied:
                # 이미 답변 완료된 건이므로 패스
                continue
                
            print(f"\n[미답변 댓글 포착] 작성자: @{from_user.get('username')}, 내용: '{comment_text}'")
            print(f"-> 매칭 상품: {matched_item.get('product_code')} (No.{matched_item.get('product_no')})")
            
            # 3. 상품 정보 및 두 링크 빌드
            title = matched_item.get("title", "추천 상품")
            description = matched_item.get("description", "")
            
            # 1) 쿠팡 직접 구매 링크 (단축 우선, 없으면 원본)
            coupang_link = matched_item.get("short_url") or matched_item.get("coupang_url") or "https://www.coupang.com"
            # 2) 6070 전체 카탈로그 몰 메인 링크
            catalog_link = "https://6070.piella.shop"
                
            # 4. 하이브리드 비용 절감 발송 분기 (DB 템플릿 우선 사용)
            db_reply = matched_item.get("comment_reply")
            db_dm = matched_item.get("dm_template")
            
            if db_reply and db_dm and db_reply.strip() != "" and db_dm.strip() != "":
                print("-> DB에 저장된 템플릿 원고 사용 (GPT 비용 절감)")
                reply_msg = db_reply.replace("{short_url}", coupang_link).replace("{catalog_url}", catalog_link)
                dm_msg = db_dm.replace("{short_url}", coupang_link).replace("{catalog_url}", catalog_link)
                if "{buyer_name}" in dm_msg:
                    dm_msg = dm_msg.replace("{buyer_name}", "어머님")
            else:
                # 템플릿이 없을 때만 GPT-4o-mini 호출
                print("-> GPT 답변 작성 중...")
                gpt_result = await gpt_agent.generate_reply_and_dm_content(
                    user_comment=comment_text,
                    product_title=title,
                    product_description=description,
                    coupang_link=coupang_link,
                    catalog_link=catalog_link
                )
                reply_msg = gpt_result.get("reply")
                dm_msg = gpt_result.get("dm")
            
            # 5. 인스타그램 대댓글 및 DM 발송
            print("-> 인스타그램 API 발송 중...")
            success_reply = await instagram_api.send_comment_reply(comment_id, reply_msg)
            success_dm = await instagram_api.send_instagram_dm(user_scoped_id, dm_msg)
            
            if success_reply and success_dm:
                print("✅ 성공: 대댓글 및 DM 전송 완료!")
                database.create_agent_log(
                    task_type="instagram_retroactive",
                    status="success",
                    message=f"💬 [소급 자동화 성공] 상품 {matched_item.get('product_code')} 관련 대댓글 및 DM 소급 완료.",
                    details=json.dumps({
                        "comment_id": comment_id,
                        "user_scoped_id": user_scoped_id,
                        "reply": reply_msg,
                        "dm": dm_msg
                    }, ensure_ascii=False)
                )
            else:
                print(f"❌ 부분 실패: 대댓글({success_reply}), DM({success_dm})")
                database.create_agent_log(
                    task_type="instagram_retroactive",
                    status="error",
                    message=f"⚠️ [소급 자동화 실패] 대댓글 성공: {success_reply}, DM 성공: {success_dm}"
                )

                
            # 스팸 API 차단 방지를 위해 2.5초 대기
            await asyncio.sleep(2.5)

    print("\n🎉 모든 기존 댓글 스캔 및 소급 처리가 완료되었습니다!")

if __name__ == "__main__":
    asyncio.run(clean_existing_comments())
