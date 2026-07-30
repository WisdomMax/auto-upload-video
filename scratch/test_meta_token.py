import requests, os
from dotenv import load_dotenv

load_dotenv(override=True)

token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
ig_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")

print("=== [META GRAPH API TOKEN VALIDATION] ===")
print("Token prefix:", token[:25] if token else None)
print("IG Business ID:", ig_id)

if not token or not ig_id:
    print("❌ Token or IG ID missing in .env!")
    exit(1)

# Test 1. Me Accounts / IG Business Account test
url = f"https://graph.facebook.com/v18.0/{ig_id}?fields=id,username,name,profile_picture_url&access_token={token}"
res = requests.get(url)
print("\n1. Instagram Business Account Info API Response:")
print("Status Code:", res.status_code)
print("Response Data:", res.json())

# Test 2. Recent Media Feed test
if res.status_code == 200:
    media_url = f"https://graph.facebook.com/v18.0/{ig_id}/media?fields=id,caption,permalink,timestamp,comments_count&limit=5&access_token={token}"
    m_res = requests.get(media_url)
    print("\n2. Instagram Media Feed API Response:")
    print("Status Code:", m_res.status_code)
    m_data = m_res.json()
    print("Media Count:", len(m_data.get('data', [])))
    for item in m_data.get('data', [])[:3]:
        print(f"  - ID: {item.get('id')}, Permalink: {item.get('permalink')}, Caption: {item.get('caption', '')[:40]}")
