import os
import json
import logging
import database

logger = logging.getLogger("catalog_builder")

def build_catalog():
    logger.info("Starting static catalog page rebuild...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    
    # 1. DB에서 전체 상품 중 쿠팡 URL이 비어있지 않은 상품만 필터링하여 조회
    raw_items = database.get_items()
    items = [it for it in raw_items if it.get("coupang_url") and it.get("coupang_url").strip() != ""]
    
    # [배포 무결성 검증 가드]
    # 연동된 상품이 0개이거나 최소 기준(예: 3개) 미만인 경우, 비정상적인 데이터 초기화로 보고 빌드를 강제 중단
    # (외국의 빈 템플릿이 배포되어 실서비스 옷 카탈로그가 백지화되는 대형 장애 방지)
    if len(items) < 3:
        raise ValueError(
            f"❌ [배포 무결성 검증 실패] 쿠팡 URL이 연동된 상품이 {len(items)}개입니다. "
            "비정상적인 데이터 유실로 판단되어 카탈로그 빌드 및 배포가 차단되었습니다. DB 복구를 확인해 주세요."
        )
    
    # 썸네일 폴더를 dist/static/thumbnails/ 로 복사하여 Cloudflare Pages 배포에 포함시킴
    src_thumb_dir = os.path.join(base_dir, "static", "thumbnails")
    dist_thumb_dir = os.path.join(dist_dir, "static", "thumbnails")
    if os.path.exists(src_thumb_dir):
        import shutil
        dist_static_dir = os.path.join(dist_dir, "static")
        os.makedirs(dist_static_dir, exist_ok=True)
        if os.path.exists(dist_thumb_dir):
            shutil.rmtree(dist_thumb_dir)
        shutil.copytree(src_thumb_dir, dist_thumb_dir)
        logger.info("Thumbnails successfully copied to dist/static/thumbnails")
    
    products_data = []
    for item in items:
        # product_code가 없는 구버전 아이템 하위 호환
        code = item.get("product_code") or f"T{item['product_no']:05d}"
        
        products_data.append({
            "id": item["id"],
            "product_no": item["product_no"],
            "product_code": code,
            "title": item["title"],
            "description": item["description"],
            "coupang_url": item["coupang_url"],
            "short_url": item.get("short_url") or item["coupang_url"] or "#",
            "thumbnail_url": f"/static/thumbnails/{code}.webp"
        })
        
    # products.json 갱신
    products_path = os.path.join(dist_dir, "products.json")
    with open(products_path, "w", encoding="utf-8") as f:
        json.dump(products_data, f, ensure_ascii=False, indent=2)
        
    # 2. dist/index.html 템플릿 갱신
    html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>MOMDAD FASHION DIARY — EDITORIAL COLLECTION</title>
    <!-- Google Fonts: Elegant Serif & Minimalist Sans -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Noto+Serif+KR:wght@200;300;400;600&family=Inter:wght@200;300;400;500&display=swap" rel="stylesheet">
    <!-- FontAwesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --color-bg: #0a0a0a;          /* Matte Jet Black */
            --color-surface: #121212;     /* Dark Gallery Charcoal */
            --color-border: rgba(255, 255, 255, 0.05); /* Thin Frame Line */
            --color-text-primary: #e5e5e5;  /* Editorial Off-white */
            --color-text-secondary: #8a8a8a;/* Silver Dust */
            --color-gold: #bca374;        /* Antique Bronze Gold */
            --font-serif: 'Cormorant Garamond', 'Noto Serif KR', serif;
            --font-sans: 'Inter', sans-serif;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background-color: var(--color-bg);
            font-family: var(--font-sans);
            color: var(--color-text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-bottom: 100px;
            letter-spacing: -0.01em;
            word-break: keep-all;
        }

        .container {
            width: 100%;
            max-width: 1200px;
            padding: 0 24px;
            display: flex;
            flex-direction: column;
            gap: 48px;
        }

        /* Top Disclaimer Banner - Slim, minimal, gold accent line */
        .disclaimer-banner {
            width: 100%;
            background: #111111;
            border-bottom: 1px solid rgba(188, 163, 116, 0.3);
            color: #ffffff;               /* Clear white for legal compliance */
            padding: 14px 16px;
            font-size: 0.88rem;            /* Significantly enlarged */
            text-align: center;
            font-weight: 500;             /* Increased weight */
            letter-spacing: 0.03em;
            position: relative;
        }
        .disclaimer-banner::before {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 100%;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--color-gold), transparent);
        }
        .disclaimer-banner i {
            color: var(--color-gold);
            margin-right: 4px;
        }

        /* Editorial Header */
        header {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 64px 0 24px 0;
            text-align: center;
        }
        header .brand-subtitle {
            font-family: var(--font-sans);
            font-size: 0.62rem;
            font-weight: 300;
            text-transform: uppercase;
            letter-spacing: 0.4em;
            color: var(--color-gold);
        }
        header h1 {
            font-family: var(--font-serif);
            font-size: 2.2rem;
            font-weight: 300;
            letter-spacing: 0.05em;
            color: var(--color-text-primary);
        }
        header h1 span {
            font-weight: 300;
            font-style: italic;
            color: var(--color-gold);
        }
        header .header-divider {
            width: 30px;
            height: 1px;
            background-color: var(--color-gold);
            margin-top: 12px;
            opacity: 0.5;
        }

        /* Search Section */
        .search-container {
            width: 100%;
            max-width: 500px;
            margin: 0 auto;
            position: relative;
        }
        
        .search-label-text {
            text-align: center;
            margin-bottom: 18px;
            color: #ffffff;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .search-label-text .main-instruction {
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: -0.01em;
        }
        .search-label-text .main-instruction .highlight {
            color: #ffe600;
            text-decoration: underline;
            font-weight: 700;
        }
        .search-label-text .sub-instruction {
            font-size: 0.95rem;
            color: #b0b0b0;
            font-weight: 500;
            letter-spacing: 0.02em;
        }
        .search-label-text .sub-instruction .example-num {
            color: #ffe600;
            font-weight: 700;
        }
        .search-label-text .sub-instruction .example-code {
            color: var(--color-gold);
            font-weight: 600;
        }
        
        /* Floating Sticky mode (Hidden state by default) */
        .search-container.floating {
            position: fixed;
            top: 16px;
            left: 50%;
            transform: translateX(-50%) translateY(-120%);
            width: calc(100% - 48px);
            max-width: 500px;
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.4s ease;
        }
        
        .search-container.floating input {
            background: #ffffff !important;
            border-color: var(--color-gold) !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8) !important;
            color: #111111 !important;
        }

        /* Floating Sticky mode (Visible state) */
        .search-container.floating.visible {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
            pointer-events: auto;
        }

        .search-container input {
            width: 100%;
            padding: 16px 20px 16px 54px;
            background: #ffffff;
            border: 3px solid var(--color-gold);
            border-radius: 8px;
            color: #111111;
            font-size: 1.1rem;
            font-family: var(--font-sans);
            font-weight: 600;
            outline: none;
            letter-spacing: 0.02em;
            transition: all 0.3s ease;
            text-align: left;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
        }
        .search-container input::placeholder {
            color: #666666;
            opacity: 1;
            font-weight: 500;
        }
        .search-container input:focus {
            border-color: #ffffff;
            box-shadow: 0 0 15px rgba(188, 163, 116, 0.4);
            background: #fdfdfd;
        }
        .search-container i {
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: #333333;
            font-size: 1.3rem;
            pointer-events: none;
            z-index: 5;
        }
        @media (max-width: 480px) {
            .container {
                padding: 0 16px;
                gap: 28px;
            }
            header {
                padding: 36px 0 16px 0;
                gap: 8px;
            }
            header h1 {
                font-size: 1.7rem;
                white-space: nowrap;
            }
            header .brand-subtitle {
                letter-spacing: 0.25em;
            }
            .search-label-text .main-instruction {
                font-size: 1.15rem !important;
            }
            .search-label-text .sub-instruction {
                font-size: 0.88rem !important;
            }
            .search-container input {
                padding: 14px 16px 14px 44px;
                font-size: 0.95rem;
            }
            .search-container i {
                left: 16px;
                font-size: 1.1rem;
            }
            .catalog-grid {
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 16px !important;
            }
            .product-code-display {
                font-size: 1.4rem !important;
                letter-spacing: 0.12em !important;
            }
            .product-info {
                padding: 10px 8px !important;
            }
        }

        /* Grid Layout */
        .catalog-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 40px;
            width: 100%;
        }

        @media (min-width: 576px) {
            .catalog-grid {
                grid-template-columns: repeat(2, 1fr);
                gap: 28px;
            }
        }

        @media (min-width: 992px) {
            .catalog-grid {
                grid-template-columns: repeat(3, 1fr);
                gap: 36px;
            }
        }

        @media (min-width: 1200px) {
            .catalog-grid {
                grid-template-columns: repeat(4, 1fr);
                gap: 40px;
            }
        }

        /* Product Card */
        .product-card {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            text-decoration: none;
            position: relative;
            transition: transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94), border-color 0.4s ease, box-shadow 0.4s ease;
        }
        .product-card:hover {
            transform: translateY(-4px);
            border-color: rgba(188, 163, 116, 0.3);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6);
        }

        /* Thumbnail Wrapper with Editorial Aspect Ratio (9:16) */
        .thumb-wrapper {
            width: 100%;
            aspect-ratio: 9 / 16;
            background: linear-gradient(135deg, #151515 0%, #0c0c0c 100%);
            overflow: hidden;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .thumb-wrapper::before {
            content: '\\f03e'; /* FontAwesome Image placeholder icon */
            font-family: 'Font Awesome 6 Free';
            font-weight: 900;
            font-size: 2rem;
            color: #1e1e1e;
            position: absolute;
            z-index: 1;
            transition: color 0.4s ease;
        }
        .product-card:hover .thumb-wrapper::before {
            color: #262626;
        }
        
        /* Model Code inside placeholder */
        .placeholder-code {
            position: absolute;
            font-family: var(--font-serif);
            font-size: 1.6rem;
            font-weight: 300;
            color: rgba(188, 163, 116, 0.12);
            letter-spacing: 0.1em;
            z-index: 2;
            pointer-events: none;
            text-transform: uppercase;
        }

        .thumb-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            position: relative;
            z-index: 3;
            filter: grayscale(12%) contrast(1.03);
            transition: transform 0.8s cubic-bezier(0.25, 1, 0.5, 1), filter 0.8s ease;
        }
        
        /* Hide broken image elements smoothly */
        .thumb-wrapper img.error {
            display: none !important;
            opacity: 0;
            z-index: 0;
        }

        .product-card:hover .thumb-wrapper img {
            transform: scale(1.03);
            filter: grayscale(0%) contrast(1);
        }

        /* Info Section - Minimalist Display for code only */
        .product-info {
            padding: 16px 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #0d0d0d;
            border-top: 1px solid var(--color-border);
        }
        
        .product-code-display {
            font-family: var(--font-serif);
            font-size: 1.8rem;             /* 1.45rem -> 1.8rem으로 크게 노출 */
            font-weight: 300;
            color: var(--color-gold);
            letter-spacing: 0.18em;        /* 자간을 넓혀 에디토리얼 감성 강화 */
            text-transform: uppercase;
            transition: color 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94), letter-spacing 0.4s ease;
        }
        
        .product-card:hover .product-code-display {
            color: #ffffff;
            letter-spacing: 0.22em;       /* 호버 시 글자 자간이 미세하게 늘어나는 고급스러운 효과 */
            transform: scale(1.02);       /* 미세 호버 효과 */
        }

        /* Empty search state */
        .search-empty {
            grid-column: 1 / -1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 8rem 2rem;
            color: var(--color-text-secondary);
            text-align: center;
            gap: 16px;
            font-family: var(--font-serif);
        }
        .search-empty i {
            font-size: 2rem;
            color: var(--color-gold);
            opacity: 0.6;
        }
        .search-empty p {
            font-size: 1rem;
            font-weight: 300;
            letter-spacing: 0.05em;
        }
    </style>
</head>
<body>
    <!-- Top banner -->
    <div class="disclaimer-banner">
        <i class="fa-solid fa-circle-info"></i> 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
    </div>

    <!-- Floating Search Bar -->
    <div class="search-container floating" id="search-floating-container">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input type="text" id="search-input-floating" placeholder="상품 번호 또는 이름 검색">
    </div>

    <div class="container">
        <header>
            <span class="brand-subtitle">Curated Senior Lookbook Collection</span>
            <h1>엄마아빠 <span>패션다이어리</span></h1>
            <div class="header-divider"></div>
        </header>

        <!-- Search Bar -->
        <div class="search-label-text">
            <div class="main-instruction"><i class="fa-solid fa-magnifying-glass"></i> 찾으시는 <span class="highlight">상품 번호(숫자)</span>를 입력하세요</div>
            <div class="sub-instruction">예시: <span class="example-num">25</span> 또는 <span class="example-code">T00025</span></div>
        </div>
        <div class="search-container" id="search-original-container">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input type="text" id="search-input" placeholder="상품 번호 또는 이름 검색">
        </div>

        <!-- Cards Grid -->
        <div class="catalog-grid" id="catalog-grid">
            <!-- Dynamically Rendered -->
        </div>
    </div>

    <script>
        const products = __PRODUCTS_PLACEHOLDER__;
        const grid = document.getElementById('catalog-grid');
        const searchInput = document.getElementById('search-input');

        function renderProducts(filterText = '') {
            grid.innerHTML = '';
            
            const filtered = products.filter(p => {
                const filterTextClean = filterText.toLowerCase().trim();
                if (!filterTextClean) return true;

                // 1. 입력값이 오직 숫자로만 구성되었는지 검사 (예: "21")
                const isOnlyDigits = /^[0-9]+$/.test(filterTextClean);

                // 2. 입력값이 상품 코드 패턴(T로 시작하고 뒤에 숫자가 붙은 패턴)인지 검사 (예: "t21", "t00021")
                const isProductCodePattern = /^t[0-9]+$/.test(filterTextClean);

                if (isOnlyDigits) {
                    return p.product_no === parseInt(filterTextClean, 10);
                }

                if (isProductCodePattern) {
                    const cleanNum = parseInt(filterTextClean.replace(/[^0-9]/g, ''), 10);
                    return p.product_no === cleanNum || p.product_code.toLowerCase().includes(filterTextClean);
                }

                // 3. 일반 텍스트 검색 (타이틀 및 설명, 코드 포함 검색)
                const searchStr = (p.title + ' ' + p.product_code + ' ' + p.description).toLowerCase();
                return searchStr.includes(filterTextClean);
            });

            if (filtered.length === 0) {
                grid.innerHTML = `
                    <div class="search-empty">
                        <i class="fa-regular fa-face-frown-open"></i>
                        <p>검색 결과에 해당하는 룩북을 찾을 수 없습니다.</p>
                    </div>
                `;
                return;
            }

            filtered.forEach(p => {
                const card = document.createElement('a');
                card.className = 'product-card';
                card.href = p.short_url;
                card.target = '_blank';
                
                const productCode = p.product_code || 'ITEM';
                
                card.innerHTML = `
                    <div class="thumb-wrapper">
                        <span class="placeholder-code">${productCode}</span>
                        <img src="${p.thumbnail_url || ''}" alt="" 
                             onerror="
                                if (!this.classList.contains('tried-1')) {
                                    this.classList.add('tried-1');
                                    this.src = './static/thumbnails/${productCode}.webp';
                                } else if (!this.classList.contains('tried-2')) {
                                    this.classList.add('tried-2');
                                    this.src = '../static/thumbnails/${productCode}.webp';
                                } else {
                                    this.classList.add('error');
                                }
                             ">
                    </div>
                    <div class="product-info">
                        <span class="product-code-display">${productCode}</span>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        const originalInput = document.getElementById('search-input');
        const floatingInput = document.getElementById('search-input-floating');
        const originalContainer = document.getElementById('search-original-container');
        const floatingContainer = document.getElementById('search-floating-container');

        // 두 입력창 값 동기화 및 렌더링 호출
        originalInput.addEventListener('input', (e) => {
            const val = e.target.value;
            floatingInput.value = val;
            renderProducts(val);
        });

        floatingInput.addEventListener('input', (e) => {
            const val = e.target.value;
            originalInput.value = val;
            renderProducts(val);
        });

        // 스크롤 감지 플로팅 검색창 로직
        let lastScrollY = window.scrollY;

        window.addEventListener('scroll', () => {
            const currentScrollY = window.scrollY;
            
            // 원래 검색창 컨테이너의 하단 위치를 스크롤 기준점으로 계산
            const originalBottom = originalContainer.getBoundingClientRect().bottom + window.scrollY;
            
            if (currentScrollY <= originalBottom) {
                // 원래 검색창이 화면 내에 머물 때는 플로팅 노출 안함
                floatingContainer.classList.remove('visible');
                lastScrollY = currentScrollY;
                return;
            }
            
            if (currentScrollY < lastScrollY) {
                // 위로 스크롤할 때 플로팅 검색창 슥 출현
                floatingContainer.classList.add('visible');
            } else {
                // 아래로 스크롤할 때는 스르륵 퇴장
                floatingContainer.classList.remove('visible');
            }
            
            lastScrollY = currentScrollY;
        }, { passive: true });

        // 초기화
        renderProducts();
    </script>
</body>
</html>"""

    final_html = html_template.replace("__PRODUCTS_PLACEHOLDER__", json.dumps(products_data, ensure_ascii=False))
    
    html_path = os.path.join(dist_dir, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    # 3. 개별 상품 리다이렉트 페이지(dist/p/{product_no}/index.html) 생성
    p_dir = os.path.join(dist_dir, "p")
    os.makedirs(p_dir, exist_ok=True)
    
    redirect_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>이동 중...</title>
    <meta http-equiv="refresh" content="0; url={target_url}">
    <script>window.location.href = "{target_url}";</script>
</head>
<body>
    잠시 후 상품 페이지로 이동합니다. 이동하지 않으면 <a href="{target_url}">여기</a>를 클릭하세요.
</body>
</html>"""

    for item in items:
        prod_no = item.get("product_no")
        if not prod_no:
            continue
            
        target_url = item.get("short_url") or item.get("coupang_url") or "#"
        if target_url == "#":
            continue
            
        prod_p_dir = os.path.join(p_dir, str(prod_no))
        os.makedirs(prod_p_dir, exist_ok=True)
        
        redirect_html = redirect_template.format(target_url=target_url)
        redirect_path = os.path.join(prod_p_dir, "index.html")
        with open(redirect_path, "w", encoding="utf-8") as f:
            f.write(redirect_html)
            
        logger.info(f"Created redirect page for product {prod_no} -> {target_url}")

    # 4. 정식 메타 검수용 개인정보 처리방침 (/privacy) 및 서비스 약관 (/terms) 생성
    _build_legal_pages(dist_dir)
        
    logger.info(f"Static catalog page rebuild completed. Registered products: {len(products_data)}")
    return True

def _build_legal_pages(dist_dir):
    # 1. privacy 페이지 생성
    privacy_dir = os.path.join(dist_dir, "privacy")
    os.makedirs(privacy_dir, exist_ok=True)
    privacy_html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>개인정보 처리방침 - 엄마아빠 패션다이어리</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background: #f9f9f9; }
        .card { background: #fff; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { color: #111; border-bottom: 2px solid #eee; padding-bottom: 10px; font-size: 24px; }
        h2 { color: #444; font-size: 18px; margin-top: 25px; }
        p, li { font-size: 15px; color: #555; }
        .footer { margin-top: 30px; font-size: 13px; color: #888; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h1>개인정보 처리방침</h1>
        <p>엄마아빠 패션다이어리(이하 '회사')는 이용자의 개인정보를 중요시하며, 「개인정보 보호법」 등 관련 법령을 준수하고 있습니다.</p>
        
        <h2>1. 수집하는 개인정보 항목 및 목적</h2>
        <p>회사는 SNS 댓글 및 메시지 자동 응대 서비스를 제공하기 위해 최소한의 개인정보를 수집합니다.</p>
        <ul>
            <li><strong>수집 항목:</strong> 인스타그램/소셜 계정 아이디(Scoped ID), 프로필명, 댓글 텍스트 내용</li>
            <li><strong>이용 목적:</strong> 요청하신 상품 구매 링크(쿠팡 파트너스/카탈로그) 안내 및 1:1 메시지(DM) 발송</li>
        </ul>

        <h2>2. 개인정보의 보유 및 이용 기간</h2>
        <p>이용자의 개인정보는 서비스 제공 목적이 달성된 후 파기하거나, 관련 법령에 따라 일정 기간 안전하게 보관 후 파기됩니다.</p>

        <h2>3. 개인정보의 제3자 제공 및 위탁</h2>
        <p>회사는 이용자의 동의 없이 개인정보를 외부에 제공하지 않으며, 서비스 운영을 위해 필요한 경우에 한하여 최소한의 범위 내에서 위탁 관리합니다.</p>

        <h2>4. 이용자의 권리와 행사 방법</h2>
        <p>이용자는 언제든지 자신의 개인정보 조회, 수정, 삭제(파기)를 요청할 수 있으며, 관련 문의는 고객지원 채널을 통해 처리됩니다.</p>

        <div class="footer">
            <p>최종 수정일: 2026년 7월 29일 | 엄마아빠 패션다이어리</p>
        </div>
    </div>
</body>
</html>"""
    with open(os.path.join(privacy_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(privacy_html)

    # 2. terms 페이지 생성
    terms_dir = os.path.join(dist_dir, "terms")
    os.makedirs(terms_dir, exist_ok=True)
    terms_html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>서비스 이용약관 - 엄마아빠 패션다이어리</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background: #f9f9f9; }
        .card { background: #fff; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { color: #111; border-bottom: 2px solid #eee; padding-bottom: 10px; font-size: 24px; }
        h2 { color: #444; font-size: 18px; margin-top: 25px; }
        p, li { font-size: 15px; color: #555; }
        .footer { margin-top: 30px; font-size: 13px; color: #888; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h1>서비스 이용약관</h1>
        <p>본 약관은 엄마아빠 패션다이어리(이하 '서비스')가 제공하는 SNS 쇼핑 카탈로그 및 자동 안내 서비스의 이용조건 및 절차를 규정합니다.</p>
        
        <h2>1. 서비스의 목적 및 내용</h2>
        <p>본 서비스는 5060 중년층 패션 카탈로그 정보 및 쿠팡 파트너스 제휴 상품 단축 링크 안내를 목적으로 합니다.</p>

        <h2>2. 서비스의 제공 및 변경</h2>
        <p>서비스는 24시간 제공을 원칙으로 하며, 시스템 점검이나 기타 불가피한 사유가 있는 경우 일시 중단될 수 있습니다.</p>

        <h2>3. 제휴 마케팅 안내</h2>
        <p>본 서비스에서 제공되는 일부 링크는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.</p>

        <div class="footer">
            <p>최종 수정일: 2026년 7월 29일 | 엄마아빠 패션다이어리</p>
        </div>
    </div>
</body>
</html>"""
    with open(os.path.join(terms_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(terms_html)
    logger.info("Successfully created privacy and terms pages in dist/")
