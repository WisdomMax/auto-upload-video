import sys
import os

# 현재 디렉토리를 sys.path에 추가하여 database.py를 로드할 수 있도록 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

def scan_pending_items():
    items = database.get_items()
    pending_items = []
    default_prefixes = ["60대 이후 옷 잘 입는", "60대 어머님들", "60대 이후 입으면", "60대 70대 어머님들"]
    
    print(f"전체 상품 개수: {len(items)}")
    
    for item in items:
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
            pending_items.append(item)
            print(f"[-] 미완료 상품 감지: ID={item_id}, 코드={item.get('product_code')}, 제목={title}")
            print(f"    현재 유튜브 제목: {yt_title}")
            print(f"    현재 유튜브 설명: {yt_desc[:50]}...")
            print(f"    조건 판단: is_empty={is_empty}, is_default_title={is_default_title}, is_default_desc={is_default_desc}")
            
    print(f"미완료 상품 개수: {len(pending_items)}")

if __name__ == "__main__":
    scan_pending_items()
