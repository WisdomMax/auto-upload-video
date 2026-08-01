import os, glob, re, json

log_dir = "/Users/wisdom/.gemini/antigravity/brain/a0dd2e95-6511-4a02-994e-bb9b211d118e/.system_generated/tasks"
log_files = glob.glob(os.path.join(log_dir, "*.log"))

failed_dm_records = []

for log_file in log_files:
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        current_post = ""
        current_user = ""
        current_product = "29"

        for line in lines:
            post_m = re.search(r'릴스\s*(\d+)번|reel/([a-zA-Z0-9_-]+)', line)
            if post_m:
                if post_m.group(1): current_product = post_m.group(1)

            user_m = re.search(r'@([a-zA-Z0-9._]+)', line)
            if user_m and 'momdad_style' not in user_m.group(1):
                current_user = user_m.group(1)

            if "DM 전송 예외" in line or "DM 예외" in line or "Timeout" in line:
                if current_user and current_user not in ['susankim0608', 'ilsunsarahchoi', 'oweolgwang', 'sughyi6624', 'eerara520']:
                    SYSTEM_BLACKLIST = {'reels', 'directinbox', 'explore', 'accountsedit', 'legalprivacy', 'legalterms', 'explorelocations', 'popular', 'weblite', 'accountsmeta_verified'}
                    if current_user not in SYSTEM_BLACKLIST and not current_user.startswith('accounts'):
                        item = {"user": current_user, "product_no": current_product}
                        if not any(r["user"] == current_user for r in failed_dm_records):
                            failed_dm_records.append(item)
    except Exception:
        pass

print(f"=== [과거 DM 누락 유저 전수 정밀 감지 결과] ===")
print(f"📌 총 DM 전송 예외 감지 유저: {len(failed_dm_records)}명")
for idx, r in enumerate(failed_dm_records, start=1):
    print(f"  [{idx}] @{r['user']} (상품 {r['product_no']}번)")

with open("scratch/failed_dm_records.json", "w", encoding="utf-8") as out:
    json.dump(failed_dm_records, out, ensure_ascii=False, indent=2)

