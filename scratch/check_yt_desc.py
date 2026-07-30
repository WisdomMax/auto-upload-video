import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

items = database.get_items()
# ID 79, 77, 74 등의 youtube_description을 상세하게 출력해봅니다.
for item in items:
    if item.get("id") in [79, 77, 74, 47]:
        print(f"ID: {item.get('id')} | Title: {item.get('title')}")
        print("YT Title:", item.get("youtube_title"))
        print("YT Desc:")
        print(item.get("youtube_description"))
        print("=" * 60)
