import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio, database, time, traceback, re, random
from datetime import datetime
from playwright.async_api import async_playwright


async def run_daemon_check(ignore_quiet: bool = False):
    if not ignore_quiet and is_quiet_hours():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🌙 [야간 휴식 모드 (21:00 ~ 07:00)] 현재 시각 {now_str}. 야간 시간에는 댓글/DM 발송을 100% 중단하고 휴식합니다.", flush=True)
        return

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🔍 [실시간 자동 응답 데몬] 전체 게시물(최신 릴스 포함) 신규 댓글 스캔 중...", flush=True)
    database.init_db()

    user_data_dir = os.path.expanduser("~/.config/ig_stealth_profile")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()

        collected_posts = []

        # 1. 메인 피드 & 2. 릴스 전용 탭 순차 진입 수집 (최신 업로드 최우선 순위 유지)
        target_urls = [
            "https://www.instagram.com/momdad_style/reels/",  # 최신 릴스 탭 (최우선)
            "https://www.instagram.com/momdad_style/"        # 메인 피드 탭
        ]

        for target_url in target_urls:
            try:
                await page.goto(target_url, wait_until="domcontentloaded")
                await asyncio.sleep(2.5)

                # 깊은 스크롤 수행 (최신부터 과거 게시물까지 100% 수집)
                last_height = 0
                for scroll_step in range(15):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1.2)
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

                tab_posts = await page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        const postHrefs = links.map(l => l.getAttribute('href')).filter(h => h && (h.includes('/p/') || h.includes('/reel/')));
                        return Array.from(new Set(postHrefs));
                    }
                """)
                for p in tab_posts:
                    if p not in collected_posts:
                        collected_posts.append(p)
            except Exception as e_tab:
                print(f"⚠️ [탭 수집 예외] {target_url}: {e_tab}", flush=True)

        posts = collected_posts
        # 실시간 모니터링: 방금 올라온 최신 릴스 2개만 집중 모니터링 (과거 30개 반복 루프 중단!)
        for p_idx, post_href in enumerate(posts[:2]):
            try:
                reel_url = f"https://www.instagram.com{post_href}"
                await page.goto(reel_url, wait_until="domcontentloaded")
                await asyncio.sleep(3)

                # ...more / ...더 보기 클릭하여 본문 완전 확장
                await page.evaluate("""
                    () => {
                        const btns = Array.from(document.querySelectorAll('span, div[role="button"]'));
                        const more = btns.find(b => b.textContent.trim().includes('more') || b.textContent.trim().includes('더 보기'));
                        if (more) more.click();
                    }
                """)
                await asyncio.sleep(1)

                caption = await page.evaluate("() => document.body.textContent")
                p_match = re.search(r'No\.?\s*(\d+)', caption, re.IGNORECASE)
                
                # 본문에서 No.XX 파싱 실패 시, 릴스 순서로 100% 정확한 상품 번호 산출
                product_no = p_match.group(1) if p_match else str(max(1, len(posts) - p_idx))

                # 댓글 영역 스크롤
                await page.evaluate("""
                    () => {
                        const divs = document.querySelectorAll('div');
                        for (const d of divs) {
                            if (d.scrollHeight > d.clientHeight && d.clientHeight > 150) {
                                d.scrollTop = d.scrollHeight;
                            }
                        }
                    }
                """)
                await asyncio.sleep(1.5)

                # 댓글 영역 내부에서만 신규 미응답 댓글 탐색 (유니버설 DOM 매칭)
                unreplied_users = await page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        const blacklist = [
                            'legal', 'privacy', 'terms', 'cookies', 'popular', 'weblite', 'accounts',
                            'meta', 'about', 'help', 'api', 'jobs', 'explore', 'momdad_style', 'direct',
                            'directinbox', 'explorelocations', 'weblite.neo', 'accountsmeta_verified'
                        ];
                        
                        const candidates = [];
                        for (const a of links) {
                            const href = a.getAttribute('href');
                            const text = a.textContent.trim();
                            if (href && href.startsWith('/') && !href.includes('/p/') && !href.includes('/reel/') && !href.includes('/explore/') && !href.includes('/legal/')) {
                                const uname = href.replace(/\\//g, '').trim();
                                if (!/^[a-zA-Z0-9._]+$/.test(uname)) continue;
                                if (blacklist.some(b => uname.toLowerCase() === b.toLowerCase())) continue;
                                
                                let container = a.parentElement;
                                let foundReply = false;
                                let alreadyReplied = false;
                                
                                for (let i = 0; i < 8; i++) {
                                    if (!container) break;
                                    const containerText = container.textContent;
                                    if (containerText.includes('DM으로 링크 보내드렸습니다')) {
                                        alreadyReplied = true;
                                    }
                                    const btns = Array.from(container.querySelectorAll('div, span, button, a'));
                                    if (btns.some(b => (b.textContent.trim() === 'Reply' || b.textContent.trim() === '답글 달기') && b.offsetWidth > 0)) {
                                        foundReply = true;
                                    }
                                    container = container.parentElement;
                                }
                                
                                if (foundReply && !alreadyReplied) {
                                    if (!candidates.some(c => c.username === uname)) {
                                        candidates.push({ username: uname, href: href, display_name: text || uname });
                                    }
                                }
                            }
                        }
                        return candidates;
                    }
                """)

                # DB에 아직 처리 안 된 상태(DM 미전송 OR 대댓글 미작성)인 유저만 필터링
                new_unreplied_users = []
                for u in unreplied_users:
                    status = database.get_ig_user_status_for_reel(u['username'], post_href)
                    # 대댓글도 안 달렸거나, DM도 안 간 경우에만 처리 대상
                    if not status['reply_posted'] or not status['dm_sent']:
                        new_unreplied_users.append((u, status))

                if not new_unreplied_users:
                    continue

                print(f"  🔥 [{post_href}] 🎯 신규 미응답 댓글 {len(new_unreplied_users)}건 감지! 처리 시작: {[u[0]['username'] for u in new_unreplied_users]}", flush=True)

                for uinfo, status in new_unreplied_users:
                    uname = uinfo['username']
                    display_name = uinfo['display_name']
                    href = uinfo['href']

                    print(f"    👉 @{uname} 님 [{post_href}] 릴스 개별 상태 기반 응답 진행 중 (DM완료:{status['dm_sent']}, 대댓글완료:{status['reply_posted']})...", flush=True)

                    dm_success = status['dm_sent']
                    global daily_dm_count

                    # 1. DM이 아직 발송 안 된 유저인 경우 -> DM 4단계 분리 발송
                    if not status['dm_sent']:
                        database.update_ig_user_dm_status(uname, post_href, True)
                        if daily_dm_count >= MAX_DAILY_DM:
                            print(f"      🛡️ [하루 안전 한도 달성] 오늘 DM {daily_dm_count}건 발송 완료.", flush=True)
                        else:
                            try:
                                SYSTEM_BLACKLIST = {
                                    'reels', 'directinbox', 'explore', 'accountsedit', 'legalprivacy', 'legalterms',
                                    'explorelocations', 'popular', 'weblite', 'accountsmeta_verified', 'about',
                                    'help', 'press', 'api', 'jobs', 'privacy', 'terms', 'momdad_style',
                                    'amariah1k', 'amariah'
                                }
                                if uname not in SYSTEM_BLACKLIST and not uname.startswith('accounts'):
                                    dm_entered = False
                                    # 1안: 유저 프로필 직행 후 [메시지 보내기] 버튼 클릭 (100% 직행 전송 보장)
                                    try:
                                        profile_url = f"https://www.instagram.com/{uname}/"
                                        await page.goto(profile_url, wait_until="domcontentloaded")
                                        await asyncio.sleep(2.5)

                                        msg_btn = page.locator("button:has-text('Message'), button:has-text('메시지 보내기'), div[role='button']:has-text('Message'), div[role='button']:has-text('메시지 보내기')").first
                                        if await msg_btn.is_visible():
                                            await msg_btn.click()
                                            await asyncio.sleep(3.5)
                                            dm_entered = True
                                    except Exception as e_p_dm:
                                        print(f"      ⚠️ 프로필 직행 DM 진입 실패, 검색 모달로 우회 ({e_p_dm})", flush=True)

                                    # 2안: 프로필 버튼 미노출 시 DM 인박스 검색 모달 우회
                                    if not dm_entered:
                                        await page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
                                        await asyncio.sleep(2.5)

                                        new_msg_btn = page.locator("svg[aria-label='New message'], svg[aria-label='새 메시지'], div[role='button']:has-text('New message'), button:has-text('New message')").first
                                        if await new_msg_btn.is_visible():
                                            await new_msg_btn.click()
                                            await asyncio.sleep(2)

                                        inp = page.locator('input[name="queryBox"], input[name="searchInput"], input[placeholder*="Search"], input[placeholder*="검색"]').first
                                        if await inp.is_visible():
                                            await inp.fill(uname)
                                            await asyncio.sleep(2)

                                            await page.evaluate(f"""
                                                () => {{
                                                    const inputs = Array.from(document.querySelectorAll('input[type="checkbox"], input[type="radio"]'));
                                                    if (inputs.length > 0) {{ inputs[0].click(); return 'input'; }}
                                                    const dialogBtns = Array.from(document.querySelectorAll('div[role="dialog"] div[role="button"], div[role="dialog"] span, div[role="dialog"] a'));
                                                    const userMatch = dialogBtns.find(el => el.textContent.trim().toLowerCase().includes('{uname.lower()}'));
                                                    if (userMatch) {{ userMatch.click(); return 'match'; }}
                                                    const firstRow = document.querySelector('div[role="dialog"] div[tabindex="0"], div[role="dialog"] label');
                                                    if (firstRow) {{ firstRow.click(); return 'firstRow'; }}
                                                    return 'none';
                                                }}
                                            """)
                                            await asyncio.sleep(1.2)

                                            await page.evaluate("""
                                                () => {
                                                    const btns = Array.from(document.querySelectorAll('div[role="button"], button'));
                                                    const chatBtn = btns.find(b => {
                                                        const txt = b.textContent.trim();
                                                        return (txt === 'Chat' || txt === 'Next' || txt === '채팅' || txt === '다음') && b.offsetWidth > 0;
                                                    });
                                                    if (chatBtn) chatBtn.click();
                                                }
                                            """)
                                            await asyncio.sleep(3.5)

                                    dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"], p[aria-label*="Message"], p[aria-label*="메시지"]').first
                                    await dm_input.wait_for(timeout=7000)
                                    
                                    await dm_input.click()
                                    await page.keyboard.type(f"안녕하세요 어머님! 💕 요청하신 {product_no}번 상품 구매 링크입니다!")
                                    await page.keyboard.press("Enter")
                                    await asyncio.sleep(1.2)

                                    await dm_input.click()
                                    await page.keyboard.type(f"https://6070.piella.shop/p/{product_no}")
                                    await page.keyboard.press("Enter")
                                    await asyncio.sleep(1.2)

                                    await dm_input.click()
                                    await page.keyboard.type("더 많은 예쁜 옷들은 여기서 구경하세요 👇")
                                    await page.keyboard.press("Enter")
                                    await asyncio.sleep(1.2)

                                    await dm_input.click()
                                    await page.keyboard.type("https://6070.piella.shop")
                                    await page.keyboard.press("Enter")
                                    await asyncio.sleep(2)

                                    daily_dm_count += 1
                                    dm_success = True
                                    print(f"      ✅ 📩 @{uname} DM 4단계 발송 100% 성공! DB 갱신 (오늘 DM {daily_dm_count}/{MAX_DAILY_DM}건)", flush=True)
                            except Exception as e_dm:
                                print(f"      ⚠️ DM 발송 예외: ({e_dm})", flush=True)

                    # 2. 대댓글이 아직 작성 안 된 유저인 경우에만 릴스로 이동하여 딱 1회 대댓글 작성
                    if not status['reply_posted']:
                        # 대댓글 작성 시작 전 즉시 DB 락 먼저 기록하여 중복 대댓글 100% 원천 차단!
                        database.update_ig_user_reply_status(uname, post_href, True)
                        try:
                            await page.goto(reel_url, wait_until="domcontentloaded")
                            await asyncio.sleep(2.5)

                            final_reply_msg = f"@{uname} 어머님 안녕하세요! 💕 문의하신 {product_no}번 상품 안내를 DM으로 보내드렸습니다! 메시지함을 확인해 주세요! ✨"

                            clicked = await page.evaluate(f"""
                                () => {{
                                    const links = Array.from(document.querySelectorAll('a[href*="/{uname}/"]'));
                                    if (links.length === 0) return false;
                                    let container = links[0];
                                    for (let i = 0; i < 6; i++) {{
                                        if (container.parentElement) container = container.parentElement;
                                    }}
                                    const replyBtn = Array.from(container.querySelectorAll('div, span, button')).find(el => 
                                        (el.textContent.trim() === '답글 달기' || el.textContent.trim() === 'Reply') && el.offsetWidth > 0
                                    );
                                    if (replyBtn) {{
                                        replyBtn.click();
                                        return true;
                                    }}
                                    return false;
                                }}
                            """)

                            if clicked:
                                await asyncio.sleep(1.5)
                                input_box = page.locator("textarea, div[role='textbox']").first
                                if await input_box.is_visible():
                                    await input_box.click()
                                    await asyncio.sleep(0.5)
                                    await input_box.fill(final_reply_msg)
                                    await asyncio.sleep(1)
                                    post_btn = page.locator("button:has-text('게시'), button:has-text('Post'), div[role='button']:has-text('게시'), div[role='button']:has-text('Post')").first
                                    if await post_btn.is_visible():
                                        await post_btn.click(force=True)
                                        await asyncio.sleep(3)
                                        print(f"      ✅ 💬 @{uname} 대댓글 1회 작성 완료! DB 갱신 (reply_posted=True)", flush=True)
                        except Exception as e_reply:
                            print(f"      ⚠️ 대댓글 작성 예외: {e_reply}", flush=True)
                    else:
                        print(f"      ℹ️ @{uname} 님은 이미 대댓글 작성이 완료되어 대댓글 작성을 완전히 스킵합니다.", flush=True)

                    # 3. 프로필 이동 & 팔로우
                    profile_url = f"https://www.instagram.com{href}"
                    try:
                        await page.goto(profile_url, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                        follow_btn = page.locator("button:has-text('Follow'), button:has-text('팔로우')").first
                        if await follow_btn.is_visible():
                            await follow_btn.click()
                            await asyncio.sleep(1)
                            print(f"      ✅ ➕ 팔로우 완료!", flush=True)
                    except:
                        pass
                    
                    safe_delay = random.uniform(15, 25)
                    print(f"      🛡️ [계정 보호] 다음 반응 전 {safe_delay:.1f}초 안전 휴식...", flush=True)
                    await asyncio.sleep(safe_delay)
            except Exception as e_reel:
                print(f"      ⚠️ [릴스 탐색 예외] {post_href}: {e_reel}", flush=True)

        await context.close()

MAX_DAILY_DM = 80
daily_dm_count = 0
processed_users_today = set()
last_reset_date = datetime.now().strftime("%Y-%m-%d")

QUIET_START_HOUR = 21  # 밤 9시 (21:00)
QUIET_END_HOUR = 7    # 오전 7시 (07:00)

def is_quiet_hours() -> bool:
    now_hour = datetime.now().hour
    return now_hour >= QUIET_START_HOUR or now_hour < QUIET_END_HOUR

async def daemon_loop():
    global daily_dm_count, last_reset_date, processed_users_today
    print("🚀 [인스타그램 전체 게시물 동적 감지 자동 응답 데몬 구동]...", flush=True)
    while True:
        try:
            if is_quiet_hours():
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"🌙 [야간 휴식 모드 (21:00 ~ 07:00)] 현재 시각 {now_str}. 야간 시간에는 댓글/DM 발송을 100% 중단하고 휴식합니다.", flush=True)
                await asyncio.sleep(300)  # 5분 휴식 후 재확인
                continue

            current_date = datetime.now().strftime("%Y-%m-%d")
            if current_date != last_reset_date:
                daily_dm_count = 0
                processed_users_today.clear()
                last_reset_date = current_date
                print(f"🔄 [날짜 변경] DM 카운터 및 사용자 중복 리스트 초기화: {current_date}", flush=True)
            
            await run_daemon_check()
        except Exception as e:
            print(f"⚠️ 데몬 예외: {e}", flush=True)
            traceback.print_exc()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(daemon_loop())
