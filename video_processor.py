import os
from PIL import Image, ImageDraw, ImageFont
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

def get_korean_font(size=30):
    # macOS 기본 한글 폰트 경로들
    font_paths = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
        "AppleGothic.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    # 만약 위 폰트들이 다 실패하면 기본 폰트 반환
    return ImageFont.load_default()

def add_subtitle_to_video(input_path, output_path, product_no, title, subtitle_text):
    """
    영상 하단에 [No. product_no | title] 과 [subtitle_text] 자막을 오버레이하여 새로운 영상으로 저장합니다.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"원본 비디오 파일을 찾을 수 없습니다: {input_path}")
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. 원본 비디오 로드 및 규격 획득
    video = VideoFileClip(input_path)
    width, height = video.size
    duration = video.duration
    
    # 2. Pillow를 사용해 오버레이 투명 이미지 생성
    # 비디오 해상도 크기와 동일하게 투명 캔버스 생성
    overlay_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay_img)
    
    # 폰트 로드
    font_large = get_korean_font(int(height * 0.045))  # 비디오 높이에 비례한 폰트 크기 (예: 1080p 기준 약 48px)
    font_small = get_korean_font(int(height * 0.035))  # (예: 1080p 기준 약 38px)
    
    # 자막 텍스트 구성
    line1 = f"No. {product_no} | {title}"
    line2 = subtitle_text
    
    # 자막 위치 계산 (하단 배치)
    # 하단 18% 영역을 자막 영역으로 지정
    box_height = int(height * 0.18)
    box_y1 = height - box_height - int(height * 0.05)
    box_y2 = height - int(height * 0.05)
    box_x1 = int(width * 0.05)
    box_x2 = width - int(width * 0.05)
    
    # 3. 반투명 배경 박스 그리기
    # 검은색 배경에 알파값 약 180 (약 70% 투명도)
    draw.rounded_rectangle(
        [box_x1, box_y1, box_x2, box_y2], 
        radius=15, 
        fill=(0, 0, 0, 180)
    )
    
    # 텍스트 바운딩 박스를 구해 가로 중앙 정렬
    # Pillow 9.2+ 이후 textbbox 권장
    try:
        l1_bbox = draw.textbbox((0, 0), line1, font=font_large)
        l1_w = l1_bbox[2] - l1_bbox[0]
        l1_h = l1_bbox[3] - l1_bbox[1]
    except AttributeError:
        # 구버전 Pillow 대응
        l1_w, l1_h = draw.textsize(line1, font=font_large)
        
    try:
        l2_bbox = draw.textbbox((0, 0), line2, font=font_small)
        l2_w = l2_bbox[2] - l2_bbox[0]
        l2_h = l2_bbox[3] - l2_bbox[1]
    except AttributeError:
        l2_w, l2_h = draw.textsize(line2, font=font_small)
        
    # 텍스트 좌표 계산 (박스 내 중앙 정렬)
    box_center_x = (box_x1 + box_x2) // 2
    l1_x = box_center_x - (l1_w // 2)
    l2_x = box_center_x - (l2_w // 2)
    
    padding = int(box_height * 0.15)
    l1_y = box_y1 + padding
    l2_y = l1_y + l1_h + int(box_height * 0.12)
    
    # 텍스트 드로잉
    # 노란색으로 강조된 상품번호와 흰색 텍스트
    draw.text((l1_x, l1_y), line1, font=font_large, fill=(255, 223, 0, 255)) # Gold/Yellow
    draw.text((l2_x, l2_y), line2, font=font_small, fill=(255, 255, 255, 255)) # White
    
    # 임시 이미지 파일로 저장
    temp_overlay_path = os.path.join(os.path.dirname(output_path), f"temp_overlay_{product_no}.png")
    overlay_img.save(temp_overlay_path)
    
    try:
        # 4. MoviePy 합성 실행
        overlay_clip = ImageClip(temp_overlay_path).set_duration(duration).set_position(("center", "top"))
        final_video = CompositeVideoClip([video, overlay_clip])
        
        # CPU 코어 수 활용 및 오디오 전송 보장
        final_video.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            temp_audiofile=os.path.join(os.path.dirname(output_path), f"temp_audio_{product_no}.mp3"),
            remove_temp=True
        )
    finally:
        # 리소스 정리
        video.close()
        try:
            if os.path.exists(temp_overlay_path):
                os.remove(temp_overlay_path)
        except:
            pass

if __name__ == "__main__":
    # 임시 기능 테스트용 코드
    print("Video Processor 모듈 로드 완료. get_korean_font 테스트:")
    font = get_korean_font(30)
    print("선택된 폰트 객체:", font)
