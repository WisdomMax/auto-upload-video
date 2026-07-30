import os, requests
from dotenv import load_dotenv

load_dotenv()

token_eaa = os.getenv('INSTAGRAM_ACCESS_TOKEN_EAA', '')
token_igaap = os.getenv('INSTAGRAM_ACCESS_TOKEN_IGAAP', '')

def test_token(name, token, is_igaap=False):
    if not token or '여기에' in token:
        print(f"⚠️ [{name}] 토큰이 설정되지 않았습니다.")
        return False
    
    url = f"https://graph.instagram.com/me?fields=id,username&access_token={token}" if is_igaap else f"https://graph.facebook.com/v19.0/me?access_token={token}"
    res = requests.get(url)
    data = res.json()
    
    if res.status_code == 200:
        info = data.get('username') or data.get('name') or data.get('id')
        print(f"✅ [{name}] 토큰 100% 정상 작동 중! (계정/ID: {info})")
        return True
    else:
        err = data.get('error', {}).get('message', 'Unknown Error')
        print(f"❌ [{name}] 토큰 검증 실패: {err}")
        return False

print("=== [인스타그램 이중 토큰 (EAA & IGAAP) 실시간 상태 검증] ===")
valid_eaa = test_token("EAA (메인 - 페이스북/웹훅용)", token_eaa, is_igaap=False)
valid_igaap = test_token("IGAAP (백업 - 인스타그램 유저용)", token_igaap, is_igaap=True)


if not valid_eaa and not valid_igaap:
    print("\n💡 두 토큰 모두 만료 상태입니다. 새 토큰을 .env에 붙여넣어 주세요.")
