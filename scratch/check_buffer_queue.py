import os
import sys
import requests
import json
import logging

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("check_buffer")

def main():
    load_dotenv()
    access_token = os.getenv("BUFFER_ACCESS_TOKEN") or database.get_setting("BUFFER_ACCESS_TOKEN")
    if not access_token:
        logger.error("Buffer Access Token is missing!")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 1. 프로필(연동 채널) 목록 조회
    query = """
    query {
      account {
        organizations {
          channels {
            id
            name
            service
          }
        }
      }
    }
    """
    try:
        res = requests.post("https://api.buffer.com", json={"query": query}, headers=headers, timeout=15)
        if res.status_code != 200:
            logger.error(f"Failed to fetch profiles: {res.status_code} - {res.text}")
            return
            
        orgs = res.json().get("data", {}).get("account", {}).get("organizations", [])
        profiles = []
        for org in orgs:
            for channel in org.get("channels", []):
                profiles.append(channel)
                
        logger.info(f"Fetched {len(profiles)} social channels from Buffer:")
        for p in profiles:
            logger.info(f"- [{p['service']}] {p['name']} (ID: {p['id']})")
            
    except Exception as e:
        logger.error(f"Error fetching profiles: {e}")
        return

    # 2. 각 채널의 보류 중인 포스트(pending) 및 전송 완료/실패(sent) 포스트 조회 (REST API 사용)
    for p in profiles:
        profile_id = p["id"]
        service = p["service"]
        
        # Pending updates
        pending_url = f"https://api.bufferapp.com/1/profiles/{profile_id}/updates/pending.json"
        try:
            res_pending = requests.get(pending_url, headers=headers, timeout=10)
            if res_pending.status_code == 200:
                pending_data = res_pending.json()
                updates = pending_data.get("updates", [])
                logger.info(f"[{service}] Pending posts count: {len(updates)}")
                for u in updates[:3]:
                    logger.info(f"  * ID: {u.get('id')}, Text: {u.get('text')[:30]}..., Due: {u.get('due_at')}, Status: {u.get('status')}")
            else:
                logger.error(f"[{service}] Failed to fetch pending posts: {res_pending.status_code} - {res_pending.text}")
        except Exception as e:
            logger.error(f"[{service}] Error fetching pending posts: {e}")

        # Sent/Failed updates (최근 포스트)
        sent_url = f"https://api.bufferapp.com/1/profiles/{profile_id}/updates/sent.json"
        try:
            res_sent = requests.get(sent_url, headers=headers, timeout=10)
            if res_sent.status_code == 200:
                sent_data = res_sent.json()
                updates = sent_data.get("updates", [])
                logger.info(f"[{service}] Sent/Failed posts count (recent 5): {len(updates[:5])}")
                for u in updates[:5]:
                    # 실패 에러로그 확인
                    error_msg = u.get("error_message") or u.get("error") or "None"
                    logger.info(f"  * ID: {u.get('id')}, Text: {u.get('text')[:30]}..., Status: {u.get('status')}, Error: {error_msg}")
            else:
                logger.error(f"[{service}] Failed to fetch sent posts: {res_sent.status_code} - {res_sent.text}")
        except Exception as e:
            logger.error(f"[{service}] Error fetching sent posts: {e}")

if __name__ == "__main__":
    main()
