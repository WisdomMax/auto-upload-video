import os, glob, re, json

log_dir = "/Users/wisdom/.gemini/antigravity/brain/a0dd2e95-6511-4a02-994e-bb9b211d118e/.system_generated/tasks"
log_files = glob.glob(os.path.join(log_dir, "*.log"))

failed_dm_list = []

for log_file in log_files:
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        current_post = ""
        current_user = ""
        current_product = ""
        
        for idx, line in enumerate(lines):
            post_m = re.search(r'스캔 접속:\s*(https://www\.instagram\.com/momdad_style/reel/[^/\s]+/)', line)
            if post_m:
                current_post = post_m.group(1)
                
            user_m = re.search(r'소급 처리 중\s*\(상품번호:\s*(\d+)\)\.\.\.\s*@([a-zA-Z0-9._]+)', line)
            if not user_m:
                user_m = re.search(r'@([a-zA-Z0-9._]+)\s*님 소급 처리 중\s*\(상품번호:\s*(\d+)\)', line)
                if user_m:
                    current_user = user_m.group(1)
                    current_product = user_m.group(2)
            else:
                current_product = user_m.group(1)
                current_user = user_m.group(2)

            if "DM 발송 예외" in line or "Timeout 5000ms exceeded" in line:
                if current_user and current_post:
                    item = {
                        "user": current_user,
                        "post": current_post,
                        "product_no": current_product or "1"
                    }
                    if not any(f["user"] == current_user and f["post"] == current_post for f in failed_dm_list):
                        failed_dm_list.append(item)
    except Exception as e:
        pass

print(f"=== [DM 실패/누락 대상자 자동 감지 추출 결과] ===")
print(f"📌 총 추출된 DM 누락 대상자: {len(failed_dm_list)}명")
for idx, f in enumerate(failed_dm_list, start=1):
    print(f"  [{idx}] @{f['user']} (상품No.{f['product_no']} / 게시물: {f['post']})")

# Save to scratch/failed_dm_users.json
with open("scratch/failed_dm_users.json", "w", encoding="utf-8") as out:
    json.dump(failed_dm_list, out, ensure_ascii=False, indent=2)

