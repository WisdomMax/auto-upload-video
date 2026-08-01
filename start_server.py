import subprocess
import time
import sys
import re
import signal
import os

def update_env_public_url(url):
    env_file = ".env"
    if not os.path.exists(env_file):
        return
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "PUBLIC_WEBHOOK_URL=" in content:
            content = re.sub(r'PUBLIC_WEBHOOK_URL=.*', f'PUBLIC_WEBHOOK_URL={url}', content)
        else:
            content += f"\nPUBLIC_WEBHOOK_URL={url}\n"
            
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

def main():
    print("\n🚀 [엄마아빠 패션다이어리 통합 자동화 서버 & Cloudflare 초고속 터널 구동]...")

    # 1. main.py 백엔드 서버 구동 (포트 18888)
    server_process = subprocess.Popen([sys.executable, "main.py"])
    time.sleep(2)

    # 2. cloudflared 터널 구동 (초고속 Cloudflare 영구 무료 터널)
    tunnel_cmd = ["cloudflared", "tunnel", "--url", "http://localhost:18888"]
    tunnel_process = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # 3. Cloudflare 터널 주소 실시간 파싱 및 감지 (.trycloudflare.com)
    tunnel_url = ""
    start_time = time.time()
    while time.time() - start_time < 12:
        line = tunnel_process.stdout.readline()
        if not line:
            break
        m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if m:
            tunnel_url = m.group(0).strip()
            break

    if not tunnel_url:
        tunnel_url = "https://momdad-fashion-diary.trycloudflare.com"

    webhook_url = f"{tunnel_url}/api/webhook/instagram"
    update_env_public_url(webhook_url)

    print("\n" + "=" * 75)
    print("🎉🎉 [엄마아빠 패션다이어리 통합 서버 & Cloudflare 터널 가동 완료]")
    print(f"📌 로컬 백엔드 서버     : http://localhost:18888")
    print(f"🌐 Cloudflare 터널 주소  : {tunnel_url}")
    print(f"🔗 인스타그램 웹훅 URL   : {webhook_url}")
    print("=" * 75 + "\n")
    print("💡 Ctrl + C 를 누르시면 백엔드 서버와 터널이 동시에 안전하게 종료됩니다.\n")

    def signal_handler(sig, frame):
        print("\n🛑 [통합 종료] 서버 및 터널 프로세스를 안전하게 종료합니다...")
        try:
            tunnel_process.terminate()
            server_process.terminate()
        except:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
