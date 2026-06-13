import os
import subprocess
import logging
import json
import re
from PIL import Image
import google.generativeai as genai
import database

logger = logging.getLogger("video_agent")

def get_video_duration(video_path):
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Error getting video duration: {e}")
        return 10.0  # fallback 기본값

def capture_frames(video_path, duration, num_frames=3):
    frames = []
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "temp_frames")
    os.makedirs(temp_dir, exist_ok=True)
    
    # 영상에서 고른 간격으로 캡처 시각 결정
    intervals = [duration * (i + 1) / (num_frames + 1) for i in range(num_frames)]
    
    for idx, sec in enumerate(intervals):
        frame_name = f"frame_{idx}.jpg"
        frame_path = os.path.join(temp_dir, frame_name)
        
        cmd = [
            "ffmpeg", "-y", "-ss", f"{sec:.2f}", "-i", video_path,
            "-vframes", "1", "-q:v", "2", frame_path
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if os.path.exists(frame_path):
                frames.append(frame_path)
        except Exception as e:
            logger.error(f"Failed to capture frame at {sec}s: {e}")
            
    return frames



def overlay_code_subtitles(input_path, output_path, product_code):
    font_paths = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/Library/Fonts/NanumGothic.ttf",
        "AppleGothic.ttf"
    ]
    font_path = None
    for path in font_paths:
        if os.path.exists(path):
            font_path = path
            break
            
    text = f"{product_code}"
    
    # 1080x1920 규격으로 스케일링(비율 유지) 후 빈 여백은 검은색 패딩 처리, 그 위에 자막 고정 합성
    # 폰트 크기 60pt, 여백 x=60, y=60 고정 적용하여 해상도와 관계없이 무조건 위치/크기 통일
    if font_path:
        vf_filter = (
            f"scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
            f"drawtext=fontfile='{font_path}':text='{text}':x=60:y=60:fontsize=60:fontcolor=white"
        )
    else:
        vf_filter = (
            f"scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
            f"drawtext=text='{text}':x=60:y=60:fontsize=60:fontcolor=white"
        )
        
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf_filter,
        "-codec:a", "copy", output_path
    ]
    
    try:
        logger.info(f"Running ffmpeg standardized overlay for code {product_code} (Target: 1080x1920, Fontsize: 60)...")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logger.info("ffmpeg standardized overlay successfully completed.")
        return True
    except Exception as e:
        logger.error(f"ffmpeg overlay command failed: {e}")
        return False

def extract_webp_thumbnail(video_path, duration, output_path):
    sec = duration * 0.95
    temp_jpeg_path = output_path + ".temp.jpg"
    
    # 1. 임시 JPEG 파일로 비디오 프레임 추출 (코덱 독립적)
    cmd = [
        "ffmpeg", "-y", "-ss", f"{sec:.2f}", "-i", video_path,
        "-vframes", "1", "-vf", "scale=540:960", temp_jpeg_path
    ]
    try:
        logger.info(f"Extracting temporary frame to {temp_jpeg_path}...")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        if os.path.exists(temp_jpeg_path):
            # 2. PIL을 이용하여 JPEG -> WEBP 인코딩 변환
            logger.info(f"Converting temporary JPEG to WebP at {output_path}...")
            with Image.open(temp_jpeg_path) as img:
                img.save(output_path, "WEBP", quality=85)
            
            # 임시 파일 정리
            os.remove(temp_jpeg_path)
            return True
        else:
            logger.error("Temporary JPEG frame was not created.")
            return False
    except Exception as e:
        logger.error(f"Failed to extract or convert webp thumbnail: {e}")
        if os.path.exists(temp_jpeg_path):
            try:
                os.remove(temp_jpeg_path)
            except:
                pass
        return False

async def process_video_pipeline(video_path):
    logger.info(f"Processing video pipeline for {video_path}...")
    
    duration = get_video_duration(video_path)
    
    # 기본값 설정
    category = "T"
    title = "엄마아빠 패션다이어리 추천 상품"
    description = "에이전트가 영상 분석을 통해 추천하는 고품질 신상품 정보입니다."
    keyword = "패션아이템"
    
    product_code = database.get_next_product_code(category)
    product_no = database.get_next_product_no()
    
    # 2. ffmpeg drawtext 자막 인코딩 수행
    originals_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "originals")
    os.makedirs(originals_dir, exist_ok=True)
    
    filename = os.path.basename(video_path)
    clean_filename = re.sub(r'[^a-zA-Z0-9._]', '_', filename)
    output_video_path = os.path.join(originals_dir, f"prod_{product_code}_{clean_filename}")
    
    overlay_success = overlay_code_subtitles(video_path, output_video_path, product_code)
    if not overlay_success:
        import shutil
        shutil.copy2(video_path, output_video_path)
        logger.warning("ffmpeg overlay failed, fallback to copying original video.")
        
    # 3. webp 전신 썸네일 이미지 추출
    thumbnail_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "thumbnails")
    os.makedirs(thumbnail_dir, exist_ok=True)
    output_thumbnail_path = os.path.join(thumbnail_dir, f"{product_code}.webp")
    
    extract_webp_thumbnail(video_path, duration, output_thumbnail_path)
    
    return {
        "product_no": product_no,
        "product_code": product_code,
        "title": title,
        "description": description,
        "keyword": keyword,
        "original_video_path": output_video_path
    }
