import asyncio, os, json, re, time, random

from playwright.async_api import async_playwright

CHECKPOINT_FILE = "/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/scratch/retroactive_checkpoint.json"

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"processed": []}

def save_checkpoint(data):
    try:
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"체크포인트 저장 오류: {e}")

async def run_newest_reels_scan():
    print("=== [최신 릴스(29번 포함 1~5번 최신 영상) 댓글 전수 소급 + DM 발송 시작] ===")
    checkpoint = load_checkpoint()
    processed_set = set(checkpoint.get("processed", []))

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

        # 프로필 메인 피드에서 전체 릴스 수집
        await page.goto("https://www.instagram.com/momdad_style/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        posts = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                const postHrefs = links.map(l => l.getAttribute('href')).filter(h => h && (h.includes('/p/') || h.includes('/reel/')));
                return Array.from(new Set(postHrefs));
            }
        """)

        print(f"📋 프로필 피드 상단 릴스 {len(posts)}개 포착 완료.")

        new_processed_count = 0

        # 최신 릴스부터 순차 처리
        for p_idx, post_href in enumerate(posts, start=1):
            reel_url = f"https://www.instagram.com{post_href}"
            print(f"\n========================================")
            print(f"[{p_idx}/{len(posts)}] 🔍 최신 릴스 스캔 접속: {reel_url}")
            await page.goto(reel_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # ...more 클릭하여 본문 확장
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
            
            # 본문에서 No.XX 파싱 실패 시, 릴스 순서(34 - p_idx)로 상품 번호 산출
            product_no = p_match.group(1) if p_match else str(34 - p_idx + 1)

            product_link = f"https://6070.piella.shop/p/{product_no}"
            dm_msg_1 = f"안녕하세요! 요청하신 {product_no}번 상품 구매 링크입니다 💕\n{product_link}"
            dm_msg_2 = f"더 많은 상품은 여기서 확인하세요 👇\nhttps://6070.piella.shop"

            # 1. 댓글 아이콘 클릭하여 댓글 서랍 열기
            await page.evaluate("""
                () => {
                    const svg = document.querySelector('svg[aria-label="Comment"], svg[aria-label="댓글"]');
                    if (svg) {
                        let p = svg;
                        for (let i = 0; i < 4; i++) {
                            if (p.parentElement) p = p.parentElement;
                        }
                        p.click();
                    }
                }
            """)
            await asyncio.sleep(2)

            # 2. 딥 스크롤 20회 수행
            for _ in range(20):
                await page.evaluate("""
                    () => {
                        const divs = document.querySelectorAll('div');
                        for (const d of divs) {
                            if (d.scrollHeight > d.clientHeight && d.clientHeight > 150) {
                                d.scrollTop = d.scrollHeight;
                            }
                        }
                        const btns = Array.from(document.querySelectorAll('span, button, div[role="button"]')).filter(el => {
                            const t = el.textContent.trim();
                            return t.includes('답글') || t.includes('더 보기') || t.includes('View replies') || t.includes('Load more');
                        });
                        for (const b of btns.slice(0, 10)) {
                            try { b.click(); } catch(e) {}
                        }
                    }
                """)
                await asyncio.sleep(0.8)

            # 3. 미응답 사용자 수집
            unreplied_users = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    const results = [];
                    const blacklist = ['legal', 'privacy', 'terms', 'cookies', 'popular', 'weblite', 'accounts', 'meta', 'about', 'help', 'api', 'jobs', 'explore', 'momdad_style', 'direct', 'directinbox'];
                    
                    for (const a of links) {
                        const href = a.getAttribute('href');
                        const text = a.textContent.trim();
                        
                        if (href && href.startsWith('/') && !href.includes('p/') && !href.includes('reels/') && text.length > 1) {
                            const uname = href.replace(/\//g, '').trim();
                            if (!/^[a-zA-Z0-9._]+$/.test(uname)) continue;
                            if (blacklist.some(b => uname.toLowerCase().includes(b))) continue;
                            if (uname.length < 3) continue;

                            let container = a;
                            for (let i = 0; i < 6; i++) {
                                if (container.parentElement) container = container.parentElement;
                            }
                            
                            const textContent = container.textContent;
                            const alreadyReplied = textContent.includes('DM으로 링크 보내드렸습니다');
                            
                            if (!alreadyReplied) {
                                if (!results.some(r => r.username === uname)) {
                                    results.push({ username: uname, href: href, display_name: text });
                                }
                            }
                        }
                    }
                    return results;
                }
            """)

            new_unreplied = [u for u in unreplied_users if f"{post_href}:{u['username']}" not in processed_set]

            if not new_unreplied:
                print(f"  ✅ 게시물 [{p_idx}/{len(posts)}] {reel_url}: 미응답 댓글 없음 (완료)")
                continue

            print(f"  🔥 [{reel_url}] 신규 미응답 작성자 {len(new_unreplied)}명 발견! {[u['username'] for u in new_unreplied]}")

            for u_idx, uinfo in enumerate(new_unreplied, start=1):
                uname = uinfo['username']
                href = uinfo['href']
                ckpt_key = f"{post_href}:{uname}"

                print(f"\n  👉 [최신 릴스 {p_idx} - {u_idx}/{len(new_unreplied)}] @{uname} 님 소급 처리 중 (상품번호: {product_no})...")

                # A. 대댓글 작성
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
                            await asyncio.sleep(2.5)
                            print(f"    ✅ 💬 @{uname} 대댓글 작성 완료!")

                # B. 프로필 팔로우
                profile_url = f"https://www.instagram.com{href}"
                await page.goto(profile_url, wait_until="domcontentloaded")
                await asyncio.sleep(2)

                follow_btn = page.locator("button:has-text('Follow'), button:has-text('팔로우')").first
                try:
                    if await follow_btn.is_visible():
                        await follow_btn.click()
                        await asyncio.sleep(1.5)
                        print(f"    ✅ ➕ @{uname} 팔로우 완료!")
                except: pass

                # C. DM 이동 & 메시지 2개 분리 전송
                await page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
                await asyncio.sleep(3)

                compose_btn = page.locator("svg[aria-label='새 메시지'], svg[aria-label='New message'], a[href='/direct/new/']").first
                if await compose_btn.is_visible():
                    await compose_btn.click()
                    await asyncio.sleep(2)

                await page.evaluate(f"""
                    () => {{
                        const inp = document.querySelector('div[role="dialog"] input, input[name="queryBox"]');
                        if (inp) {{
                            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                            nativeSetter.call(inp, '{uname}');
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}
                """)
                await asyncio.sleep(2)

                await page.evaluate(f"""
                    async () => {{
                        const dialog = document.querySelector('div[role="dialog"]');
                        if (!dialog) return;
                        const opt = dialog.querySelector('div[role="option"]');
                        if (opt) opt.click();
                        await new Promise(r => setTimeout(r, 1000));
                        const chatBtn = Array.from(dialog.querySelectorAll('div[role="button"], button')).find(el => {{
                            const txt = el.textContent.trim();
                            return (txt === 'Chat' || txt === 'Next' || txt === '채팅' || txt === '다음') && el.offsetWidth > 0;
                        }});
                        if (chatBtn) chatBtn.click();
                    }}
                """)
                await asyncio.sleep(2.5)

                try:
                    dm_input = page.locator('div[aria-label*="Message"], div[aria-label*="메시지"], div[contenteditable="true"]').first
                    await dm_input.wait_for(timeout=5000)
                    await dm_input.click()
                    await asyncio.sleep(0.5)
                    await page.keyboard.type(dm_msg_1)
                    await asyncio.sleep(1)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(2)

                    await dm_input.click()
                    await asyncio.sleep(0.5)
                    await page.keyboard.type(dm_msg_2)
                    await asyncio.sleep(1)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(2)
                    print(f"    ✅ 📩 @{uname} DM 2개 발송 완료!")
                except Exception as e_dm:
                    print(f"    ⚠️ DM 발송 예외: {e_dm}")

                # 체크포인트 저장
                processed_set.add(ckpt_key)
                checkpoint["processed"] = list(processed_set)
                save_checkpoint(checkpoint)
                
                new_processed_count += 1
                print(f"  ✨ [최신 릴스 처리 누적 완결: {len(processed_set)}건]")
                
                # 🛡️ 계정 차단 방지를 위한 자연스러운 휴식 시간 (15~25초)
                safe_delay = random.uniform(15, 25)
                print(f"  🛡️ [계정 보호] 다음 발송 전 {safe_delay:.1f}초 안전 휴식...")
                await asyncio.sleep(safe_delay)


        print(f"\n🎉🎉 [완전 완결] 최신 릴스 소급 완료 총 {new_processed_count}건!")
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_newest_reels_scan())
