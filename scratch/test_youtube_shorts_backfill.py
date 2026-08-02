import os, re, json, datetime, requests
from dotenv import load_dotenv

load_dotenv()

print("=== 🚀 [최근 1개월 유튜브 쇼츠 영상 전체 댓글 중 '엄마' 문의 감지 테스트] ===")

# Try YouTube Data API with token or API Key
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
token_path = "token.json"
channel_id = "UC-bYx0BTsO133T_jRL96o4Q"

youtube = None
if os.path.exists(token_path):
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        youtube = build("youtube", "v3", credentials=creds)
        print("✅ YouTube Credentials Loaded Successfully!")
    except Exception as e:
        print(f"⚠️ Credentials Error: {e}")

if not youtube:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        youtube = build("youtube", "v3", developerKey=api_key)
        print("✅ YouTube API Key Loaded!")

if not youtube:
    print("❌ YouTube Service could not be built. OAuth login required.")
    exit(1)

# Fetch videos published in the last 30 days
one_month_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat() + "Z"
print(f"📌 검색 시작일 (최근 30일): {one_month_ago}")

search_res = youtube.search().list(
    channelId=channel_id,
    part="snippet",
    type="video",
    maxResults=50,
    publishedAfter=one_month_ago,
    order="date"
).execute()

items = search_res.get("items", [])
print(f"📌 최근 1개월 간 업로드된 쇼츠/영상 수: {len(items)}개")

matched_comments = []

for idx, v in enumerate(items, start=1):
    vid = v["id"]["videoId"]
    title = v["snippet"]["title"]
    print(f"  [{idx}/{len(items)}] 비디오: {title} (ID: {vid})")
    
    try:
        comment_res = youtube.commentThreads().list(
            videoId=vid,
            part="snippet",
            maxResults=100
        ).execute()
        
        c_items = comment_res.get("items", [])
        for c in c_items:
            top_comment = c["snippet"]["topLevelComment"]["snippet"]
            text = top_comment.get("textOriginal", "")
            author = top_comment.get("authorDisplayName", "")
            
            if "엄마" in text:
                matched_comments.append({
                    "video_id": vid,
                    "video_title": title,
                    "author": author,
                    "text": text,
                    "published_at": top_comment.get("publishedAt")
                })
    except Exception as e_c:
        print(f"    ⚠️ 댓글 조회 건너뜀 (댓글 비활성화 등): {e_c}")

print(f"\n🎉🎉 [감지 결과] 최근 1개월 쇼츠 영상 중 '엄마' 문의 댓글 총: {len(matched_comments)}건 발견!")
for idx, m in enumerate(matched_comments, start=1):
    print(f"  {idx}. [{m['author']}] 비디오: {m['video_title']} -> 댓글: '{m['text']}' ({m['published_at']})")

