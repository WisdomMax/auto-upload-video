import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

items = database.get_items()
print(f"Total items in DB: {len(items)}")
for item in items:
    yt_title = item.get("youtube_title") or ""
    yt_desc = item.get("youtube_description") or ""
    print(f"ID: {item.get('id')} | Code: {item.get('product_code')} | Title: {item.get('title')[:30]}...")
    print(f"  YT Title: {yt_title}")
    print(f"  YT Desc (first 50 chars): {yt_desc[:50]}")
    print("-" * 50)
