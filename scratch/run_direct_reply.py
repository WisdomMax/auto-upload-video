import asyncio, os, dotenv, httpx, json
import database, instagram_api

dotenv.load_dotenv()
token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
media_id = "3945313537111603053" # 28번 릴스 미디어 ID

print("=== 28번 릴스 직행 타깃팅 대댓글 & DM 발송 개시 ===")

item28 = database.get_item_by_product_no(28)
coupang_link = item28.get("short_url") or item28.get("coupang_url")
catalog_link = "https://6070.piella.shop/p/28"
title = item28["title"]

print(f"타깃 상품: [{title}]")
print(f"쿠팡 링크: {coupang_link}")

# 메타 API 댓글 직접 쿼리 (라이브 모드 전용 토큰)
url_comments = f"https://graph.facebook.com/v17.0/{media_id}/comments?fields=id,text,from,username&access_token={token}"

try:
    res = httpx.get(url_comments).json()
    print("Direct Comments Response:", json.dumps(res, indent=2, ensure_ascii=False))
    
    data = res.get("data", [])
    if data:
        target_c = data[0]
        cid = target_c.get("id")
        cuser = target_c.get("username") or target_c.get("from", {}).get("username", "어머님")
        ctext = target_c.get("text", "")
        
        print(f"\n🚀 [실제 대댓글 발송 대상] 댓글 ID: {cid} | 작성자: @{cuser} | 본문: '{ctext}'")
        
        reply_msg = f"@{cuser} 안녕하세요 어머님! 요청하신 28번 상품 상세 정보와 쿠팡 구매 링크를 메시지(DM)로 전송해 드렸습니다! 💕"
        
        # 대댓글 쓰기 API
        reply_url = f"https://graph.facebook.com/v17.0/{cid}/replies"
        res_reply = httpx.post(reply_url, data={"message": reply_msg, "access_token": token}).json()
        print("=== 대댓글 작성 API 최종 결과 ===")
        print(res_reply)
        
except Exception as e:
    print("❌ 실행 중 예외:", e)
