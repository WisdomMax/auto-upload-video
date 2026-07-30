import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

items = database.get_items()
print(f"Total items in DB: {len(items)}")
for item in items[:5]:  # 상위 5개만 간단히 출력
    print(f"ID: {item.get('id')}, Code: {item.get('product_code')}, Title: {item.get('title')}, YT Title: {item.get('youtube_title')}")
