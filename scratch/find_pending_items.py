import sys
import os

# 현재 폴더를 sys.path에 추가
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import database

def find_pending():
    items = database.get_items()
    pending_items = []
    default_prefixes = ["60대 이후 옷 잘 입는", "60대 어머님들", "60대 이후 입으면", "60대 70대 어머님들"]
    
    print(f"전체 상품 개수: {len(items)}")
    for item in items:
        # DB 컬럼 값 가져오기
        item_id = item.get("id")
        title = item.get("title") or ""
        desc = item.get("description") or ""
        yt_title = item.get("youtube_title") or ""
        yt_desc = item.get("youtube_description") or ""
        coupang_url = item.get("coupang_url") or ""
        short_url = item.get("short_url") or ""
        
        is_empty = not yt_title or not yt_desc
        is_default_title = any(yt_title.startswith(p) for p in default_prefixes) or "엄마아빠 패션다이어리" in yt_title or "추천 상품" in yt_title
        is_default_desc = "에이전트가 영상 분석을 통해" in yt_desc or "에이전트가 추천한" in yt_desc or not yt_desc
        
        if is_empty or is_default_title or is_default_desc:
            pending_items.append({
                "id": item_id,
                "title": title,
                "description": desc,
                "youtube_title": yt_title,
                "youtube_description": yt_desc,
                "coupang_url": coupang_url,
                "short_url": short_url
            })
            
    print(f"미완료 상품 개수: {len(pending_items)}")
    for p in pending_items[:5]: # 너무 많을 수 있으니 우선 5개 출력
        print(f"ID: {p['id']} | 원본제목: {p['title']} | 설명: {p['description'][:30]}... | 유튜브제목: {p['youtube_title']}")
        
if __name__ == "__main__":
    find_pending()
