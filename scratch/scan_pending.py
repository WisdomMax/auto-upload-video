import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import json

items = database.get_items()
pending_items = []
default_prefixes = ["60대 이후 옷 잘 입는", "60대 어머님들", "60대 이후 입으면", "60대 70대 어머님들"]

for item in items:
    title = item.get("title") or ""
    yt_title = item.get("youtube_title") or ""
    yt_desc = item.get("youtube_description") or ""
    
    is_empty = not yt_title or not yt_desc
    is_default_title = any(yt_title.startswith(p) for p in default_prefixes) or "엄마아빠 패션다이어리" in yt_title or "추천 상품" in yt_title
    is_default_desc = "에이전트가 영상 분석을 통해" in yt_desc or "에이전트가 추천한" in yt_desc or not yt_desc
    
    if is_empty or is_default_title or is_default_desc:
        pending_items.append({
            "id": item.get("id"),
            "product_no": item.get("product_no"),
            "product_code": item.get("product_code"),
            "title": item.get("title"),
            "description": item.get("description"),
            "coupang_url": item.get("coupang_url"),
            "short_url": item.get("short_url"),
            "youtube_title": yt_title,
            "youtube_description": yt_desc
        })

print(json.dumps(pending_items, ensure_ascii=False, indent=2))
