import sys
import os

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import database

def dump_all():
    items = database.get_items()
    for item in items:
        print(f"ID: {item.get('id')} | Code: {item.get('product_code')} | Title: {item.get('title')} | YT_Title: {item.get('youtube_title')} | YT_Desc_Len: {len(item.get('youtube_description') or '')}")

if __name__ == "__main__":
    dump_all()
