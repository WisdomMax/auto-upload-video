import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

for target_id in [77, 79]:
    item = database.get_item(target_id)
    if item:
        print("="*60)
        print(f"ID: {item.get('id')} | Code: {item.get('product_code')} | No: {item.get('product_no')}")
        print(f"원본제목: {item.get('title')}")
        print(f"유튜브제목: {item.get('youtube_title')}")
        print(f"유튜브설명: {item.get('youtube_description')}")
        print(f"SNS 캡션: {item.get('sns_caption')}")
        print(f"우회 댓글: {item.get('comment_reply')}")
    else:
        print(f"ID {target_id} 상품을 찾을 수 없습니다.")
