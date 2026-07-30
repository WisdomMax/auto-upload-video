import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 로깅 기본 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

import catalog_builder

def run_build():
    try:
        catalog_builder.build_catalog()
        print("정적 카탈로그 빌드가 성공적으로 완료되었습니다.")
    except Exception as e:
        print(f"정적 카탈로그 빌드 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_build()
