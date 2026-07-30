import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

pending_ids = [77, 74, 73, 72]
items = database.get_items()

result = []
for item in items:
    if item.get("id") in pending_ids:
        result.append({
            "id": item.get("id"),
            "product_no": item.get("product_no"),
            "product_code": item.get("product_code"),
            "title": item.get("title"),
            "description": item.get("description"),
            "coupang_url": item.get("coupang_url"),
            "short_url": item.get("short_url"),
            "youtube_title": item.get("youtube_title"),
            "youtube_description": item.get("youtube_description")
        })

print(json.dumps(result, ensure_ascii=False, indent=2))
