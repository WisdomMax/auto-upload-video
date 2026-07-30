import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

items = database.get_items()
print(f"Total items: {len(items)}")
for item in items[:10]: # 최근 10개만 출력
    print(f"ID: {item['id']} | Code: {item.get('product_code')} | Title: {item['title']}")
    print(f"  YT Title: {item.get('youtube_title')}")
    print(f"  YT Desc: {item.get('youtube_description')[:50] if item.get('youtube_description') else None}")
    print("-" * 50)
