// products.json은 git push 시 자동으로 최신화됨
const DATA_URL = './products.json';

async function loadProducts() {
  const loading = document.getElementById('loading');
  const emptyState = document.getElementById('empty-state');
  const grid = document.getElementById('product-grid');
  const updatedAt = document.getElementById('updated-at');

  try {
    const res = await fetch(DATA_URL + '?t=' + Date.now());
    if (!res.ok) throw new Error('fetch failed');
    const data = await res.json();

    loading.style.display = 'none';

    if (data.updated_at) {
      const d = new Date(data.updated_at);
      updatedAt.textContent = '업데이트: ' + d.toLocaleDateString('ko-KR', {
        year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    }

    const products = data.products || [];

    if (products.length === 0) {
      emptyState.style.display = 'block';
      return;
    }

    grid.style.display = 'grid';
    grid.innerHTML = products.map((p, i) => renderCard(p, i)).join('');

  } catch (err) {
    loading.style.display = 'none';
    emptyState.style.display = 'block';
    console.error('상품 로드 실패:', err);
  }
}

function renderCard(p, index) {
  const labels = ['NEW', 'HOT', 'PICK', '추천', 'BEST'];
  const badge = labels[index % labels.length];

  // 미디어 영역
  let mediaHtml = '';
  if (p.video_url) {
    mediaHtml = `
      <video src="${escHtml(p.video_url)}" 
             muted loop playsinline preload="metadata"
             onmouseenter="this.play()" onmouseleave="this.pause()">
      </video>`;
  } else if (p.thumbnail_url) {
    mediaHtml = `<img src="${escHtml(p.thumbnail_url)}" alt="${escHtml(p.name)}" loading="lazy" />`;
  } else {
    mediaHtml = `<div class="card-media-placeholder">👗</div>`;
  }

  const link = p.short_url || p.coupang_url || '#';

  return `
    <article class="product-card">
      <div class="card-media">
        ${mediaHtml}
        <span class="card-badge">${badge}</span>
      </div>
      <div class="card-body">
        <h3 class="card-name">${escHtml(p.name)}</h3>
        ${p.description ? `<p class="card-desc">${escHtml(p.description)}</p>` : ''}
        <a href="${escHtml(link)}" 
           target="_blank" 
           rel="noopener noreferrer sponsored"
           class="btn-buy"
           id="buy-btn-${p.id || index}">
          🛒 쿠팡에서 구매하기
        </a>
      </div>
    </article>`;
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// 실행
loadProducts();
