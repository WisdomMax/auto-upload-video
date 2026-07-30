import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

def update_items():
    # ID: 84 - 우일 여성 인견 플리츠 반팔 원피스 (T00026)
    id_84_youtube_title = "나이 들수록 축 처지는 어깨와 뱃살 싹 감추는 인견 플리츠 원피스 코디법 #중년코디 #시니어패션 #여름원피스"
    id_84_youtube_desc = """안녕하세요, 어머님 아버님! 엄마아빠 패션다이어리입니다. 🌸

무더운 여름철, 어떤 옷을 입어도 땀이 차고 몸에 달라붙어 외출하기 망설여지셨죠? 특히 나이가 들면서 늘어나는 뱃살과 군살 때문에 얇은 옷 입기가 조심스러우셨을 텐데요.

오늘 소개해 드리는 원피스는 몸에 달라붙지 않아 마치 에어컨을 입은 듯 시원한 인견 소재의 플리츠 원피스입니다. 플리츠 특유의 자연스러운 세로 주름이 몸매 라인을 슬림하게 잡아주고, 축 처진 군살을 감쪽같이 커버해 준답니다. 가볍게 툭 걸치기만 해도 세련되고 귀티 나는 스타일을 연출할 수 있어요. 

더운 여름에도 시원하고 품격 있게 스타일을 유지해 보세요!

착용하신 상품 정보와 상세 내용이 궁금하시다면 아래 링크를 참고해 주세요.👇
제품 정보 확인하기: https://link.coupang.com/re/AFFSDP?lptag=AF1047126&pageKey=8670059021&itemId=25168052327&vendorItemId=75111610003&traceid=V0-153-725d1099796fb1f7&clickBeacon=e92d8d50-6b48-11f1-abae-06aaf7b078c7%7E3&requestid=20260619040711812142532391&token=31850C%7CMIXED

* 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."""
    
    id_84_youtube_tags = "중년여성의류, 시니어패션, 60대원피스, 인견원피스, 주름원피스, 체형커버코디, 여름원피스추천, 5060패션"
    id_84_sns_caption = """나이 들수록 팔뚝살과 뱃살 때문에 얇은 반팔 원피스 하나 입기도 신경 쓰이시죠? 🥲

그렇다고 매번 펑퍼짐한 옷만 입을 수도 없고 고민이 많으셨을 어머님들을 위해 준비했어요! 
몸에 부드럽게 흐르면서도 살에 달라붙지 않아 에어컨을 입은 듯 시원한 인견 플리츠 원피스입니다. 세로 주름 공정 덕분에 날씬해 보이면서 격식 있는 모임이나 외출복으로도 정말 훌륭하답니다. ✨

이 제품의 자세한 정보와 구매 링크를 받아보고 싶으신 어머님들은 댓글에 편하게 '엄마'라고 남겨주세요! 💌 확인하는 대로 DM으로 즉시 구매 링크를 전송해 드릴게요!

#시니어패션 #중년코디 #엄마옷추천 #동안패션 #5060패션 #체형커버코디 #인견원피스"""

    id_84_dm_template = """어머님, 안녕하세요! 요청하신 '우일 여성 인견 플리츠 반팔 원피스' 구매 링크입니다. 🌸 
더운 여름에도 세련되게 체형 커버를 해주는 시원한 원피스 정보예요.
👉 링크 클릭: https://link.coupang.com/re/AFFSDP?lptag=AF1047126&pageKey=8670059021&itemId=25168052327&vendorItemId=75111610003&traceid=V0-153-725d1099796fb1f7&clickBeacon=e92d8d50-6b48-11f1-abae-06aaf7b078c7%7E3&requestid=20260619040711812142532391&token=31850C%7CMIXED"""

    id_84_comment_reply = "어머님들! 이 시원하고 고급스러운 인견 플리츠 원피스의 정보가 궁금하시다면 네이버 검색창에 '엄마아빠 패션다이어리 우일 여성 인견 플리츠 반팔 원피스'를 검색해 보세요! 상세한 내용과 구매 링크를 바로 만나보실 수 있습니다."

    print("ID 84 업데이트 진행 중...")
    database.update_item_generated_contents(
        item_id=84,
        youtube_title=id_84_youtube_title,
        youtube_description=id_84_youtube_desc,
        youtube_tags=id_84_youtube_tags,
        sns_caption=id_84_sns_caption,
        dm_template=id_84_dm_template,
        comment_reply=id_84_comment_reply
    )
    print("ID 84 업데이트 완료.")

    # ID: 85 - 여름 에스닉 면 마 원피스 (T00027)
    id_85_youtube_title = "동창 모임에서 10년은 젊고 귀티 나 보이는 린넨 에스닉 원피스 코디의 비밀 #중년코디 #60대패션 #린넨원피스"
    id_85_youtube_desc = """안녕하세요, 어머님 아버님! 엄마아빠 패션다이어리입니다. 🌸

여름 나들이나 모임이 있을 때 어떤 옷을 입어야 세련되면서도 편안할까 항상 고민 많으시죠? 너무 화려한 건 부담스럽고, 그렇다고 밋밋한 옷은 기품이 살지 않으니까요.

오늘 보여드리는 아이템은 천연 면 마(린넨) 소재의 내추럴함에 고급스러운 에스닉 자수 포인트가 어우러진 린넨 원피스입니다. 넉넉하고 편안한 루즈핏이지만, 허리 조임 끈이 있어 날씬하게 라인을 잡을 수 있답니다. 고풍스러운 개량 한복 느낌의 우아한 실루엣 덕분에 일상복뿐만 아니라 주말 나들이룩이나 특별한 모임에서도 돋보이실 수 있습니다.

소재가 주는 쾌적함과 품격 있는 디자인으로 올여름을 더욱 특별하게 보내세요!

착용하신 상품 정보와 상세 내용이 궁금하시다면 아래 링크를 참고해 주세요.👇
제품 정보 확인하기: https://link.coupang.com/re/AFFSDP?lptag=AF1047126&pageKey=8605028571&itemId=24953934046&vendorItemId=92055154038&traceid=V0-153-2d2b7b8642b415dc&clickBeacon=c938ac40-7c92-11f1-94cb-38d0ad626437%7E3&requestid=20260711040850749030030514&token=31850C%7CMIXED

* 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."""

    id_85_youtube_tags = "중년여성의류, 시니어패션, 60대원피스, 린넨원피스, 에스닉원피스, 모임룩추천, 개량한복, 5060패션"
    id_85_sns_caption = """단체사진이나 동창 모임에서 유독 화사하고 우아해 보이는 어머님들의 코디 비밀을 알고 싶으신가요? ✨

천연 린넨과 면 소재가 섞여 통기성이 매우 훌륭하고, 한국적인 우아함이 돋보이는 에스닉 자수가 가미된 린넨 원피스입니다. 루즈핏이라 몸매 콤플렉스는 감쪽같이 가려주면서, 허리 라인을 원하는 만큼 조절하여 날씬해 보이는 실루엣을 만들 수 있어요. 올여름 품격 있는 나들이룩으로 강력 추천해 드립니다! 🥰

이 제품의 자세한 정보와 구매 링크를 받아보고 싶으신 어머님들은 댓글에 편하게 '엄마'라고 남겨주세요! 💌 확인하는 대로 DM으로 즉시 구매 링크를 전송해 드릴게요!

#시니어패션 #중년코디 #엄마옷추천 #동안패션 #5060패션 #체형커버코디 #린넨원피스 #모임룩"""

    id_85_dm_template = """어머님, 안녕하세요! 요청하신 '여름 에스닉 면 마 린넨 원피스' 구매 링크입니다. 🌸 
모임과 나들이에서 세련되게 빛날 수 있는 우아한 원피스 정보예요.
👉 링크 클릭: https://link.coupang.com/re/AFFSDP?lptag=AF1047126&pageKey=8605028571&itemId=24953934046&vendorItemId=92055154038&traceid=V0-153-2d2b7b8642b415dc&clickBeacon=c938ac40-7c92-11f1-94cb-38d0ad626437%7E3&requestid=20260711040850749030030514&token=31850C%7CMIXED"""

    id_85_comment_reply = "어머님들! 이 고급스러운 린넨 에스닉 원피스 정보가 궁금하시다면 네이버 검색창에 '엄마아빠 패션다이어리 여름 에스닉 면 마 원피스'를 검색해 보세요! 상세 페이지에서 자세한 정보와 구매처를 바로 확인하실 수 있습니다."

    print("ID 85 업데이트 진행 중...")
    database.update_item_generated_contents(
        item_id=85,
        youtube_title=id_85_youtube_title,
        youtube_description=id_85_youtube_desc,
        youtube_tags=id_85_youtube_tags,
        sns_caption=id_85_sns_caption,
        dm_template=id_85_dm_template,
        comment_reply=id_85_comment_reply
    )
    print("ID 85 업데이트 완료.")

if __name__ == "__main__":
    update_items()
