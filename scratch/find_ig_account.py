import requests, os
from dotenv import load_dotenv

load_dotenv(override=True)
token = os.getenv("INSTAGRAM_ACCESS_TOKEN")

print("=== [FACEBOOK GRAPH API ACCOUNT & PAGE FINDER] ===")

# 1. Check me
r1 = requests.get(f"https://graph.facebook.com/v18.0/me?fields=id,name,accounts&access_token={token}")
print("me fields:", r1.json())

# 2. Check permissions
r2 = requests.get(f"https://graph.facebook.com/v18.0/me/permissions?access_token={token}")
print("permissions:", r2.json())

# 3. Check pages endpoint
r3 = requests.get(f"https://graph.facebook.com/v18.0/122180025896933242/accounts?access_token={token}")
print("user accounts:", r3.json())

# 4. Check debug_token details
r4 = requests.get(f"https://graph.facebook.com/v18.0/debug_token?input_token={token}&access_token={token}")
print("debug_token:", r4.json())
