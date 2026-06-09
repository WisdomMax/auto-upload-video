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

async def analyze_video_frames_with_gemini(frame_paths):
    api_key = database.get_setting("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set. Skipping AI frame analysis.")
        return None
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        images = []
        for path in frame_paths:
            if os.path.exists(path):
                images.append(Image.open(path))
                
        if not images:
            return None
            
        prompt = """
        당신은 숏폼 전문 패션 마케팅 에이전트입니다.
        제공된 비디오 프레임들을 유심히 분석하여 의류 정보를 분류하고 마케팅 문구를 제안해 주세요.
        
        1. 카테고리(category): 아래의 5가지 접두사 중 무조건 하나로만 결정하셔야 합니다.
           - O: 아우터 (자켓, 코트, 카디건 등)
           - T: 상의 (티셔츠, 블라우스, 니트, 셔츠, 나시 등)
           - P: 하의 (슬랙스, 팬츠, 데님, 스커트 등)
           - D: 원피스 (드레스)
           - S: 신발 및 패션 잡화 (샌들, 단화, 가방 등)
        2. 상품명(title): 의류의 특징이나 장점을 포함한 15자 내외의 클릭하고 싶은 상품명.
        3. 상세설명(description): 린넨, 면 등 재질감이나 시원함/찰랑거림, 추천 코디법을 다정하고 명확하게 적은 2줄 이내의 소개글.
        4. 주요 키워드(keyword): 대표 검색 키워드 하나 (예: 린넨바지, 어머니원피스 등).
        
        반드시 백틱(```json)이나 다른 설명 없이 아래 JSON 규격만 정밀하게 리턴해 주세요.
        {
            "category": "T",
            "title": "린넨 루즈핏 블라우스",
            "description": "린넨 혼방 소재로 한여름에도 시원하게 입을 수 있는 깔끔한 루즈핏 블라우스입니다. 데님이나 스커트 어디에나 찰떡 코디 가능해요!",
            "keyword": "린넨블라우스"
        }
        """
        
        response = model.generate_content(
            [prompt] + images,
            generation_config={"response_mime_type": "application/json"}
        )
        
        if response and response.text:
            data = json.loads(response.text.strip())
            logger.info(f"AI Frame Analysis Result: {data}")
            return data
            
    except Exception as e:
        logger.error(f"Gemini AI video frame analysis failed: {e}")
        
    return None

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
    sec = duration * 0.8
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
    
    # 1. 비디오 프레임 추출 및 Gemini 분석 수행
    try:
        frames = capture_frames(video_path, duration, num_frames=3)
        if frames:
            logger.info(f"Captured {len(frames)} frames for AI analysis: {frames}")
            ai_data = await analyze_video_frames_with_gemini(frames)
            if ai_data:
                category = ai_data.get("category", "T")
                title = ai_data.get("title", title)
                description = ai_data.get("description", description)
                keyword = ai_data.get("keyword", keyword)
                logger.info(f"Successfully extracted product info via Gemini: {ai_data}")
            
            # 임시 프레임 파일 정리
            for f in frames:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception as rm_err:
                        logger.error(f"Failed to remove temp frame {f}: {rm_err}")
    except Exception as ai_err:
        logger.error(f"Error during AI video analysis: {ai_err}")
        
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
