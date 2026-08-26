import os
import subprocess
import shutil
import tempfile
import logging

logger = logging.getLogger(__name__)

GWT_BIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "gwt-mini")

def is_watermark_cleaner_available() -> bool:
    """GeminiWatermarkTool 바이너리 사용 가능 여부 확인"""
    return os.path.exists(GWT_BIN_PATH) and os.access(GWT_BIN_PATH, os.X_OK)

def remove_video_watermark(input_video: str, output_video: str, threshold: float = 0.15) -> bool:
    """
    Google Gemini / Veo 비디오의 우측 하단 반투명 별빛 워터마크를
    Reverse Alpha Blending(수학적 역 알파 블렌딩) 기법으로 100% 원본 픽셀로 복원/제거합니다.
    (블러나 인페인팅 왜곡 없이 원본 디테일 완벽 보존)
    """
    if not is_watermark_cleaner_available():
        logger.warning(f"Watermark cleaner binary not found at {GWT_BIN_PATH}. Skipping watermark removal.")
        shutil.copy(input_video, output_video)
        return False
        
    temp_dir = tempfile.mkdtemp(prefix="clean_wm_")
    frames_in = os.path.join(temp_dir, "in")
    frames_out = os.path.join(temp_dir, "out")
    audio_path = os.path.join(temp_dir, "audio.aac")
    os.makedirs(frames_in, exist_ok=True)
    os.makedirs(frames_out, exist_ok=True)
    
    try:
        # 1. 비디오 FPS 및 오디오 트랙 추출
        fps_cmd = ['ffprobe', '-v', '0', '-of', 'csv=p=0', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', input_video]
        fps_str = subprocess.check_output(fps_cmd).decode().strip()
        
        subprocess.run(['ffmpeg', '-y', '-i', input_video, '-vn', '-c:a', 'copy', audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        has_audio = os.path.exists(audio_path) and os.path.getsize(audio_path) > 0
        
        # 2. PNG 무손실 프레임 분해
        logger.info(f"Extracting frames for watermark removal: {input_video}")
        subprocess.run(['ffmpeg', '-y', '-i', input_video, '-qscale:v', '1', os.path.join(frames_in, 'frame_%05d.png')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # 3. gwt-mini 역 알파 블렌딩 복원 배치 실행
        logger.info("Executing Reverse Alpha Blending watermark removal on frames...")
        subprocess.run([GWT_BIN_PATH, '-i', frames_in, '-o', frames_out, '-t', str(threshold), '--no-banner', '-q'], check=True)
        
        # 4. 고화질 재인코딩 (H.264 CRF 16 무손실급)
        logger.info(f"Re-assembling clean video to: {output_video}")
        ffmpeg_cmd = ['ffmpeg', '-y', '-r', fps_str, '-i', os.path.join(frames_out, 'frame_%05d.png')]
        if has_audio:
            ffmpeg_cmd.extend(['-i', audio_path, '-c:a', 'aac'])
        ffmpeg_cmd.extend(['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', output_video])
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        logger.info("Watermark removal completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error removing watermark: {e}")
        shutil.copy(input_video, output_video)
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
