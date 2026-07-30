import os
import sys
import logging
import unicodedata

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import video_agent
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("regenerate_all_pending")

def regenerate_item(product_no, original_filename_keyword, product_code):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_dir = os.path.join(base_dir, "input", "processed")
    originals_dir = os.path.join(base_dir, "uploads", "originals")
    thumbnail_dir = os.path.join(base_dir, "static", "thumbnails")
    
    # 원본 파일 찾기 (유니코드 NFC 정규화 적용)
    original_file = None
    for f in os.listdir(processed_dir):
        normalized_name = unicodedata.normalize('NFC', f)
        if original_filename_keyword in normalized_name:
            original_file = f
            break
            
    if not original_file:
        logger.error(f"Original file keyword '{original_filename_keyword}' not found in input/processed.")
        return False
        
    input_path = os.path.join(processed_dir, original_file)
    output_path = os.path.join(originals_dir, f"prod_{product_code}_{original_file}")
    thumbnail_path = os.path.join(thumbnail_dir, f"{product_code}.webp")
    
    logger.info(f"[{product_code}] Processing video: {input_path} -> {output_path}")
    
    # 1. 자막 합성
    success = video_agent.overlay_code_subtitles(input_path, output_path, product_code)
    
    if success:
        # 2. 썸네일 재생성
        duration = video_agent.get_video_duration(output_path)
        thumb_success = video_agent.extract_webp_thumbnail(output_path, duration, thumbnail_path)
        
        # 3. DB 업데이트
        item = database.get_item_by_code(product_code)
        if item:
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE items SET original_video_path = ? WHERE id = ?", (output_path, item['id']))
            conn.commit()
            conn.close()
            logger.info(f"[{product_code}] Successfully updated DB path and thumbnail.")
            return True
    return False

def main():
    # No. 16 (T00016 / 3번 영상) 재생성
    regenerate_item(16, "3번", "T00016")
    # No. 17 (T00017 / 1번 영상) 재생성
    regenerate_item(17, "1번", "T00017")

if __name__ == "__main__":
    main()
