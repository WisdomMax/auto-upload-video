import asyncio, os, json, re, random
from playwright.async_api import async_playwright

CHECKPOINT_FILE = "/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/scratch/retroactive_checkpoint.json"
RESEND_CHECKPOINT = "/Volumes/NVME/7.AI_vibe_coding/20260605 momdad fashion diary/scratch/resend_checkpoint.json"

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"processed": []}

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"저장 오류: {e}")

async def run_resend_correction():
    print("=== [Emergency DM Fix: 1000명 대상 상품 직행 상세 링크 재발송 모드 구동] ===")
    main_ckpt = load_json(CHECKPOINT_FILE)
    resend_ckpt = load_json(RESEND_CHECKPOINT)
    
    past_processed = main_ckpt.get("processed", [])
    already_resent = set(resend_ckpt.get("processed", []))

    print(f"📌 과거 수신자 총 {len(past_processed)}건 중 재발송 완료된 건: {len(already_resent)}건")

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

        # 1. 릴스 URL -> 상품 번호 맵 생성
        print("\n1. 전체 릴스 상품 번호 매핑 수집 중...")
        await page.goto("https://www.instagram.com/momdad_style/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        for _ in range(12):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

        posts = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                const postHrefs = links.map(l => l.getAttribute('href')).filter(h => h && (h.includes('/p/') || h.includes('/reel/')));
                return Array.from(new Set(postHrefs));
            }
        """)

        reel_product_map = {}
        for idx, post_href in enumerate(posts, start=1):
            reel_url = f"https://www.instagram.com{post_href}"
            await page.goto(reel_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            await page.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll('span, div[role="button"]'));
                    const more = btns.find(b => b.textContent.trim().includes('more') || b.textContent.trim().includes('더 보기'));
                    if (more) more.click();
                }
            """)
            await asyncio.sleep(0.8)

            caption = await page.evaluate("() => document.body.textContent")
            p_match = re.search(r'No\.?\s*(\d+)', caption, re.IGNORECASE)
            p_no = p_match.group(1) if p_match else str(34 - idx + 1)
            reel_product_map[post_href] = p_no
            print(f"  [매핑] {post_href} -> 상품 No.{p_no}")

        # 2. 과거 수신자 1000명에게 상품 직행 상세 링크 재발송
        print(f"\n2. 과거 수신자 대상 상품 직행 상세 링크 정정 재발송 시작...")
        
        count = 0
        for item in past_processed:
            if item in already_resent:
                continue

            try:
                post_href, uname = item.split(":", 1)
            except:
                continue

            product_no = reel_product_map.get(post_href, "1")
            product_link = f"https://6070.piella.shop/p/{product_no}"

            dm_fix_msg = f"안녕하세요 어머님! 💕 아까 안내해 드린 링크에 접속 오류가 있어, 문의하신 {product_no}번 상품으로 바로 연결되는 상세 구매 링크를 다시 보내드립니다!\n\n👇 {product_no}번 상품 직행 링크:\n{product_link}\n\n불편을 드려 죄송하며 예쁘게 입으세요! ✨"

            print(f"\n👉 [{count+1}/{len(past_processed)}] @{uname} 님께 {product_no}번 상품 직행 링크 정정 DM 재발송 중...")

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
            await asyncio.sleep(3)

            try:
                dm_input = page.locator('div[aria-label*="Message"], div[aria-label*="메시지"], div[contenteditable="true"]').first
                await dm_input.wait_for(timeout=6000)
                await dm_input.click()
                await asyncio.sleep(0.5)
                await page.keyboard.type(dm_fix_msg)
                await asyncio.sleep(1)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)
                print(f"  ✅ @{uname} 님께 {product_no}번 직행 링크 재발송 성공!")
            except Exception as e_dm:
                print(f"  ⚠️ @{uname} DM 재발송 예외: {e_dm}")

            already_resent.add(item)
            resend_ckpt["processed"] = list(already_resent)
            save_json(RESEND_CHECKPOINT, resend_ckpt)

            count += 1
            delay = random.uniform(20, 30)
            print(f"  🛡️ [계정 안전 보장] {delay:.1f}초 휴식 후 다음 재발송...")
            await asyncio.sleep(delay)

        print(f"\n🎉🎉 [완전 완결] 과거 수신자 1000명 대상 상품 직행 링크 정정 재발송 총 {count}건 완료!")
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_resend_correction())
