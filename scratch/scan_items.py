import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

items = database.get_items()
print(f"전체 상품 개수: {len(items)}")

pending_items = []
default_prefixes = ["60대 이후 옷 잘 입는", "60대 어머님들", "60대 이후 입으면", "60대 70대 어머님들"]

for item in items:
    item_id = item.get("id")
    product_no = item.get("product_no")
    product_code = item.get("product_code")
    title = item.get("title") or ""
    desc = item.get("description") or ""
    yt_title = item.get("youtube_title") or ""
    yt_desc = item.get("youtube_description") or ""
    
    is_empty = not yt_title or not yt_desc
    is_default_title = any(yt_title.startswith(p) for p in default_prefixes) or "엄마아빠 패션다이어리" in yt_title or "추천 상품" in yt_title
    is_default_desc = "에이전트가 영상 분석을 통해" in yt_desc or "에이전트가 추천한" in yt_desc or not yt_desc
    
    if is_empty or is_default_title or is_default_desc:
        pending_items.append(item)
        print(f"[미완료] ID: {item_id} | Code: {product_code} | No: {product_no} | 원본제목: {title}")
        print(f"        YT Title: {yt_title}")
        print(f"        YT Desc: {yt_desc[:50]}...")
    else:
        print(f"[완료] ID: {item_id} | Code: {product_code} | No: {product_no} | 원본제목: {title}")

print(f"\n미완료 상품 개수: {len(pending_items)}")
