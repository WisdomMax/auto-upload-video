import os
import json
import logging
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger("gpt_agent")


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        import database
        api_key = database.get_setting("OPENAI_API_KEY")
        
    if not api_key:
        logger.error("OPENAI_API_KEY is not set.")
        return None
    return AsyncOpenAI(api_key=api_key)

async def generate_reply_and_dm_content(user_comment: str, product_title: str, product_description: str, coupang_link: str, catalog_link: str) -> dict:
    """
    OpenAI gpt-4o-mini를 사용하여 사용자 댓글에 대해 짧은 대댓글과 
    쿠팡 직접 구매 링크 + 전체 카탈로그 쇼핑몰 메인 주소(다른 옷들 모아보기)가 모두 포함된 DM 내용을 생성합니다.
    """
    client = _get_openai_client()
    if not client:
        # OpenAI API Key가 없을 때의 fallback 텍스트 반환
        logger.warning("OpenAI API key missing. Using fallback response templates.")
        fallback_reply = "안녕하세요 어머님! 문의주신 제품 정보와 구매 링크를 DM(메시지)으로 바로 보내드렸어요! 💕"
        fallback_dm = (
            f"안녕하세요 어머님! 🌸 영상 속에서 보신 '{product_title}' 상세 정보입니다.\n\n"
            f"✨ {product_description}\n\n"
            f"🛒 편하신 방법으로 구경해 보세요:\n"
            f"1️⃣ 쿠팡에서 이 옷 바로 구매하기:\n{coupang_link}\n\n"
            f"2️⃣ 카탈로그 쇼핑몰에서 다른 예쁜 옷들도 함께 구경하기:\n{catalog_link}\n\n"
            f"궁금한 점이 있으시면 언제든 편하게 말씀해 주세요. 감사합니다!"
        )
        return {"reply": fallback_reply, "dm": fallback_dm}

    system_prompt = (
        "너는 50대~70대 시니어 여성을 주 타겟으로 하는 세련된 코디 채널 '엄마아빠 패션다이어리'의 다정하고 따뜻한 AI 점장이야.\n"
        "고객(시니어 어머님들)이 릴스 영상에 단 댓글을 보고, 그에 맞게 다정다감하고 상냥한 경어체(~해요, ~랍니다, 💕 등)로\n"
        "1. 인스타그램 답글(대댓글) 텍스트\n"
        "2. 인스타그램 DM으로 전송할 상세 안내 텍스트\n"
        "를 작성해줘. 반드시 JSON 형식으로 출력해야 하며, 키값은 'reply', 'dm'이어야 해.\n\n"
        "## 작성 수칙:\n"
        "- **답글(reply)**: 무조건 1줄 내외로 아주 심플하게 작성해야 해. 내용은 반드시 'DM(메시지)을 전송했다'는 사실을 전달해야 함.\n"
        "  ⚠️ [중요] 인스타그램 봇 탐지 필터를 우회하기 위해, 매번 완전히 똑같은 답장을 달지 말고, 어투나 문장 구조, 이모티콘을 매번 조금씩 무작위로 다르게 변형해줘.\n"
        "  (예시: 'DM 보내드렸습니다! 💕', '어머님, 메시지함으로 링크 보내드렸어요! 🌸', '방금 DM 발송 완료했습니다. 확인해 보세요! 😊' 등)\n\n"
        "- **DM**: 스팸 광고 느낌이 나지 않도록 매우 정중하고 정겨운 말투로 상품 특징을 설명해줘.\n"
        "  특히 본문 하단에 제공된 아래 **두 가지 링크**를 모두 이쁘게 정렬해서 필수 포함해야 해:\n"
        "  1) 해당 개별 상품을 즉시 구매할 수 있는 쿠팡 직접 구매 링크\n"
        "  2) 다른 모든 옷들과 코디 상품들을 모아서 구경할 수 있는 전체 카탈로그 쇼핑몰 메인 주소\n"
        "- 어머님들의 눈높이에 맞춰 복잡하고 트렌디한 신조어는 배제하고 편안한 단어를 사용해줘."
    )

    user_prompt = (
        f"고객 댓글: \"{user_comment}\"\n"
        f"상품명: {product_title}\n"
        f"상품 설명: {product_description}\n"
        f"1) 쿠팡 직접 구매 링크: {coupang_link}\n"
        f"2) 전체 카탈로그 메인 주소 (다른 상품 모아보기): {catalog_link}"
    )

    try:
        logger.info("Calling OpenAI GPT-4o-mini API...")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.75,
            timeout=15.0
        )
        
        raw_content = response.choices[0].message.content
        logger.info(f"GPT Response: {raw_content}")
        
        result = json.loads(raw_content)
        if "reply" in result and "dm" in result:
            return result
        else:
            raise KeyError("JSON missing 'reply' or 'dm' keys.")
            
    except Exception as e:
        logger.error(f"Error generating content via OpenAI: {e}", exc_info=True)
        # 에러 발생 시의 fallback
        fallback_reply = f"안녕하세요 어머님! 문의주신 제품 정보와 구매 링크를 DM으로 살포시 보내드렸어요! 확인 부탁드립니다. 💕"
        fallback_dm = (
            f"안녕하세요 어머님! 🌸 영상 속에서 보신 '{product_title}' 상세 정보입니다.\n\n"
            f"✨ {product_description}\n\n"
            f"🛒 상품 상세 보기 및 구매:\n"
            f"1️⃣ 쿠팡에서 이 상품 바로 구매:\n{coupang_link}\n\n"
            f"2️⃣ 카탈로그에서 다른 다양한 상품들도 한눈에 구경하기:\n{catalog_link}\n\n"
            f"오늘도 기분 좋은 하루 보내세요! 🍀"
        )
        return {"reply": fallback_reply, "dm": fallback_dm}

async def generate_chat_reply_and_link(user_message: str, product_no: str = "1") -> str:
    """
    고객이 DM으로 보낸 질문/대화에 대해 세세하고 긴 설명 없이 
    2~3줄 이내로 다정다감하게 간단히 대화를 주고받고 직행 상품 링크를 전달합니다.
    """
    client = _get_openai_client()
    product_link = f"https://6070.piella.shop/p/{product_no}" if product_no else "https://6070.piella.shop"
    
    if not client:
        return (
            f"어머님 안녕하세요! 💕 문의해 주셔서 감사해요!\n"
            f"요청하신 상품 구매 링크 바로 보내드리니 편리하게 구경해 보세요! ✨\n\n"
            f"👇 상품 바로가기 링크:\n{product_link}"
        )

    system_prompt = (
        "너는 50대~70대 어머님들과 친근하게 대화하는 '엄마아빠 패션다이어리'의 다정한 AI 친절 점장이야.\n"
        "고객(어머님)이 DM으로 보낸 질문이나 대화 메시지에 대해 답변할 때 아래 수칙을 반드시 준수해줘:\n\n"
        "## 핵심 작성 수칙:\n"
        "1. **길고 복잡하며 세세한 상품 설명 금지**: 너무 긴 설명이나 지루한 텍스트는 어머님들이 읽기 힘들어하시니 절대 금지야.\n"
        "2. **2~3줄 이내 짤막하고 다정한 대화**: '어머님 안녕하세요! 💕 ~해 드릴게요!'처럼 따뜻하고 짤막하게 반응해줘.\n"
        "3. **링크 필수 안내**: 답변 마지막에 아래 제공된 직행 구매 링크를 예쁘게 첨부해줘.\n"
        f"   링크: {product_link}\n"
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"고객 DM 메시지: \"{user_message}\""}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error in generate_chat_reply_and_link: {e}")
        return (
            f"어머님 안녕하세요! 💕 문의해 주셔서 감사해요!\n"
            f"요청하신 상품 구매 링크 바로 전달해 드려요! 편하게 둘러보세요! ✨\n\n"
            f"👇 상품 바로가기 링크:\n{product_link}"
        )

