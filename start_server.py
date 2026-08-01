import subprocess
import time
import sys
import re
import signal
import os

def main():
    print("\n🚀 [엄마아빠 패션다이어리 통합 서버 & 터널 구동기 시작]...")

    # 1. main.py 백엔드 서버 구동 (포트 18888)
    server_process = subprocess.Popen([sys.executable, "main.py"])

    # 서버 초기화 대기 (2초)
    time.sleep(2)

    # 2. localtunnel 구동 및 고정 서브도메인(momdad-fashion-diary) 또는 자동 감지
    tunnel_cmd = ["npx", "localtunnel", "--port", "18888", "--subdomain", "momdad-fashion-diary"]
    tunnel_process = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # 3. 터널 주소 실시간 파싱 및 감지
    tunnel_url = "https://momdad-fashion-diary.loca.lt"
    while True:
        line = tunnel_process.stdout.readline()
        if not line:
            break
        m = re.search(r'your url is:\s*(https://[^\s]+)', line)
        if m:
            tunnel_url = m.group(1).strip()
            break

    print("\n" + "=" * 70)
    print("🎉🎉 [통합 자동화 서버 & 터널 가동 완료]")
    print(f"📌 백엔드 로컬 서버 : http://localhost:18888")
    print(f"🌐 터널 실시간 주소  : {tunnel_url}")
    print(f"🔗 인스타그램 웹훅 URL: {tunnel_url}/api/webhook/instagram")
    print("=" * 70 + "\n")
    print("💡 Ctrl + C 를 누르시면 서버와 터널이 함께 안전하게 종료됩니다.\n")

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
