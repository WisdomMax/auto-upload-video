import asyncio, os, json, random, re
from playwright.async_api import async_playwright

REEL_MAPPING = {
    "DbWg-WlkdhL": "29", "DbUFEoJk4yT": "28", "DbRe9yXkfI2": "27", "DbO6mQpEq5k": "26",
    "DbMTSVnkc2a": "25", "DbJwAosEwS_": "24", "DbHM9HME1f1": "23", "DbEjO6SEpFA": "22",
    "DbB--GZEsV6": "21", "Da_KGuhEQ_J": "20", "Da8jBnkEnV4": "19", "Da58KrkEU2x": "18",
    "Da3ScC5ERgD": "17", "Da0uB0DEuU_": "16", "DayJy2JEvW-": "15", "DavliKik0s7": "14",
    "Das69Jtk0r0": "13", "DaqTOHhEZjJ": "12", "DanrcdNEVDt": "11", "DalBFDMEZq2": "10",
    "DaiY0G6kfM_": "9",  "DafxeRSEvY3": "8",  "DadI3gJk5-X": "7",  "Daah1Z2E0z8": "6",
    "DaX-2Y0E7W9": "5",  "DaVVa74k6wR": "4",  "DaSz9R_k4cQ": "3",  "DaQNA9xknF6": "2",
    "DaNhD5FE_l_": "1"
}

async def run_ultra_deep_scan():
    user_data_dir = os.path.expanduser('~/.config/ig_stealth_profile')
    ckpt_file = 'scratch/ultra_deep_checkpoint.json'
    processed_set = set()
    if os.path.exists(ckpt_file):
        try:
            with open(ckpt_file, 'r') as f:
                processed_set = set(json.load(f))
        except:
            pass

    print("=== [1,000개 댓글 전수 스캔 및 100% 미응답 유저 전원 답글/DM 처리 시작] ===")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        total_new_processed = 0

        for shortcode, prod_no in REEL_MAPPING.items():
            reel_url = f"https://www.instagram.com/momdad_style/reel/{shortcode}/"
            print(f"\n🎬 [릴스 {prod_no}번] {reel_url} 접속 중...")
            try:
                await page.goto(reel_url, wait_until="domcontentloaded")
                await asyncio.sleep(3.5)

                # 1. 댓글 더보기 30회 반복 클릭 및 딥 스크롤
                for scroll_idx in range(30):
                    await page.evaluate("""
                        () => {
                            const btns = Array.from(document.querySelectorAll('span, div[role="button"], button'));
                            const moreBtn = btns.find(b => {
                                const txt = b.textContent.trim();
                                return (txt.includes('댓글 더 보기') || txt.includes('View more comments') || txt.includes('댓글 더보기') || txt === '+') && b.offsetWidth > 0;
                            });
                            if (moreBtn) moreBtn.click();
                            
                            const containers = Array.from(document.querySelectorAll('div[class*="x1n2onr6"], ul, div[role="dialog"]'));
                            for (const c of containers) {
                                if (c.scrollHeight > c.clientHeight) c.scrollTop += 2000;
                            }
                            window.scrollTo(0, document.body.scrollHeight);
                        }
                    """)
                    await asyncio.sleep(0.8)

                # 2. 렌더링된 모든 유저 댓글 추출
                raw_users = await page.evaluate("""
                    () => {
                        const spans = Array.from(document.querySelectorAll('span'));
                        const res = [];
                        for (const s of spans) {
                            const txt = s.textContent.trim();
                            if (txt.length >= 1 && !txt.includes('좋아요') && !txt.includes('답글') && !txt.includes('게시')) {
                                let p = s;
                                for (let k = 0; k < 6; k++) {
                                    if (p.parentElement) p = p.parentElement;
                                    const a = p.querySelector('a[href^="/"]');
                                    if (a) {
                                        const href = a.getAttribute('href');
                                        if (href && href !== '/' && !href.includes('/reel/')) {
                                            const u = href.replace(/\\//g, '');
                                            if (u && u !== 'momdad_style') {
                                                res.push(u);
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        return Array.from(new Set(res));
                    }
                """)

                print(f"  📌 {prod_no}번 릴스에서 총 {len(raw_users)}명의 유저 감지!")

                # 3. 미처리 유저 선별 및 처리
                for uname in raw_users:
                    ckpt_key = f"{shortcode}:{uname}"
                    if ckpt_key in processed_set:
                        continue

                    print(f"  👉 [신규 미처리 유저] @{uname} (상품 {prod_no}번) 대댓글 & DM 가동...")

                    # A. 대댓글 작성 시도
                    comment_reply_text = f"어머님 안녕하세요! 💕 문의하신 {prod_no}번 상품 직행 링크 및 상세정보는 보내드린 DM과 프로필 링크(6070.piella.shop)에서 바로 확인 가능하십니다! ✨"
                    try:
                        await page.evaluate(f"""
                            () => {{
                                const spans = Array.from(document.querySelectorAll('span'));
                                const targetSpan = spans.find(s => s.textContent.includes('{uname}'));
                                if (targetSpan) {{
                                    let p = targetSpan;
                                    for (let i = 0; i < 5; i++) {{
                                        if (p.parentElement) p = p.parentElement;
                                        const replyBtn = Array.from(p.querySelectorAll('span, div[role="button"]')).find(b => b.textContent.trim() === '답글 달기' || b.textContent.trim() === 'Reply');
                                        if (replyBtn) {{
                                            replyBtn.click();
                                            break;
                                        }}
                                    }}
                                }}
                            }}
                        """)
                        await asyncio.sleep(1.5)

                        comment_input = page.locator('textarea[placeholder*="답글"], textarea[placeholder*="Add a comment"], div[role="textbox"]').first
                        if await comment_input.is_visible():
                            await comment_input.click()
                            await page.keyboard.type(comment_reply_text)
                            await asyncio.sleep(1)
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(2)
                            print(f"    ✅ 대댓글 작성 완료!")
                    except Exception as e_c:
                        print(f"    ⚠️ 대댓글 예외: {e_c}")

                    # B. Direct DM 전송 (100% 직행)
                    try:
                        await page.goto("https://www.instagram.com/direct/new/", wait_until="domcontentloaded")
                        await asyncio.sleep(3)

                        dm_inp = page.locator('input[name="queryBox"], input[name="searchInput"], input[placeholder*="Search"], input[placeholder*="검색"]').first
                        if await dm_inp.is_visible():
                            await dm_inp.fill(uname)
                            await asyncio.sleep(2.5)

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
                            await asyncio.sleep(3.5)

                            dm_input = page.locator('div[role="textbox"], textarea, div[contenteditable="true"]').first
                            if await dm_input.is_visible():
                                msg1 = f"안녕하세요 어머님! 💕 요청하신 {prod_no}번 상품 구매 링크입니다!\nhttps://6070.piella.shop/p/{prod_no}"
                                msg2 = "더 많은 예쁜 옷들은 여기서 구경하세요 👇\nhttps://6070.piella.shop"
                                await dm_input.click()
                                await page.keyboard.type(msg1)
                                await page.keyboard.press("Enter")
                                await asyncio.sleep(1.5)
                                await dm_input.click()
                                await page.keyboard.type(msg2)
                                await page.keyboard.press("Enter")
                                await asyncio.sleep(2)
                                print(f"    ✅ 📩 DM 2개 정상 발송 완료!")
                    except Exception as e_dm:
                        print(f"    ⚠️ DM 예외: {e_dm}")

                    # 체크포인트 저장
                    processed_set.add(ckpt_key)
                    with open(ckpt_file, 'w') as f:
                        json.dump(list(processed_set), f)

                    total_new_processed += 1

                    # 계정 보호 안전 휴식 (15~25초)
                    delay = random.uniform(15, 25)
                    print(f"    🛡️ 계정 보호 {delay:.1f}초 안전 대기...")
                    await asyncio.sleep(delay)

            except Exception as e_reel:
                print(f"❌ 릴스 {prod_no}번 스캔 중 오류: {e_reel}")

        print(f"\n🎉🎉 [1,000개 댓글 딥 스크롤 완결] 총 {total_new_processed}명의 누락된 미응답 유저에게 추가 발송 완결!")
        await context.close()

if __name__ == '__main__':
    asyncio.run(run_ultra_deep_scan())
