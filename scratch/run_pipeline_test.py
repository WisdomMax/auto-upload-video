import asyncio
import os
import shutil
import database
import recommendation_agent
from agent_engine import agent_engine

async def main():
    print("1. 대기 중인 추천 상품을 조회합니다...")
    recs = database.get_recommended_items(status="pending")
    if not recs:
        print("대기 중인 추천 상품이 없어 추천 상품 발굴을 먼저 실행합니다...")
        await recommendation_agent.run_recommendation_batch(max_items_to_add=2)
        recs = database.get_recommended_items(status="pending")
        
    if not recs:
        print("추천 상품을 발굴할 수 없습니다. 처리를 중단합니다.")
        return
        
    # 첫 번째 추천 상품 선택
    rec = recs[0]
    rec_id = rec['id']
    print(f"선택된 추천 상품: ID {rec_id}, 이름: {rec['product_name']}")
    
    # 숏링크 생성 시도
    print("쿠팡 파트너스 숏링크 생성 중...")
    short_url = recommendation_agent.generate_partners_short_link(rec['coupang_url'])
    if not short_url:
        print("숏링크 생성 실패, 원본 URL을 사용합니다.")
        short_url = rec['coupang_url']
        
    product_code = database.get_next_product_code("T")
    product_no = database.get_next_product_no()
    
    print(f"새로운 상품 코드: {product_code}, 상품 번호: {product_no}")
    
    # waiting_video 상태로 아이템 추가
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
    
    database.update_recommendation_status(rec_id, "approved")
    print(f"추천 상품 ID {rec_id}가 승인되어 {product_code}번 상품으로 waiting_video 등록되었습니다.")
    
    # 테스트용 비디오 복사 배치
    # 기존 원본 파일 중 하나를 input/{product_no}.mp4 로 복사
    src_video = os.path.join("/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/uploads/originals/prod_T00027_27.mp4")
    dest_video = os.path.join("/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/input", f"{product_no}.mp4")
    
    if os.path.exists(src_video):
        print(f"비디오 복사 중: {src_video} -> {dest_video}")
        shutil.copy2(src_video, dest_video)
    else:
        print("소스 비디오가 존재하지 않습니다! 다른 비디오를 찾습니다...")
        # uploads/originals 디렉토리의 첫 번째 mp4 파일 사용
        orig_dir = "/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/uploads/originals"
        files = [f for f in os.listdir(orig_dir) if f.lower().endswith('.mp4')]
        if files:
            src_video = os.path.join(orig_dir, files[0])
            print(f"대체 비디오 복사 중: {src_video} -> {dest_video}")
            shutil.copy2(src_video, dest_video)
        else:
            print("복사할 수 있는 비디오가 없습니다. 빈 더미 파일을 생성합니다.")
            with open(dest_video, 'wb') as f:
                f.write(b'')
                
    print("2. AI 에이전트 수동 즉시 실행 시퀀스(run_once)를 구동합니다...")
    # run_once()는 비동기 함수
    await agent_engine.run_once()
    print("3. 전체 시퀀스 실행이 완료되었습니다.")

if __name__ == "__main__":
    asyncio.run(main())
