import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import json

items = database.get_items()
summary = []
for item in items:
    summary.append({
        "id": item.get("id"),
        "product_no": item.get("product_no"),
        "product_code": item.get("product_code"),
        "title": item.get("title"),
        "youtube_title": item.get("youtube_title"),
        "youtube_description": item.get("youtube_description")[:50] if item.get("youtube_description") else None,
        "publish_status": item.get("publish_status")
    })

print(json.dumps(summary, ensure_ascii=False, indent=2))
