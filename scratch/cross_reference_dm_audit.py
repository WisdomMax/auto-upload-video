import os, requests, json
from dotenv import load_dotenv

load_dotenv()
token_igaap = os.getenv('INSTAGRAM_ACCESS_TOKEN_IGAAP').strip()

print("=== 🔍 [인스타그램 1~29번 릴스 전체 댓글 유저 vs DM 전송 완료 유저 정밀 대조] ===")

# 1. 릴스 전체 댓글 유저 수집 (Commenter List)
media_url = f"https://graph.instagram.com/v19.0/me/media?fields=id,caption,comments{{id,text,username,from}}&limit=50&access_token={token_igaap}"
r_media = requests.get(media_url)
media_data = r_media.json().get('data', [])

all_commenters = {} # {username: {comment_id, product_no}}

for m in media_data:
    caption = m.get('caption', '')
    comments = m.get('comments', {}).get('data', [])
    for c in comments:
        uname = c.get('from', {}).get('username')
        cid = c.get('id')
        if uname and uname != 'momdad_style':
            if uname not in all_commenters:
                all_commenters[uname] = {
                    'comment_id': cid,
                    'username': uname,
                    'text': c.get('text', '')
                }

print(f"📌 1. 전체 릴스 댓글 유저 총 수: {len(all_commenters)}명")

# JSON 저장
with open("scratch/audit_commenters.json", "w", encoding="utf-8") as out:
    json.dump(all_commenters, out, ensure_ascii=False, indent=2)

