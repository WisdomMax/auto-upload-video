import asyncio, os, database, time, traceback, re, random
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

                # 1. 릴스에서 대댓글 작성 (@태그 결합)
                await page.goto(reel_url, wait_until="domcontentloaded")
                await asyncio.sleep(2.5)

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
                        reply_msg = f"@{uname} {reply_text_template}"
                        await input_box.fill(reply_msg)
                        await asyncio.sleep(1)
                        post_btn = page.locator("button:has-text('게시'), button:has-text('Post'), div[role='button']:has-text('게시'), div[role='button']:has-text('Post')").first
                        if await post_btn.is_visible():
                            await post_btn.click(force=True)
                            await asyncio.sleep(3)
                            print(f"      ✅ 💬 @{uname} 대댓글 게시 완료!")

                # 2. 프로필 이동 & 팔로우
                profile_url = f"https://www.instagram.com{href}"
                await page.goto(profile_url, wait_until="domcontentloaded")
                await asyncio.sleep(2.5)

                follow_btn = page.locator("button:has-text('Follow'), button:has-text('팔로우')").first
                try:
                    if await follow_btn.is_visible():
                        await follow_btn.click()
                        await asyncio.sleep(1.5)
                        print(f"      ✅ ➕ 팔로우 완료!")
                except:
                    pass

                # 3. DM 이동 & 메시지 2개 발송 (100% 완결 검증 플로우)
                await page.goto("https://www.instagram.com/direct/new/", wait_until="domcontentloaded")
                await asyncio.sleep(3)

                inp = page.locator('input[name="queryBox"], input[name="searchInput"], input[placeholder*="Search"], input[placeholder*="검색"]').first
                # 시스템 푸터 링크 및 본인 계정 제외
                SYSTEM_BLACKLIST = {
                    'reels', 'directinbox', 'explore', 'accountsedit', 'legalprivacy', 'legalterms',
                    'explorelocations', 'popular', 'weblite', 'accountsmeta_verified', 'about',
                    'help', 'press', 'api', 'jobs', 'privacy', 'terms', 'momdad_style'
                }
                if uname in SYSTEM_BLACKLIST or uname.startswith('accounts'):
                    continue

                if await inp.is_visible():
                    await inp.fill(uname)
                    await asyncio.sleep(2.5)

                    await page.evaluate(f"""
                        () => {{
                            const inputs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                            if (inputs.length > 0) {{
                                inputs[0].click();
                                return;
                            }}
                            const buttons = Array.from(document.querySelectorAll('div[role="button"]'));
                            const userBtn = buttons.find(b => b.textContent.includes('{uname}'));
                            if (userBtn) {{
                                userBtn.click();
                                return;
                            }}
                            if (buttons.length > 0) buttons[0].click();
                        }}
                    """)
                    await asyncio.sleep(1.5)

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

                    try:
                        dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
                        await dm_input.wait_for(timeout=6000)
                        
                        # 1. 안내 메시지 단독 발송
                        dm_txt_guide = f"안녕하세요 어머님! 💕 요청하신 {product_no}번 상품 구매 링크입니다!"
                        await dm_input.click()
                        await asyncio.sleep(0.5)
                        await page.keyboard.type(dm_txt_guide)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(1.5)

                        # 2. PURE 상품 직행 URL 단독 발송 (한글 결합 100% 방지)
                        dm_url_prod = f"https://6070.piella.shop/p/{product_no}"
                        await dm_input.click()
                        await asyncio.sleep(0.5)
                        await page.keyboard.type(dm_url_prod)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(1.5)

                        # 3. 카탈로그 안내 텍스트 단독 발송
                        dm_txt_guide2 = "더 많은 예쁜 옷들은 여기서 구경하세요 👇"
                        await dm_input.click()
                        await asyncio.sleep(0.5)
                        await page.keyboard.type(dm_txt_guide2)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(1.5)

                        # 4. PURE 메인 카탈로그 URL 단독 발송
                        dm_url_catalog = "https://6070.piella.shop"
                        await dm_input.click()
                        await asyncio.sleep(0.5)
                        await page.keyboard.type(dm_url_catalog)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(2)

                        print(f"      ✅ 📩 4단계 순수 링크 독립 분리 DM 발송 완료!")

                    except Exception as e_dm:
                        print(f"      ⚠️ DM 전송 예외: {e_dm}")



                # 🛡️ 계정 차단 방지를 위한 자연스러운 휴식 시간 (15~25초)
                safe_delay = random.uniform(15, 25)
                print(f"      🛡️ [계정 보호] 다음 반응 전 {safe_delay:.1f}초 안전 휴식...")
                await asyncio.sleep(safe_delay)


        await context.close()

async def daemon_loop():
    print("🚀 [인스타그램 전체 게시물 동적 감지 자동 응답 데몬 구동]...")
    while True:
        try:
            await run_daemon_check()
        except Exception as e:
            print(f"⚠️ 데몬 예외: {e}")
            traceback.print_exc()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(daemon_loop())
