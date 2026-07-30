import os
import sys
import logging

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import video_agent
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_overlay")

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_dir = os.path.join(base_dir, "input", "processed")
    originals_dir = os.path.join(base_dir, "uploads", "originals")
    thumbnail_dir = os.path.join(base_dir, "static", "thumbnails")
    
    # 2번.mp4 원본 파일 찾기 (자모 분리 대응을 위해 검색)
    original_file = None
    for f in os.listdir(processed_dir):
        if "2번" in f or "2" in f:
            original_file = f
            break
            
    if not original_file:
        logger.error("Original file for '2번.mp4' not found in input/processed.")
        return
        
    input_path = os.path.join(processed_dir, original_file)
    output_path = os.path.join(originals_dir, "prod_T00015_2___.mp4")
    thumbnail_path = os.path.join(thumbnail_dir, "T00015.webp")
    
    logger.info(f"Using input video: {input_path}")
    logger.info(f"Target output video: {output_path}")
    logger.info(f"Target thumbnail: {thumbnail_path}")
    
    # 1. 자막 합성
    logger.info("Applying ffmpeg overlay...")
    success = video_agent.overlay_code_subtitles(input_path, output_path, "T00015")
    
    if success:
        logger.info("Subtitles overlaid successfully.")
        
        # 2. 썸네일 재생성
        duration = video_agent.get_video_duration(output_path)
        logger.info(f"Video duration: {duration}s. Extracting webp thumbnail...")
        thumb_success = video_agent.extract_webp_thumbnail(output_path, duration, thumbnail_path)
        
        if thumb_success:
            logger.info("WebP thumbnail extracted successfully.")
        else:
            logger.error("Failed to extract WebP thumbnail.")
            
        # 3. DB 업데이트 확인 (original_video_path)
        item = database.get_item_by_code("T00015")
        if item:
            logger.info(f"DB Item T00015 found (ID: {item['id']}). Updating original_video_path...")
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE items SET original_video_path = ? WHERE id = ?", (output_path, item['id']))
            conn.commit()
            conn.close()
            logger.info("DB path updated successfully.")
        else:
            logger.warning("DB Item T00015 not found. Skipping path update.")
    else:
        logger.error("Failed to apply overlay.")

if __name__ == "__main__":
    main()
