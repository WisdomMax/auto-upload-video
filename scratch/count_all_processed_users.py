import os, glob, re

log_dir = "/Users/wisdom/.gemini/antigravity/brain/a0dd2e95-6511-4a02-994e-bb9b211d118e/.system_generated/tasks"
log_files = glob.glob(os.path.join(log_dir, "*.log"))

all_processed_users = set()
all_comments_found = 0
post_stats = {}

for log_file in log_files:
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Find user process lines
        matches = re.findall(r'@([a-zA-Z0-9._]+)\s*님', content)
        for m in matches:
            if m not in ['momdad_style', 'susankim0608', 'ilovehusky486']:
                all_processed_users.add(m)
                
        # Find comment count lines
        c_matches = re.findall(r'댓글\s*(\d+)개\n', content)
        for c in c_matches:
            all_comments_found += int(c)

    except Exception:
        pass

print("=== [인스타그램 전체 스캔 및 전송 통계 집계] ===")
print(f"📊 1. 총 감지된 댓글 수: 약 {all_comments_found}개")
print(f"✅ 2. 실제로 답글/DM이 완료된 순수 유저 수: 총 {len(all_processed_users)}명")

