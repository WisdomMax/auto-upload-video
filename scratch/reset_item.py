import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

item_id = 47
item = database.get_item(item_id)
if item:
    print(f"Resetting item ID {item_id} ({item['title']}) to default values...")
    database.update_item_generated_contents(
        item_id=item_id,
        youtube_title="60대 어머님들 추천 상품 - WEIHAN 중년 여성 여름 빅사이즈 캐주얼 세트",
        youtube_description="에이전트가 영상 분석을 통해 추천하는 고품질 신상품 정보입니다.",
        youtube_tags="",
        sns_caption="",
        dm_template="",
        comment_reply=""
    )
    print("Reset completed.")
else:
    print("Item not found.")
