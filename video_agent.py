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
            
    # 영상 전체 길이 구하기
    duration = get_video_duration(input_path)
    start_time = max(0.0, duration - 5.0)
    
    # 임시 폴더
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(base_dir, "static", "temp_texts")
    os.makedirs(temp_dir, exist_ok=True)
    
    overlay_img_path = os.path.join(temp_dir, f"overlay_{product_code}.png")
    
    # Pillow를 이용해 투명 PNG 이미지 생성 (1080x1920 규격)
    from PIL import Image, ImageDraw, ImageFont
    
    overlay_img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_img)
    
    # 폰트 로드
    font_size = 54
    if font_path:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()
        
    # 세그먼트별로 색상을 다르게 렌더링하고 중앙 정렬하는 함수
    def draw_mixed_color_text(draw, font, segments, y_position, total_width=1080):
        widths = []
        for text, _ in segments:
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
            except AttributeError:
                w, _ = draw.textsize(text, font=font)
            widths.append(w)
            
        total_text_width = sum(widths)
        start_x = (total_width - total_text_width) // 2
        
        current_x = start_x
        for i, (text, color) in enumerate(segments):
            draw.text(
                (current_x, y_position), 
                text, 
                font=font, 
                fill=color, 
                stroke_width=4, 
                stroke_fill=(0, 0, 0, 255)
            )
            current_x += widths[i]
            
    # 첫째 줄: 댓글에 '엄마'라고 남겨주세요 ('엄마' -> 노란색)
    segments_line1 = [
        ("댓글에 ", (255, 255, 255, 255)),
        ("'엄마'", (255, 223, 0, 255)),
        ("라고 남겨주세요", (255, 255, 255, 255))
    ]
    
    # 둘째 줄: 링크는 프로필 확인! ('프로필' -> 톡톡 튀는 연하늘색/민트)
    segments_line2 = [
        ("링크는 ", (255, 255, 255, 255)),
        ("프로필", (0, 229, 255, 255)),
        (" 확인!", (255, 255, 255, 255))
    ]
    
    # Y 좌표: 화면 세로 중앙(960) 기준 상하 60px 배치
    draw_mixed_color_text(draw, font, segments_line1, 960 - 60)
    draw_mixed_color_text(draw, font, segments_line2, 960 + 60)
    
    # 이미지 저장
    try:
        overlay_img.save(overlay_img_path)
    except Exception as e:
        logger.error(f"Failed to save temporary overlay image: {e}")
        
    text = f"{product_code}"
    
    # filter_complex 사용해서 동영상 스케일링, 좌측 상단 텍스트 추가 후 마지막 5초에 오버레이 PNG 적용
    if font_path:
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
            f"drawtext=fontfile='{font_path}':text='{text}':x=60:y=60:fontsize=60:fontcolor=white[v0];"
            f"[v0][1:v]overlay=0:0:enable='gte(t,{start_time:.2f})'"
        )
    else:
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
            f"drawtext=text='{text}':x=60:y=60:fontsize=60:fontcolor=white[v0];"
            f"[v0][1:v]overlay=0:0:enable='gte(t,{start_time:.2f})'"
        )
        
    cmd = [
        "ffmpeg", "-y", "-i", input_path, "-i", overlay_img_path,
        "-filter_complex", filter_complex,
        "-codec:a", "copy", output_path
    ]
    
    try:
        logger.info(f"Running ffmpeg complex filter overlay for code {product_code}...")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logger.info("ffmpeg complex filter overlay successfully completed.")
        success = True
    except Exception as e:
        logger.error(f"ffmpeg complex filter overlay failed: {e}")
        success = False
    finally:
        # 임시 이미지 파일 정리
        if os.path.exists(overlay_img_path):
            try:
                os.remove(overlay_img_path)
            except:
                pass
                
    return success

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

async def process_video_pipeline(video_path, product_code=None, product_no=None):
    logger.info(f"Processing video pipeline for {video_path}...")
    
    duration = get_video_duration(video_path)
    
    # 기본값 설정
    category = "T"
    title = "엄마아빠 패션다이어리 추천 상품"
    description = "에이전트가 영상 분석을 통해 추천하는 고품질 신상품 정보입니다."
    keyword = "패션아이템"
    
    if not product_code:
        product_code = database.get_next_product_code(category)
    if not product_no:
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
