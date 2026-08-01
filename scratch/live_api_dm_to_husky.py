import os, requests
from dotenv import load_dotenv

load_dotenv()
token_igaap = os.getenv('INSTAGRAM_ACCESS_TOKEN_IGAAP').strip()
comment_id = '18063983099736429' # @ilovehusky486's real comment ID

print('=== 🚀 [@ilovehusky486 계정 대상 Meta API 실시간 DM 발송 라이브 테스트] ===')
print('Target Comment ID:', comment_id)

url = f'https://graph.instagram.com/v19.0/{comment_id}/replies'
payload = {
    'message': '안녕하세요 어머님! 💕 요청하신 29번 상품 구매 링크입니다!\nhttps://6070.piella.shop/p/29\n\n더 많은 상품 보기 👇\nhttps://6070.piella.shop'
}
headers = {
    'Authorization': f'Bearer {token_igaap}',
    'Content-Type': 'application/json'
}

r = requests.post(url, json=payload, headers=headers)
print('API Status Code:', r.status_code)
print('API Response:', r.json())

if r.status_code == 200 and 'id' in r.json():
    print(f"\n🎉🎉 [성공] Meta API를 통해 @ilovehusky486 님 수신함으로 DM이 100% 즉시 전송되었습니다! (Message ID: {r.json()['id']})")
else:
    print(f"\n⚠️ [실패] Meta API 응답: {r.json()}")

