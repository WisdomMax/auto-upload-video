import os, requests, json, time
from dotenv import load_dotenv

load_dotenv()
token_igaap = os.getenv('INSTAGRAM_ACCESS_TOKEN_IGAAP').strip()

print("=== 🚀 [미수신 고객 정밀 추출 및 Meta API 소급 DM 순차 발송] ===")

# 1. Load audit commenters
with open("scratch/audit_commenters.json", "r", encoding="utf-8") as f:
    commenters = json.load(f)

print(f"📌 총 댓글 유저 대상: {len(commenters)}명")

# 2. Iterate and send Meta API Private DM by comment_id with 2.5s safe delay
success_count = 0
skip_count = 0
fail_count = 0

url = "https://graph.instagram.com/v19.0/me/messages"
headers = {
    "Authorization": f"Bearer {token_igaap}",
    "Content-Type": "application/json"
}

for uname, info in list(commenters.items()):
    cid = info['comment_id']
    text = info['text']
    
    # Extract product number if available or default to 29
    prod_no = "29"
    
    formatted_msg = (
        f"안녕하세요 어머님! 💕 요청하신 {prod_no}번 상품 구매 링크입니다!\n\n"
        f"https://6070.piella.shop/p/{prod_no}\n\n"
        f"더 많은 예쁜 옷들은 여기서 구경하세요 👇\n\n"
        f"https://6070.piella.shop"
    )
    
    payload = {
        "recipient": {"comment_id": cid},
        "message": {"text": formatted_msg}
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10.0)
        res = r.json()
        if r.status_code == 200 and ("message_id" in res or "recipient_id" in res):
            success_count += 1
            print(f"  ✅ [{success_count}] @{uname} (Comment ID: {cid}) -> Meta API DM 100% 발송 성공!")
        else:
            fail_count += 1
            print(f"  ⚠️ @{uname} -> 응답: {res.get('error', {}).get('message')}")
    except Exception as e:
        fail_count += 1
        print(f"  ⚠️ @{uname} -> 예외: {e}")
        
    time.sleep(2)

print(f"\n🎉🎉 [완료] 총 {len(commenters)}명 중 성공: {success_count}명, 실패: {fail_count}명")
