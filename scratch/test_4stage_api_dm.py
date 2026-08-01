import os, requests, time
from dotenv import load_dotenv

load_dotenv()
token_igaap = os.getenv('INSTAGRAM_ACCESS_TOKEN_IGAAP').strip()
comment_id = '18063983099736429'
prod_no = '29'

print(f"=== 🚀 [@ilovehusky486 대상 API 4단계 완전 독립 말풍선 DM 2.5초 간격 발송] ===")

messages = [
    f"안녕하세요 어머님! 💕 요청하신 {prod_no}번 상품 구매 링크입니다!",
    f"https://6070.piella.shop/p/{prod_no}",
    "더 많은 예쁜 옷들은 여기서 구경하세요 👇",
    "https://6070.piella.shop"
]

url = 'https://graph.instagram.com/v19.0/me/messages'
headers = {
    'Authorization': f'Bearer {token_igaap}',
    'Content-Type': 'application/json'
}

for idx, msg_text in enumerate(messages, start=1):
    payload = {
        'recipient': {'comment_id': comment_id},
        'message': {'text': msg_text}
    }
    r = requests.post(url, json=payload, headers=headers)
    print(f"  [{idx}/4] 발송 상태: {r.status_code}, Res: {r.json()}")
    time.sleep(2.5)

print("\n🎉🎉 4단계 독립 말풍선 API 연속 발송 완결!")
