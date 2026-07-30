import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

item_id = 47

youtube_title = "뱃살과 팔뚝살 싹 감춰주고 10년은 날씬해 보이는 중년 여름 와이드팬츠 상하세트 코디법 #중년여성패션 #여름코디 #체형커버"

youtube_description = """반갑습니다, 어머님 아버님! 엄마아빠 패션다이어리입니다. 🌸

나이가 들면서 늘어나는 뱃살과 팔뚝살 때문에 여름철 얇은 옷 입기가 참 망설여지시죠? 
몸에 딱 달라붙는 옷은 부담스럽고, 그렇다고 너무 헐렁하게만 입으면 자칫 촌스러워 보이기 십상입니다.

오늘은 이런 고민을 싹 해결해 줄 세련된 여름 캐주얼 와이드팬츠 상하세트 코디 노하우를 소개해 드립니다. 
어깨 라인을 자연스럽게 커버해 주는 반팔티와 하체의 군살을 마법처럼 감춰주는 와이드핏 팬츠의 조합으로, 입는 순간 10년은 젊고 슬림해 보이는 효과를 느끼실 수 있어요. 
통기성이 우수한 가벼운 소재로 제작되어 한여름에도 에어컨을 입은 듯 시원하고 편안하게 활동하실 수 있답니다. 
가벼운 외출이나 모임 어디에나 찰떡같이 어울리는 만능 세트 상품을 만나보세요!

영상 속 추천 아이템 상세 정보 및 구매 링크는 아래를 클릭해 주세요! 👇
구매 링크: https://link.coupang.com/a/eyhqblzXK8

(채널 프로필 홈에 연결된 링크를 클릭하시면 모든 제품의 구매 링크를 한눈에 편리하게 확인하실 수 있습니다)

* 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.

#중년여성패션 #여름코디 #체형커버 #와이드팬츠세트"""

youtube_tags = "시니어패션, 60대여성의류, 동안코디, 엄마옷추천, 중년여성패션, 와이드팬츠코디, 5060패션, 체형커버코디"

sns_caption = """나이 들수록 팔뚝살과 뱃살 때문에 여름 반팔 입기 신경 쓰이시죠? 😢

가볍고 시원하면서도 군살을 마법처럼 싹 감춰주는 중년 맞춤형 와이드팬츠 상하세트를 소개해 드려요! ✨
달라붙지 않는 쾌적한 소재와 세련된 루즈핏으로, 입는 순간 10년은 더 젊고 날씬해 보인답니다. 
마실 룩부터 모임 룩까지 옷 걱정 없이 편안하게 입어보세요! 💕

이 제품의 자세한 정보와 구매 링크를 받아보고 싶으신 어머님들은 댓글에 편하게 '엄마'라고 남겨주세요! 💌 확인하는 대로 DM으로 즉시 구매 링크를 전송해 드릴게요!

#시니어패션 #중년코디 #엄마옷추천 #동안패션 #5060패션 #체형커버코디 #여름상하세트"""

comment_reply = "유튜브 정책상 댓글에 직접 링크 클릭이 되지 않아 네이버 검색을 유도해 드려요! 🔍 네이버 검색창에 '엄마아빠 패션다이어리 WEIHAN 중년 여성 여름 빅사이즈 캐주얼 세트'를 검색하시면 상세 정보와 쿠팡 링크를 바로 확인하실 수 있습니다!"

dm_template = """안녕하세요, 엄마아빠 패션다이어리입니다! 😊
요청하신 [No.14 - WEIHAN 중년 여성 여름 빅사이즈 캐주얼 세트]의 상세 링크입니다.

👇 쿠팡 즉시구매 링크
https://link.coupang.com/a/eyhqblzXK8

오늘도 세련되고 편안한 하루 보내세요! 🌸"""

print(f"Updating database for item ID {item_id}...")
database.update_item_generated_contents(
    item_id=item_id,
    youtube_title=youtube_title,
    youtube_description=youtube_description.strip(),
    youtube_tags=youtube_tags,
    sns_caption=sns_caption.strip(),
    dm_template=dm_template.strip(),
    comment_reply=comment_reply
)
print("Database update completed.")
