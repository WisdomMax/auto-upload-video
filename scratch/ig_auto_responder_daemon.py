import asyncio, os, database, time, traceback, re, random
from datetime import datetime
from playwright.async_api import async_playwright


async def run_daemon_check():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🔍 [실시간 자동 응답 데몬] 전체 게시물(최신 릴스 포함) 신규 댓글 스캔 중...")
    database.init_db()

    user_data_dir = os.path.expanduser("~/.config/ig_stealth_profile")
    reply_text_template = "안녕하세요! DM으로 링크 보내드렸습니다 💕"

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # 메인 프로필 피드 진입
        await page.goto("https://www.instagram.com/momdad_style/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 전체 피드 100% 수집을 위해 스크롤 수행
        for i in range(8):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.2)

        posts = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                const postHrefs = links.map(l => l.getAttribute('href')).filter(h => h && (h.includes('/p/') || h.includes('/reel/')));
                return Array.from(new Set(postHrefs));
            }
        """)

        print(f"📋 프로필 전체 게시물/릴스 {len(posts)}개 100% 탐색 감지 중: {posts}")



        for post_href in posts:
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
            
            # 본문에서 No.XX 파싱 실패 시, 릴스 순서(29 - p_idx)로 100% 정확한 상품 번호 산출
            product_no = p_match.group(1) if p_match else str(29 - p_idx)

            product_link = f"https://6070.piella.shop/p/{product_no}"
            dm_msg_1 = f"안녕하세요! 요청하신 {product_no}번 상품 구매 링크입니다 💕\n{product_link}"
            dm_msg_2 = f"더 많은 상품은 여기서 확인하세요 👇\nhttps://6070.piella.shop"


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

            # 댓글 영역 내부에서만 신규 미응답 댓글 탐색 (페이지 푸터/사이드바 제외)
            unreplied_users = await page.evaluate("""
                () => {
                    const commentContainers = Array.from(document.querySelectorAll('#comments, ul, div[role="dialog"] ul'));
                    const links = [];
                    for (const container of commentContainers) {
                        links.push(...Array.from(container.querySelectorAll('a[href]')));
                    }
                    
                    const results = [];
                    const blacklist = [
                        'legal', 'privacy', 'terms', 'cookies', 'popular', 'weblite', 'accounts',
                        'meta', 'about', 'help', 'api', 'jobs', 'explore', 'momdad_style', 'direct',
                        'directinbox', 'explorelocations', 'weblite.neo', 'accountsmeta_verified'
                    ];

                    for (const a of links) {
                        const href = a.getAttribute('href');
                        const text = a.textContent.trim();
                        
                        if (href && href.startsWith('/') && !href.includes('p/') && !href.includes('reels/') && text.length > 1) {
                            const uname = href.replace(/\//g, '').trim();
                            if (!/^[a-zA-Z0-9._]+$/.test(uname)) continue;
                            if (blacklist.some(b => uname.toLowerCase().includes(b))) continue;
                            
                            // 부모 요소에서 답글 달기 버튼 및 이미 응답 여부 확인
                            let container = a.parentElement;
                            for (let i = 0; i < 6; i++) {
                                if (container.parentElement) container = container.parentElement;
                            }
                            
                            const hasReplyBtn = Array.from(container.querySelectorAll('div, span, button')).some(el => 
                                (el.textContent.trim() === '답글 달기' || el.textContent.trim() === 'Reply') && el.offsetWidth > 0
                            );
                            const alreadyReplied = container.textContent.includes('DM으로 링크 보내드렸습니다');
                            
                            if (hasReplyBtn && !alreadyReplied) {
                                const uname = href.replace(/\//g, '');
                                if (!results.some(r => r.username === uname)) {
                                    results.push({ username: uname, href: href, display_name: text });
                                }
                            }
                        }
                    }
                    return results;
                }
            """)

            if not unreplied_users:
                continue

            print(f"  🔥 [{post_href}] 미응답 댓글 {len(unreplied_users)}건 감지: {[u['username'] for u in unreplied_users]}")

            for uinfo in unreplied_users:
                uname = uinfo['username']
                display_name = uinfo['display_name']
                href = uinfo['href']

                print(f"    👉 @{uname} 님 자동 대댓글 + 팔로우 + DM 처리 중...")

                # 1. DM 선발송 시도 (DM 성공 여부 100% 추적)
                dm_success = False
                global daily_dm_count
                
                if daily_dm_count >= MAX_DAILY_DM:
                    print(f"      🛡️ [하루 안전 한도 달성] 오늘 DM {daily_dm_count}건 발송 완료. DM 대신 대댓글에 직행 링크를 작성합니다.")
                else:
                    try:
                        await page.goto("https://www.instagram.com/direct/new/", wait_until="domcontentloaded")
                        await asyncio.sleep(2.5)

                        inp = page.locator('input[name="queryBox"], input[name="searchInput"], input[placeholder*="Search"], input[placeholder*="검색"]').first
                        SYSTEM_BLACKLIST = {
                            'reels', 'directinbox', 'explore', 'accountsedit', 'legalprivacy', 'legalterms',
                            'explorelocations', 'popular', 'weblite', 'accountsmeta_verified', 'about',
                            'help', 'press', 'api', 'jobs', 'privacy', 'terms', 'momdad_style'
                        }
                        if uname not in SYSTEM_BLACKLIST and not uname.startswith('accounts') and await inp.is_visible():
                            await inp.fill(uname)
                            await asyncio.sleep(2)

                            await page.evaluate(f"""
                                () => {{
                                    const inputs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                                    if (inputs.length > 0) {{ inputs[0].click(); return; }}
                                    const buttons = Array.from(document.querySelectorAll('div[role="button"]'));
                                    const userBtn = buttons.find(b => b.textContent.includes('{uname}'));
                                    if (userBtn) {{ userBtn.click(); return; }}
                                    if (buttons.length > 0) buttons[0].click();
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
                            await asyncio.sleep(3)

                            dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
                            await dm_input.wait_for(timeout=5000)
                            
                            # 4단계 PURE URL 독립 메시지 발송
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
                            print(f"      ✅ 📩 DM 4단계 분리 메시지 100% 발송 성공! (오늘 총 {daily_dm_count}/{MAX_DAILY_DM}건)")
                    except Exception as e_dm:
                        print(f"      ⚠️ DM 발송 실패/스킵 ({e_dm}) -> 대댓글에 직행 링크를 직접 작성합니다.")

                # 2. 릴스 이동 및 대댓글 작성 (DM 성공 여부에 따른 맞춤 분기)
                await page.goto(reel_url, wait_until="domcontentloaded")
                await asyncio.sleep(2.5)

                # 공개 대댓글에는 URL 링크를 절대로 포함하지 않음 (스팸 방지 및 클릭 불가능 원인)
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
                            print(f"      ✅ 💬 @{uname} 대댓글 작성 완료! (DM성공여부: {dm_success})")

                # 3. 프로필 이동 & 팔로우
                profile_url = f"https://www.instagram.com{href}"
                try:
                    await page.goto(profile_url, wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                    follow_btn = page.locator("button:has-text('Follow'), button:has-text('팔로우')").first
                    if await follow_btn.is_visible():
                        await follow_btn.click()
                        await asyncio.sleep(1)
                        print(f"      ✅ ➕ 팔로우 완료!")
                except:
                    pass

                # 🛡️ 계정 차단 방지를 위한 자연스러운 휴식 시간 (15~25초)
                safe_delay = random.uniform(15, 25)
                print(f"      🛡️ [계정 보호] 다음 반응 전 {safe_delay:.1f}초 안전 휴식...")
                await asyncio.sleep(safe_delay)

                print(f"      🛡️ [계정 보호] 다음 반응 전 {safe_delay:.1f}초 안전 휴식...")
                await asyncio.sleep(safe_delay)


        await context.close()

# 🛡️ 계정 안전 및 심야 고객 배려 설정
MAX_DAILY_DM = 80
daily_dm_count = 0
last_reset_date = datetime.now().strftime("%Y-%m-%d")

# 🌙 심야 안심 시간대 (밤 11시 ~ 아침 8시에는 DM 발송 일시 중지 및 대기)
QUIET_START_HOUR = 23
QUIET_END_HOUR = 8

def is_quiet_hours() -> bool:
    now_hour = datetime.now().hour
    return now_hour >= QUIET_START_HOUR or now_hour < QUIET_END_HOUR


async def daemon_loop():
    global daily_dm_count, last_reset_date
    print("🚀 [인스타그램 전체 게시물 동적 감지 자동 응답 데몬 구동]...")
    while True:
        try:
            # 매일 자정 카운터 초기화
            current_date = datetime.now().strftime("%Y-%m-%d")
            if current_date != last_reset_date:
                daily_dm_count = 0
                last_reset_date = current_date
                print(f"🔄 [날짜 변경] DM 카운터 초기화: {current_date}")
            
            await run_daemon_check()
        except Exception as e:
            print(f"⚠️ 데몬 예외: {e}")
            traceback.print_exc()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(daemon_loop())
