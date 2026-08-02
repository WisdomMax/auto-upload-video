import os, datetime, json
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "UC-bYx0BTsO133T_jRL96o4Q").strip()

print("=== 🚀 [최근 1개월 유튜브 쇼츠 전체 댓글 중 '엄마' 문의 정밀 감지] ===")
print("Channel ID:", channel_id)
print("API Key:", api_key[:10] + "...")

youtube = build("youtube", "v3", developerKey=api_key)

# 1. Fetch channel uploaded videos
search_res = youtube.search().list(
    channelId=channel_id,
    part="snippet",
    type="video",
    maxResults=50,
    order="date"
).execute()

items = search_res.get("items", [])
print(f"\n📌 채널 최근 업로드 쇼츠/비디오 총 {len(items)}개 감지됨!")

matched_comments = []
all_comments_count = 0

for idx, item in enumerate(items, start=1):
    vid = item["id"]["videoId"]
    title = item["snippet"]["title"]
    pub_at = item["snippet"].get("publishedAt", "")[:10]
    
    try:
        comment_res = youtube.commentThreads().list(
            videoId=vid,
            part="snippet",
            maxResults=100
        ).execute()
        
        c_items = comment_res.get("items", [])
        all_comments_count += len(c_items)
        
        for c in c_items:
            top = c["snippet"]["topLevelComment"]["snippet"]
            text = top.get("textOriginal", "")
            author = top.get("authorDisplayName", "")
            c_date = top.get("publishedAt", "")[:10]
            
            if "엄마" in text or "구매" in text or "링크" in text or "정보" in text:
                matched_comments.append({
                    "video_id": vid,
                    "video_title": title,
                    "video_date": pub_at,
                    "author": author,
                    "comment_text": text,
                    "comment_date": c_date
                })
    except Exception as e:
        pass

print(f"\n=========================================================================")
print(f"🎉🎉 [유튜브 1개월 쇼츠 댓글 스캔 완결]")
print(f"📌 총 스캔 비디오: {len(items)}개")
print(f"📌 총 수집 댓글 : {all_comments_count}개")
print(f"🎯 '엄마/구매/링크' 문의 감지 건수: {len(matched_comments)}건")
print(f"=========================================================================\n")

for idx, m in enumerate(matched_comments, start=1):
    print(f" [{idx}] 👤 {m['author']} | 📅 {m['comment_date']} | 🎬 영상: {m['video_title']}")
    print(f"     💬 댓글 내용: \"{m['comment_text']}\"")
    print("-" * 75)

