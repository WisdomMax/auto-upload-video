#!/usr/bin/env python3
"""5개 샘플 상품을 DB에 삽입하는 스크립트"""
import sys
sys.exit("seed_products.py is disabled to prevent database overwrite.")
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database

products = [
    {
        "product_no": 1,
        "title": "60대 이상 어머니 여름 상하세트",
        "description": "편하고 시원한 느낌으로 집에서도, 잠깐 외출할 때도 부담 없이 입기 좋은 여름옷입니다.",
        "coupang_url": "",  # 나중에 입력
        "original_video_path": "",
        "youtube_title": "60대 이상 어머니 여름 상하세트, 편하고 시원하게 입기 좋아요 #시니어패션 #엄마옷",
        "youtube_description": "60대 이상 어머니 여름 상하세트 제품번호: 00001\n\n편하고 시원한 느낌으로 집에서도, 잠깐 외출할 때도 부담 없이 입기 좋은 여름옷입니다.",
        "youtube_tags": "60대이상,시니어패션,엄마옷,어머니옷,엄마여름옷,여름상하세트,면린넨세트,부모님패션,쿠팡추천템",
        "sns_caption": """60대 이상 어머니 여름 상하세트
제품번호: 00001

편하고 시원한 느낌으로 집에서도, 잠깐 외출할 때도 부담 없이 입기 좋은 여름옷입니다.

상품은 프로필 링크에서 확인해보세요.
가격과 재고는 변동될 수 있습니다.
쿠팡 파트너스 활동을 통해 일정액의 수수료를 제공받습니다.

#60대이상 #시니어패션 #엄마옷 #어머니옷 #엄마여름옷 #여름상하세트 #면린넨세트 #부모님패션 #쿠팡추천템""",
        "dm_template": "문의 주셔서 감사합니다.\n제품번호 00001 입니다.\n프로필 링크에서 확인해보세요.\nhttps://link.coupang.com/a/ehuVBtToxo",
        "comment_reply": "문의 주셔서 감사합니다.\n제품번호 00001 입니다.\n프로필 링크에서 확인해보세요.",
    },
    {
        "product_no": 2,
        "title": "60대 이상 어머니 여름 티셔츠",
        "description": "몸에 달라붙지 않고 팔과 배 부분이 부담 덜한 루즈핏 상의라 여름에 편하게 입기 좋은 엄마옷입니다.",
        "coupang_url": "",
        "original_video_path": "",
        "youtube_title": "60대 이상 어머니 여름 티셔츠, 달라붙지 않는 루즈핏 상의 #엄마여름옷 #시니어패션",
        "youtube_description": "60대 이상 어머니 여름 티셔츠 제품번호: 00002\n\n몸에 달라붙지 않고 팔과 배 부분이 부담 덜한 루즈핏 상의라 여름에 편하게 입기 좋은 엄마옷입니다.",
        "youtube_tags": "60대패션,시니어패션,엄마옷,어머니옷,여름티셔츠,루즈핏티셔츠,엄마여름옷,중년여성패션,부모님패션,쿠팡추천템",
        "sns_caption": """60대 이상 어머니 여름 티셔츠
제품번호: 00002

몸에 달라붙지 않고 팔과 배 부분이 부담 덜한 루즈핏 상의라 여름에 편하게 입기 좋은 엄마옷입니다.

상품은 프로필 링크에서 확인해보세요.
가격과 재고는 변동될 수 있습니다.
쿠팡 파트너스 활동을 통해 일정액의 수수료를 제공받습니다.

#60대패션 #시니어패션 #엄마옷 #어머니옷 #여름티셔츠 #루즈핏티셔츠 #엄마여름옷 #중년여성패션 #부모님패션 #쿠팡추천템""",
        "dm_template": "문의 주셔서 감사합니다.\n제품번호 00002 입니다.\n프로필 링크에서 확인해보세요.\nhttps://link.coupang.com/a/ehuVBtToxo",
        "comment_reply": "문의 주셔서 감사합니다.\n제품번호 00002 입니다.\n프로필 링크에서 확인해보세요.",
    },
    {
        "product_no": 3,
        "title": "60대 이상 어머니 여름 샌들",
        "description": "발끝이 화사해 보이고 집 앞 외출이나 장보기, 산책할 때 편하게 신기 좋은 여름 샌들입니다.",
        "coupang_url": "",
        "original_video_path": "",
        "youtube_title": "60대 이상 어머니 여름 샌들, 발끝이 화사해 보이네요 #엄마신발 #여름샌들",
        "youtube_description": "60대 이상 어머니 여름 샌들 제품번호: 00003\n\n발끝이 화사해 보이고 집 앞 외출이나 장보기, 산책할 때 편하게 신기 좋은 여름 샌들입니다.",
        "youtube_tags": "60대이상,시니어패션,엄마신발,어머니신발,여름샌들,여성샌들,빨간샌들,부모님패션,쿠팡추천템",
        "sns_caption": """60대 이상 어머니 여름 샌들
제품번호: 00003

발끝이 화사해 보이고 집 앞 외출이나 장보기, 산책할 때 편하게 신기 좋은 여름 샌들입니다.

상품은 프로필 링크에서 확인해보세요.
가격과 재고는 변동될 수 있습니다.
쿠팡 파트너스 활동을 통해 일정액의 수수료를 제공받습니다.

#60대이상 #시니어패션 #엄마신발 #어머니신발 #여름샌들 #여성샌들 #빨간샌들 #부모님패션 #쿠팡추천템""",
        "dm_template": "문의 주셔서 감사합니다.\n제품번호 00003 입니다.\n프로필 링크에서 확인해보세요.\nhttps://link.coupang.com/a/ehuVBtToxo",
        "comment_reply": "문의 주셔서 감사합니다.\n제품번호 00003 입니다.\n프로필 링크에서 확인해보세요.",
    },
    {
        "product_no": 4,
        "title": "60대 이상 어머니 여름 단화",
        "description": "발등은 시원해 보이고 앞코는 막혀 있어 단정한 느낌이라 여름 외출용으로 신기 좋은 엄마 신발입니다.",
        "coupang_url": "",
        "original_video_path": "",
        "youtube_title": "60대 이상 어머니 여름 단화, 발등은 시원하고 앞코는 단정하게 #엄마신발 #메쉬단화",
        "youtube_description": "60대 이상 어머니 여름 단화 제품번호: 00004\n\n발등은 시원해 보이고 앞코는 막혀 있어 단정한 느낌이라 여름 외출용으로 신기 좋은 엄마 신발입니다.",
        "youtube_tags": "60대이상,시니어패션,엄마신발,어머니신발,여름단화,메쉬단화,메리제인,여성단화,부모님패션,쿠팡추천템",
        "sns_caption": """60대 이상 어머니 여름 단화
제품번호: 00004

발등은 시원해 보이고 앞코는 막혀 있어 단정한 느낌이라 여름 외출용으로 신기 좋은 엄마 신발입니다.

상품은 프로필 링크에서 확인해보세요.
가격과 재고는 변동될 수 있습니다.
쿠팡 파트너스 활동을 통해 일정액의 수수료를 제공받습니다.

#60대이상 #시니어패션 #엄마신발 #어머니신발 #여름단화 #메쉬단화 #메리제인 #여성단화 #부모님패션 #쿠팡추천템""",
        "dm_template": "문의 주셔서 감사합니다.\n제품번호 00004 입니다.\n프로필 링크에서 확인해보세요.\nhttps://link.coupang.com/a/ehuVBtToxo",
        "comment_reply": "문의 주셔서 감사합니다.\n제품번호 00004 입니다.\n프로필 링크에서 확인해보세요.",
    },
    {
        "product_no": 5,
        "title": "60대 이상 어머니 여름 원피스",
        "description": "화사한 꽃무늬와 편한 핏으로 여름에 시원하고 부담 없이 입기 좋은 엄마 외출용 원피스입니다.",
        "coupang_url": "",
        "original_video_path": "",
        "youtube_title": "60대 이상 어머니 여름 원피스, 화사하고 편하게 입기 좋아요 #엄마옷 #여름원피스",
        "youtube_description": "60대 이상 어머니 여름 원피스 제품번호: 00005\n\n화사한 꽃무늬와 편한 핏으로 여름에 시원하고 부담 없이 입기 좋은 엄마 외출용 원피스입니다.",
        "youtube_tags": "60대이상,시니어패션,엄마옷,어머니원피스,여름원피스,꽃무늬원피스,엄마여름옷,부모님패션,쿠팡추천템",
        "sns_caption": """60대 이상 어머니 여름 원피스
제품번호: 00005

화사한 꽃무늬와 편한 핏으로 여름에 시원하고 부담 없이 입기 좋은 엄마 외출용 원피스입니다.

상품은 프로필 링크에서 확인해보세요.
가격과 재고는 변동될 수 있습니다.
쿠팡 파트너스 활동을 통해 일정액의 수수료를 제공받습니다.

#60대이상 #시니어패션 #엄마옷 #어머니원피스 #여름원피스 #꽃무늬원피스 #엄마여름옷 #부모님패션 #쿠팡추천템""",
        "dm_template": "문의 주셔서 감사합니다.\n제품번호 00005 입니다.\n프로필 링크에서 확인해보세요.\nhttps://link.coupang.com/a/ehuVBtToxo",
        "comment_reply": "문의 주셔서 감사합니다.\n제품번호 00005 입니다.\n프로필 링크에서 확인해보세요.",
    },
]

import sqlite3
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.sqlite")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 기존 테스트 데이터 확인
cursor.execute("SELECT COUNT(*) FROM items")
count = cursor.fetchone()[0]
print(f"기존 상품 수: {count}개")

inserted = 0
for p in products:
    cursor.execute("""
        INSERT INTO items (
            product_no, title, description, coupang_url, original_video_path,
            publish_status, youtube_title, youtube_description, youtube_tags,
            sns_caption, dm_template, comment_reply
        ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
    """, (
        p["product_no"], p["title"], p["description"],
        p["coupang_url"], p["original_video_path"],
        p["youtube_title"], p["youtube_description"], p["youtube_tags"],
        p["sns_caption"], p["dm_template"], p["comment_reply"]
    ))
    item_id = cursor.lastrowid
    print(f"  ✅ [{p['product_no']:05d}] {p['title']} → ID: {item_id}")
    inserted += 1

conn.commit()
conn.close()

print(f"\n총 {inserted}개 상품 추가 완료!")
print("쿠팡 링크는 대시보드에서 각 상품 편집 시 입력하세요.")
