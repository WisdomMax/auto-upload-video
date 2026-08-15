import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio, database, time, traceback, re, random
from datetime import datetime
from playwright.async_api import async_playwright

MAX_DAILY_REPLY = 80
daily_reply_count = 0
last_reset_date = datetime.now().strftime("%Y-%m-%d")

QUIET_START_HOUR = 21  # 밤 9시 (21:00)
QUIET_END_HOUR = 7    # 오전 7시 (07:00)

def is_quiet_hours() -> bool:
    now_hour = datetime.now().hour
    return now_hour >= QUIET_START_HOUR or now_hour < QUIET_END_HOUR

async def run_tiktok_daemon_check(ignore_quiet: bool = False):
    if not ignore_quiet and is_quiet_hours():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🌙 [틱톡 야간 휴식 모드 (21:00 ~ 07:00)] 현재 시각 {now_str}. 야간 시간에는 댓글/DM 발송을 100% 중단하고 휴식합니다.", flush=True)
        return

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🔍 [실시간 틱톡 자동 응답 데몬] 최신 틱톡 영상 신규 댓글 스캔 중...", flush=True)
    database.init_db()

    user_data_dir = os.path.expanduser("~/.config/tiktok_stealth_profile")
    if not os.path.exists(user_data_dir):
        print(f"⚠️ [틱톡 세션 없음] '{user_data_dir}' 폴더가 없습니다. 먼저 scratch/launch_tiktok_login_window.py 로 로그인해 주세요.", flush=True)
        return

    global daily_reply_count, last_reset_date
    current_date = datetime.now().strftime("%Y-%m-%d")
    if current_date != last_reset_date:
        daily_reply_count = 0
        last_reset_date = current_date
        print(f"🔄 [날짜 변경] 틱톡 일일 카운터 초기화: {current_date}", flush=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()

        profile_url = "https://www.tiktok.com/@momdad_style"
        try:
            await page.goto(profile_url, wait_until="domcontentloaded")
            await asyncio.sleep(4)

            # 최신 영상 링크 수집 (최신 3개 영상 집중 감시)
            video_hrefs = await page.evaluate("""
                () => {
                    const anchors = Array.from(document.querySelectorAll('a[href*="/video/"]'));
                    const seen = new Set();
                    const links = [];
                    for (const a of anchors) {
                        const href = a.getAttribute('href');
                        if (href && !seen.has(href)) {
                            seen.add(href);
                            links.push(href);
                        }
                    }
                    return links;
                }
            """)

            if not video_hrefs:
                print("  ℹ️ 틱톡 최신 영상 목록을 찾지 못했습니다. (로그인 세션 확인 필요)", flush=True)
                await context.close()
                return

            # 최신 3개 영상 탐색
            target_videos = video_hrefs[:3]
            print(f"  🎬 틱톡 최신 영상 {len(target_videos)}개 스캔 시작...", flush=True)

            for v_idx, v_href in enumerate(target_videos):
                video_url = v_href if v_href.startswith("http") else f"https://www.tiktok.com{v_href}"
                video_id = database.extract_tiktok_video_id(video_url)
                print(f"  👉 [{v_idx+1}/{len(target_videos)}] 틱톡 영상 탐색: {video_url} (ID: {video_id})", flush=True)

                try:
                    await page.goto(video_url, wait_until="domcontentloaded")
                    await asyncio.sleep(3.5)

                    # 영상 설명/캡션에서 상품 번호 추출
                    caption_text = await page.evaluate("""
                        () => {
                            const descEl = document.querySelector('[data-e2e="browse-video-desc"], h1[data-e2e="video-desc"], [class*="DivDescription"]');
                            return descEl ? descEl.textContent : '';
                        }
                    """)
                    
                    product_no = "9" # 기본값
                    m_no = re.search(r'(\d+)번', caption_text)
                    if m_no:
                        product_no = m_no.group(1)

                    # 댓글 목록 및 미응답 유저 탐색
                    unreplied_users = await page.evaluate("""
                        () => {
                            const comments = Array.from(document.querySelectorAll('[data-e2e="comment-level-1"], [class*="DivCommentItemContainer"]'));
                            const blacklist = ['momdad_style', 'tiktok', 'admin', 'user'];
                            const results = [];

                            for (const c of comments) {
                                const userAnchor = c.querySelector('a[href*="/@"]');
                                if (!userAnchor) continue;
                                const userHref = userAnchor.getAttribute('href') || '';
                                const unameMatch = userHref.match(/@([^/?#]+)/);
                                if (!unameMatch) continue;
                                const uname = unameMatch[1].trim();
                                if (blacklist.some(b => uname.toLowerCase() === b.toLowerCase())) continue;

                                const commentText = c.textContent || '';
                                // 이미 내가 답변을 달았는지 체크
                                if (commentText.includes('프로필 상단 링크') || commentText.includes('6070.piella.shop')) {
                                    continue;
                                }

                                const replyBtn = c.querySelector('[data-e2e="comment-reply-1"], span:has-text("Reply"), span:has-text("답글"), [class*="Reply"]');
                                if (replyBtn) {
                                    results.push({ username: uname, comment_text: commentText.slice(0, 50) });
                                }
                            }
                            return results;
                        }
                    """)

                    # DB 대조 후 신규 미응답 유저만 필터링
                    new_users = []
                    for u in unreplied_users:
                        status = database.get_tiktok_user_status_for_video(u['username'], video_id)
                        if not status['reply_posted']:
                            new_users.append((u, status))

                    if not new_users:
                        continue

                    print(f"    🔥 [틱톡 영상 {video_id}] 🎯 신규 미응답 댓글 {len(new_users)}건 감지! 유저: {[u[0]['username'] for u in new_users]}", flush=True)

                    for uinfo, status in new_users:
                        uname = uinfo['username']
                        if daily_reply_count >= MAX_DAILY_REPLY:
                            print(f"      🛡️ [하루 안전 한도 달성] 오늘 틱톡 댓글 {daily_reply_count}건 작성 완료.", flush=True)
                            break

                        # 1. 대댓글 작성 전 즉시 DB 락 선-선언 (중복 도배 100% 원천 차단)
                        database.update_tiktok_user_reply_status(uname, video_id, True)

                        reply_msg = f"@{uname} 어머님 안녕하세요! 💕 문의하신 {product_no}번 상품은 프로필 상단 링크(6070.piella.shop) ➔ {product_no}번에서 바로 보실 수 있습니다! ✨"

                        try:
                            # 해당 유저 댓글의 답글(Reply) 버튼 클릭
                            reply_clicked = await page.evaluate(f"""
                                () => {{
                                    const comments = Array.from(document.querySelectorAll('[data-e2e="comment-level-1"], [class*="DivCommentItemContainer"]'));
                                    for (const c of comments) {{
                                        const userAnchor = c.querySelector('a[href*="/@{uname}"]');
                                        if (userAnchor) {{
                                            const replyBtn = c.querySelector('[data-e2e="comment-reply-1"], span:has-text("Reply"), span:has-text("답글"), [class*="Reply"]');
                                            if (replyBtn) {{
                                                replyBtn.click();
                                                return true;
                                            }}
                                        }}
                                    }}
                                    return false;
                                }}
                            """)

                            if reply_clicked:
                                await asyncio.sleep(1.5)
                                input_box = page.locator('[data-e2e="comment-input"], div[contenteditable="true"], textarea').first
                                if await input_box.is_visible():
                                    await input_box.click()
                                    await asyncio.sleep(0.5)
                                    await input_box.fill(reply_msg)
                                    await asyncio.sleep(1)

                                    post_btn = page.locator('[data-e2e="comment-post"], button:has-text("Post"), button:has-text("게시")').first
                                    if await post_btn.is_visible():
                                        await post_btn.click(force=True)
                                        await asyncio.sleep(3)
                                        daily_reply_count += 1
                                        print(f"      ✅ 💬 틱톡 @{uname} 대댓글 1회 작성 완료! (오늘 {daily_reply_count}/{MAX_DAILY_REPLY}건)", flush=True)
                        except Exception as e_reply:
                            print(f"      ⚠️ 틱톡 대댓글 작성 예외: {e_reply}", flush=True)

                        # 2. 유저 프로필 이동 후 1:1 메시지(DM) 시도 (선택)
                        try:
                            user_profile_url = f"https://www.tiktok.com/@{uname}"
                            await page.goto(user_profile_url, wait_until="domcontentloaded")
                            await asyncio.sleep(2.5)

                            msg_btn = page.locator('button:has-text("Message"), button:has-text("메시지"), [data-e2e="message-button"]').first
                            if await msg_btn.is_visible():
                                database.update_tiktok_user_dm_status(uname, video_id, True)
                                await msg_btn.click()
                                await asyncio.sleep(2.5)
                                dm_box = page.locator('div[contenteditable="true"], textarea').first
                                if await dm_box.is_visible():
                                    await dm_box.click()
                                    await page.keyboard.type(f"안녕하세요 어머님! 💕 요청하신 {product_no}번 상품 안내입니다: https://6070.piella.shop/p/{product_no}")
                                    await page.keyboard.press("Enter")
                                    await asyncio.sleep(1.5)
                                    print(f"      ✅ 📩 틱톡 @{uname} 1:1 DM 발송 성공!", flush=True)
                        except Exception:
                            pass

                        safe_delay = random.uniform(15, 25)
                        print(f"      🛡️ [계정 보호] 다음 틱톡 반응 전 {safe_delay:.1f}초 안전 휴식...", flush=True)
                        await asyncio.sleep(safe_delay)

                except Exception as e_vid:
                    print(f"      ⚠️ [틱톡 영상 처리 예외] {v_href}: {e_vid}", flush=True)

        except Exception as e_profile:
            print(f"  ⚠️ [틱톡 프로필 접근 예외]: {e_profile}", flush=True)

        await context.close()

async def tiktok_daemon_loop():
    print("🚀 [틱톡 최신 영상 실시간 자동 응답 데몬 구동]...", flush=True)
    while True:
        try:
            await run_tiktok_daemon_check()
        except Exception as e:
            print(f"⚠️ 틱톡 데몬 예외: {e}", flush=True)
            traceback.print_exc()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(tiktok_daemon_loop())
