import os
import subprocess
import logging
import json
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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



def get_pretendard_font(size, weight="black"):
    font_candidates = [
        "/Library/Fonts/Pretendard-Black.otf",
        "/Library/Fonts/Pretendard-ExtraBold.otf",
        "/Library/Fonts/Pretendard-Bold.otf",
        "/Library/Fonts/NotoSansKR-Black.otf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                if "AppleSDGothic" in p:
                    return ImageFont.truetype(p, size, index=6) # Bold index
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def overlay_code_subtitles(input_path, output_path, product_code):
    # 영상 전체 길이 구하기
    duration = get_video_duration(input_path)
    start_time = max(0.0, duration - 5.0)
    
    # 임시 폴더
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(base_dir, "static", "temp_texts")
    os.makedirs(temp_dir, exist_ok=True)
    
    overlay_img_path = os.path.join(temp_dir, f"overlay_{product_code}.png")
    
    # Pillow를 이용해 투명 PNG 이미지 생성 (1080x1920 규격)
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    
    overlay_img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay_img)
    
    # 폰트 로드
    f_tag = get_pretendard_font(34, "black")
    f_main = get_pretendard_font(48, "black")
    
    center_x = 1080 // 2
    
    # 1. 좌상단: 세련된 옐로우 라운드 뱃지 (스마트폰 상단 UI 안전지대 Y=130)
    tag_text = f"{product_code}"
    tb = d.textbbox((0, 0), tag_text, font=f_tag)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    
    # 드롭 섀도우
    sh_img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(sh_img)
    tag_x1, tag_y1 = 60, 130
    tag_x2, tag_y2 = tag_x1 + tw + 44, tag_y1 + th + 24
    sh_draw.rounded_rectangle([tag_x1, tag_y1 + 6, tag_x2, tag_y2 + 6], radius=16, fill=(0, 0, 0, 120))
    sh_img = sh_img.filter(ImageFilter.GaussianBlur(14))
    overlay_img.alpha_composite(sh_img)
    
    # 뱃지 본체 (비비드 옐로우)
    d.rounded_rectangle([tag_x1, tag_y1, tag_x2, tag_y2], radius=16, fill=(250, 204, 21, 255))
    d.text((tag_x1 + 22, tag_y1 + 12 - tb[1]), tag_text, font=f_tag, fill=(15, 23, 42, 255))
    
    # 2. 중앙: S-2 인스타그램 스토리 스티커 바 (Y=1240)
    # [ 댓글에 ] + [ 엄마 (옐로우 칩) ] + [ 남겨주세요! ]
    txt1 = "댓글에"
    txt_hi = "엄마"
    txt2 = "남겨주세요!"
    
    bb1 = d.textbbox((0, 0), txt1, font=f_main)
    bbh = d.textbbox((0, 0), txt_hi, font=f_main)
    bb2 = d.textbbox((0, 0), txt2, font=f_main)
    
    w1 = bb1[2] - bb1[0]
    wh = bbh[2] - bbh[0]
    w2 = bb2[2] - bb2[0]
    
    CHIP_PAD = 16
    m_box_w = wh + (CHIP_PAD * 2)
    GAP = 18
    
    tot_content_w = w1 + GAP + m_box_w + GAP + w2
    stk_h = 86
    stk_w = tot_content_w + 64
    stk_x1 = center_x - (stk_w // 2)
    stk_x2 = center_x + (stk_w // 2)
    stk_y1 = 1240
    stk_y2 = stk_y1 + stk_h
    
    # 스티커 섀도우
    sh_stk = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    sh_stk_draw = ImageDraw.Draw(sh_stk)
    sh_stk_draw.rounded_rectangle([stk_x1, stk_y1 + 8, stk_x2, stk_y2 + 8], radius=22, fill=(0, 0, 0, 140))
    sh_stk = sh_stk.filter(ImageFilter.GaussianBlur(16))
    overlay_img.alpha_composite(sh_stk)
    
    # 메인 다크 반투명 칩 (알파 215, 약 84% 불투명)
    d.rounded_rectangle([stk_x1, stk_y1, stk_x2, stk_y2], radius=22, fill=(0, 0, 0, 215))
    
    base_stk_y = stk_y1 + (stk_h // 2)
    cur_x = center_x - (tot_content_w // 2)
    
    # '댓글에'
    d.text((cur_x, base_stk_y - ((bb1[3] - bb1[1]) // 2) - bb1[1]), txt1, font=f_main, fill=(255, 255, 255, 255))
    cur_x += w1 + GAP
    
    # '엄마' 형광 옐로우 스티커 칩
    chip_y1 = stk_y1 + 10
    chip_y2 = stk_y2 - 10
    d.rounded_rectangle([cur_x, chip_y1, cur_x + m_box_w, chip_y2], radius=14, fill=(250, 204, 21, 255))
    d.text((cur_x + CHIP_PAD, base_stk_y - ((bbh[3] - bbh[1]) // 2) - bbh[1]), txt_hi, font=f_main, fill=(0, 0, 0, 255))
    cur_x += m_box_w + GAP
    
    # '남겨주세요!'
    d.text((cur_x, base_stk_y - ((bb2[3] - bb2[1]) // 2) - bb2[1]), txt2, font=f_main, fill=(255, 255, 255, 255))
    
    # 이미지 저장
    try:
        overlay_img.save(overlay_img_path)
    except Exception as e:
        logger.error(f"Failed to save temporary overlay image: {e}")
        
    # 1. 원본 영상 화각과 화질 100% 보존하며 1080x1920 규격 맞춤 (워터마크 인위적 조작 없음)
    filter_complex = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black[v0];"
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
