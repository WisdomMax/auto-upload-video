import sys
import os
import asyncio
import json

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import database

client = TestClient(app)

def test_instagram_webhook_verification():
    """
    1. GET /webhook/instagram 챌린지 검증 테스트
    """
    print("\n=== Test 1: Webhook Verification (GET) ===")
    
    # 1-1. 토큰 일치하는 경우
    verify_token = "my_test_verify_token"
    os.environ["INSTAGRAM_VERIFY_TOKEN"] = verify_token
    
    challenge_str = "123456789"
    response = client.get(
        "/webhook/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": challenge_str,
            "hub.verify_token": verify_token
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    assert response.status_code == 200
    assert response.text == challenge_str
    print("✅ Webhook Verification (Success case) Passed!")
    
    # 1-2. 토큰 불일치하는 경우
    response_fail = client.get(
        "/webhook/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": challenge_str,
            "hub.verify_token": "wrong_token"
        }
    )
    print(f"Fail case Status Code: {response_fail.status_code}")
    assert response_fail.status_code == 403
    print("✅ Webhook Verification (Failure case) Passed!")

def test_instagram_webhook_event():
    """
    2. POST /webhook/instagram 댓글 수신 이벤트 테스트
    """
    print("\n=== Test 2: Webhook Event Receiving (POST) ===")
    
    # DB 초기화 및 테스트 데이터 삽입 확인
    database.init_db()
    
    # 임의의 상품 정보 가져오기 (가장 최신 상품 폴백 테스트용)
    items = database.get_items()
    if not items:
        # 테스트용 임시 상품 하나 주입
        print("No items in DB. Creating a test product...")
        database.create_item(
            product_no=999,
            title="테스트용 꽃무늬 원피스",
            description="어머님들이 입기 좋은 편안한 린넨 소재 원피스입니다.",
            coupang_url="https://coupang.com/test",
            original_video_path="input/test.mp4",
            product_code="T00999"
        )
    
    # 모의 인스타그램 웹북 페이로드
    mock_payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "INST_BIZ_ACC_123",
                "time": 1721410000,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "MOCK_COMMENT_9999",
                            "text": "이 옷 너무 이쁘네요! 정보 부탁드려요.",
                            "from": {
                                "id": "USER_SCOPED_777",
                                "username": "pretty_grandma"
                            },
                            "media": {
                                "id": "MOCK_MEDIA_888",
                                "media_product_type": "REELS"
                            }
                        }
                    }
                ]
            }
        ]
    }
    
    # 봇 계정 ID 환경 변수 임시 설정 (무한 루프 차단 테스트용)
    os.environ["INSTAGRAM_BUSINESS_ACCOUNT_ID"] = "INST_BIZ_ACC_123"
    
    # 이벤트 POST 전송
    response = client.post("/webhook/instagram", json=mock_payload)
    print(f"Event Status Code: {response.status_code}")
    print(f"Event Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Webhook Event Receiving Route Passed!")

if __name__ == "__main__":
    test_instagram_webhook_verification()
    test_instagram_webhook_event()
    print("\n🎉 All integration router logic tests passed successfully!")
