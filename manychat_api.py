import os
import logging
import httpx

logger = logging.getLogger("manychat_api")

MANYCHAT_API_URL = "https://api.manychat.com"

def _get_headers():
    api_key = os.getenv("MANYCHAT_API_KEY")
    if not api_key:
        logger.error("MANYCHAT_API_KEY is not set in environment variables.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

async def set_subscriber_custom_field(subscriber_id: int, field_name: str, field_value: str) -> bool:
    url = f"{MANYCHAT_API_URL}/fb/subscriber/setCustomField"
    headers = _get_headers()
    payload = {
        "subscriber_id": subscriber_id,
        "field_name": field_name,
        "field_value": field_value
    }
    
    logger.info(f"Setting Manychat custom field '{field_name}' for subscriber {subscriber_id} to: {field_value}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            res_json = response.json()
            if response.status_code == 200 and res_json.get("status") == "success":
                logger.info(f"Successfully set custom field for subscriber {subscriber_id}")
                return True
            else:
                logger.error(f"Failed to set custom field: {res_json}")
                return False
    except Exception as e:
        logger.error(f"Error calling setCustomField API: {e}", exc_info=True)
        return False

async def trigger_flow(subscriber_id: int, flow_id: str) -> bool:
    url = f"{MANYCHAT_API_URL}/fb/sending/triggerFlow"
    headers = _get_headers()
    payload = {
        "subscriber_id": subscriber_id,
        "flow_ns": flow_id
    }
    
    logger.info(f"Triggering Manychat Flow {flow_id} for subscriber {subscriber_id}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            res_json = response.json()
            if response.status_code == 200 and res_json.get("status") == "success":
                logger.info(f"Successfully triggered flow {flow_id} for subscriber {subscriber_id}")
                return True
            else:
                logger.error(f"Failed to trigger flow: {res_json}")
                return False
    except Exception as e:
        logger.error(f"Error calling triggerFlow API: {e}", exc_info=True)
        return False
