document.addEventListener('DOMContentLoaded', () => {
    // State Variables
    let currentItemId = null;
    let pollInterval = null;

    // DOM Elements - Modals & Buttons
    const btnAddItem = document.getElementById('btn-add-item');
    const btnSettings = document.getElementById('btn-settings');
    const modalAddItem = document.getElementById('modal-add-item');
    const modalSettings = document.getElementById('modal-settings');
    const btnCloseAddModal = document.getElementById('btn-close-add-modal');
    const btnCancelAddModal = document.getElementById('btn-cancel-add-modal');
    const btnCloseSettingsModal = document.getElementById('btn-close-settings-modal');
    const btnCloseSettingsFooter = document.getElementById('btn-close-settings-footer');
    
    // DOM Elements - Lists & Details
    const itemsGrid = document.getElementById('items-grid');
    const detailSection = document.getElementById('detail-section');
    const detailPlaceholder = document.getElementById('detail-placeholder');
    const detailContainer = document.getElementById('detail-container');
    const btnCloseDetail = document.getElementById('btn-close-detail');
    const modalDetailItem = document.getElementById('modal-detail-item');
    const btnCancelDetail = document.getElementById('btn-cancel-detail');
    

    // Detail Panel fields
    const detailProductNo = document.getElementById('detail-product-no');
    const detailTitle = document.getElementById('detail-title');
    const detailPublishStatus = document.getElementById('detail-publish-status');
    const detailVideoPlayer = document.getElementById('detail-video-player');
    const detailR2Url = document.getElementById('detail-r2-url');
    const detailCoupangUrl = document.getElementById('detail-coupang-url');
    const detailShortUrl = document.getElementById('detail-short-url');
    const detailProductTitle = document.getElementById('detail-product-title');
    const btnSaveShortLink = document.getElementById('btn-save-short-link');
    const btnVisitCoupang = document.getElementById('btn-visit-coupang');
    const btnDeleteItem = document.getElementById('btn-delete-item');
    const btnRegenerate = document.getElementById('btn-regenerate');
    const btnPublishNow = document.getElementById('btn-publish-now');
    const publishResultsDetail = document.getElementById('publish-results-detail');

    // YouTube Trends Elements
    const trendsSearchKeyword = document.getElementById('trends-search-keyword');
    const btnSearchTrends = document.getElementById('btn-search-trends');
    const btnRefreshTrends = document.getElementById('btn-refresh-trends');
    const youtubeTrendsList = document.getElementById('youtube-trends-list');
    const trendsCacheStatus = document.getElementById('trends-cache-status');

    // Platforms checkboxes
    const chkYoutube = document.getElementById('chk-youtube');
    const chkTiktok = document.getElementById('chk-tiktok');
    const chkInstagram = document.getElementById('chk-instagram');

    // Tabs Panel fields
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    // Copy Targets
    const ytTitle = document.getElementById('yt-title');
    const ytDesc = document.getElementById('yt-desc');
    const ytTags = document.getElementById('yt-tags');
    const snsCaption = document.getElementById('sns-caption');
    const dmReply = document.getElementById('dm-reply');
    const dmText = document.getElementById('dm-text');

    // Forms
    const formAddItem = document.getElementById('form-add-item');
    const formSettings = document.getElementById('form-settings');
    const inputVideo = document.getElementById('input-video');
    const fileNamePreview = document.getElementById('file-name-preview');

    // --- Tab Switch Logic ---
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));
            
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
            
            // YouTube 댓글 탭 선택 시 자동 새로고침 실행
            if (targetId === 'tab-comments') {
                fetchYoutubeComments();
            } else if (targetId === 'tab-agent') {
                fetchAgentLogs();
            }
        });
    });

    // --- Modal Controls ---
    const showModal = (modal) => modal.classList.add('show');
    const hideModal = (modal) => modal.classList.remove('show');

    if (btnAddItem) btnAddItem.addEventListener('click', () => showModal(modalAddItem));
    if (btnSettings) {
        btnSettings.addEventListener('click', () => {
            loadSettings();
            showModal(modalSettings);
        });
    }
    if (btnCloseAddModal) btnCloseAddModal.addEventListener('click', () => hideModal(modalAddItem));
    if (btnCancelAddModal) btnCancelAddModal.addEventListener('click', () => hideModal(modalAddItem));
    if (btnCloseSettingsModal) btnCloseSettingsModal.addEventListener('click', () => hideModal(modalSettings));
    if (btnCloseSettingsFooter) btnCloseSettingsFooter.addEventListener('click', () => hideModal(modalSettings));
    
    const closeDetailModal = () => {
        if (modalDetailItem) {
            hideModal(modalDetailItem);
        }
        if (detailVideoPlayer) {
            detailVideoPlayer.pause();
        }
    };

    if (btnCloseDetail) {
        btnCloseDetail.addEventListener('click', closeDetailModal);
    }
    if (btnCancelDetail) {
        btnCancelDetail.addEventListener('click', closeDetailModal);
    }
    if (modalDetailItem) {
        modalDetailItem.addEventListener('click', (e) => {
            if (e.target === modalDetailItem) {
                closeDetailModal();
            }
        });
    }

    // Input File preview
    inputVideo.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileNamePreview.innerText = `선택된 파일: ${e.target.files[0].name}`;
            fileNamePreview.style.display = 'block';
        } else {
            fileNamePreview.style.display = 'none';
        }
    });

    // --- API Calls & Integration ---

    // 0. Helper function to extract publish error message
    function getErrorMessage(item) {
        if (!item.publish_results) return '';
        try {
            const results = typeof item.publish_results === 'string'
                ? JSON.parse(item.publish_results)
                : item.publish_results;
            if (!results) return '';
            if (results.error || results.global_error) {
                return results.error || results.global_error;
            }
            const failedChannels = [];
            for (const ch in results) {
                if (results[ch] && results[ch].status !== 'success') {
                    failedChannels.push(`${ch.toUpperCase()}: ${results[ch].message}`);
                }
            }
            if (failedChannels.length > 0) {
                return failedChannels.join(', ');
            }
        } catch (e) {
            console.error('Error parsing publish_results:', e);
            return '에러 상세 정보 파싱 실패';
        }
        return '';
    }

    // 1. Fetch & Render Items List
    async function loadItems(selectedIdAfterLoad = null) {
        try {
            const res = await fetch('/api/items');
            const items = await res.json();
            
            if (items.length === 0) {
                itemsGrid.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-regular fa-folder-open empty-icon"></i>
                        <p>등록된 상품이 없습니다. 새 상품 등록 버튼을 눌러 첫 콘텐츠를 등록해보세요!</p>
                    </div>
                `;
                return;
            }

            itemsGrid.innerHTML = '';
            items.forEach(item => {
                const card = document.createElement('div');
                card.className = `item-card ${item.id === currentItemId ? 'active' : ''}`;
                card.setAttribute('data-id', item.id);
                
                let statusBadgeClass = 'badge-pending';
                let statusText = '대기중';
                let badgeAttr = '';

                if (item.publish_status === 'pending') {
                    if (!item.coupang_url || item.coupang_url === '') {
                        statusBadgeClass = 'badge-pending'; // 황색 계열 골드색
                        statusText = '링크대기';
                    } else {
                        statusBadgeClass = 'badge-waiting'; // 파란색 계열
                        statusText = '배포대기';
                    }
                } else if (item.publish_status === 'publishing') {
                    statusBadgeClass = 'badge-processing';
                    statusText = '배포중';
                } else if (item.publish_status === 'scheduled') {
                    statusBadgeClass = 'badge-completed';
                    statusText = '예약됨';
                } else if (item.publish_status === 'completed') {
                    statusBadgeClass = 'badge-completed';
                    statusText = '배포완료';
                } else if (item.publish_status === 'partial_failed') {
                    statusBadgeClass = 'badge-failed';
                    statusText = '부분실패';
                    const errMsg = getErrorMessage(item);
                    if (errMsg) {
                        badgeAttr = `title="${errMsg}" style="cursor: help;"`;
                    }
                } else if (item.publish_status === 'failed') {
                    statusBadgeClass = 'badge-failed';
                    statusText = '배포실패';
                    const errMsg = getErrorMessage(item);
                    if (errMsg) {
                        badgeAttr = `title="${errMsg}" style="cursor: help;"`;
                    }
                }

                const displayCode = item.product_code || `No. ${item.product_no}`;
                let scheduleMeta = '';
                if (item.scheduled_at) {
                    try {
                        const sDate = new Date(item.scheduled_at);
                        const kstTimeStr = sDate.toLocaleDateString('ko-KR', {month:'short', day:'numeric'}) + ' ' + sDate.toLocaleTimeString('ko-KR', {hour: '2-digit', minute:'2-digit'});
                        scheduleMeta = `<span class="schedule-text" style="color: var(--accent-gold); display: block; margin-top: 4px; font-size: 0.72rem; font-weight: 500;"><i class="fa-regular fa-clock"></i> ${kstTimeStr} KST 예약</span>`;
                    } catch(e) {}
                }

                card.innerHTML = `
                    <div class="card-thumbnail-box" style="width: 75px; aspect-ratio: 9/16; border-radius: var(--radius-medium); overflow: hidden; background: #000; flex-shrink: 0;">
                        <img src="/static/thumbnails/${item.product_code || ''}.webp" alt="썸네일" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='https://images.unsplash.com/photo-1483985988355-763728e1935b?q=80&w=150'">
                    </div>
                    <div class="card-content-box" style="display: flex; flex-direction: column; flex: 1; min-width: 0; justify-content: space-between;">
                        <div class="card-top" style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="product-badge">${displayCode}</span>
                            <span class="badge ${statusBadgeClass}" ${badgeAttr}>${statusText}</span>
                        </div>
                        <h3 class="card-title" style="margin: 4px 0 2px 0;">${item.title}</h3>
                        <p class="card-desc" style="margin: 0; font-size: 0.78rem; line-height: 1.4; color: var(--text-secondary); display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; height: 1.1rem;">${item.description || ''}</p>
                        <div class="card-meta" style="margin-top: 4px; padding-top: 4px; display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; border-top: 1px solid rgba(255, 255, 255, 0.03);">
                            <span class="date-text" style="color: var(--text-muted);">${new Date(item.created_at).toLocaleDateString()}</span>
                            ${scheduleMeta}
                        </div>
                    </div>
                `;

                card.addEventListener('click', () => {
                    selectItem(item.id);
                });

                itemsGrid.appendChild(card);
            });

            if (selectedIdAfterLoad) {
                selectItem(selectedIdAfterLoad);
            }
        } catch (err) {
            console.error('Error loading items:', err);
        }
    }

    // 2. Select & Show Single Item Details
    async function selectItem(itemId) {
        currentItemId = itemId;
        
        // Highlight active card
        document.querySelectorAll('.item-card').forEach(card => {
            if (card.getAttribute('data-id') == itemId) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });

        // Show details panel in central modal
        if (detailPlaceholder) detailPlaceholder.style.display = 'none';
        if (detailSection) detailSection.classList.add('open');
        if (detailContainer) detailContainer.style.display = 'block';
        if (modalDetailItem) showModal(modalDetailItem);

        // Clear poll interval if active
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }

        await fetchItemDetails(itemId);
    }

    // Fetch details logic (polled during distribution)
    async function fetchItemDetails(itemId) {
        try {
            const res = await fetch(`/api/items/${itemId}`);
            if (res.status === 404) return;
            const item = await res.json();
            
            // Only update details if this is still the selected item
            if (currentItemId !== item.id) return;

            if (detailProductNo) {
                detailProductNo.innerText = `No. ${item.product_no}`;
            }
            if (detailTitle) {
                detailTitle.innerText = item.title;
            }
            if (detailProductTitle) {
                detailProductTitle.value = item.title || '';
            }
            
            // Video path (Original local preview)
            if (detailVideoPlayer) {
                detailVideoPlayer.src = item.original_video_path.replace(new RegExp('^.*uploads/originals/'), '/uploads/originals/');
            }
            
            // R2 URL
            if (detailR2Url) {
                detailR2Url.value = item.r2_video_url || '';
            }

            // Status setup
            if (detailPublishStatus) {
                detailPublishStatus.className = 'badge';
                if (btnPublishNow) btnPublishNow.disabled = false;
                
                if (item.publish_status === 'pending') {
                    if (!item.coupang_url || item.coupang_url === "") {
                        detailPublishStatus.classList.add('badge-pending');
                        detailPublishStatus.innerText = '링크대기';
                    } else {
                        detailPublishStatus.classList.add('badge-waiting');
                        detailPublishStatus.innerText = '배포대기';
                    }
                } else if (item.publish_status === 'scheduled') {
                    detailPublishStatus.classList.add('badge-completed');
                    detailPublishStatus.innerText = '예약됨';
                } else if (item.publish_status === 'publishing') {
                    detailPublishStatus.classList.add('badge-processing');
                    detailPublishStatus.innerText = '배포중';
                    if (btnPublishNow) btnPublishNow.disabled = true;
                    // Poll for updates
                    startPolling(item.id);
                } else if (item.publish_status === 'completed') {
                    detailPublishStatus.classList.add('badge-completed');
                    detailPublishStatus.innerText = '배포완료';
                } else if (item.publish_status === 'partial_failed') {
                    detailPublishStatus.classList.add('badge-failed');
                    detailPublishStatus.innerText = '부분실패';
                } else {
                    detailPublishStatus.classList.add('badge-failed');
                    detailPublishStatus.innerText = '배포실패';
                }
            }

            // Error Message Box control
            const detailErrorBox = document.getElementById('detail-error-box');
            const detailErrorMsg = document.getElementById('detail-error-msg');
            if (detailErrorBox && detailErrorMsg) {
                if (item.publish_status === 'failed' || item.publish_status === 'partial_failed') {
                    const errMsg = getErrorMessage(item);
                    detailErrorMsg.innerText = errMsg || '알 수 없는 배포 오류가 발생했습니다.';
                    detailErrorBox.style.display = 'block';
                } else {
                    detailErrorBox.style.display = 'none';
                    detailErrorMsg.innerText = '';
                }
            }

            // Publish Results Details Rendering
            if (publishResultsDetail) {
                if (item.publish_results) {
                    try {
                        const results = JSON.parse(item.publish_results);
                        
                        if (results.error || results.global_error) {
                            // Global exception
                            publishResultsDetail.innerHTML = `
                                <div class="result-item" style="color: var(--danger)">
                                    <span><i class="fa-solid fa-triangle-exclamation"></i> 오류: ${results.error || results.global_error}</span>
                                </div>
                            `;
                        } else {
                            // Channel results
                            let html = '';
                            for (const platform in results) {
                                const detail = results[platform];
                                const isSuccess = detail.status === 'success';
                                const statusIcon = isSuccess ? '<i class="fa-solid fa-circle-check result-status-ok"></i>' : '<i class="fa-solid fa-circle-xmark result-status-err"></i>';
                                const statusMsg = isSuccess ? '성공' : `실패 (${detail.message})`;
                                const msgClass = isSuccess ? 'result-status-ok' : 'result-status-err';
                                
                                html += `
                                    <div class="result-item">
                                        <span class="result-platform">${statusIcon} ${platform.toUpperCase()}</span>
                                        <span class="${msgClass}">${statusMsg}</span>
                                    </div>
                                `;
                            }
                            publishResultsDetail.innerHTML = html;
                        }
                        publishResultsDetail.style.display = 'flex';
                    } catch (e) {
                        publishResultsDetail.style.display = 'none';
                    }
                } else {
                    publishResultsDetail.style.display = 'none';
                }
            }

            // Coupang Links
            if (detailCoupangUrl) {
                detailCoupangUrl.value = item.coupang_url || '';
            }
            if (detailShortUrl) {
                detailShortUrl.value = item.short_url || '';
            }
            if (btnVisitCoupang) {
                btnVisitCoupang.href = item.coupang_url || '#';
            }
            
            // Description Input Binding
            const detailDescInput = document.getElementById('detail-description-input');
            if (detailDescInput) {
                detailDescInput.value = item.description || '';
            }

            // Platform Contents
            if (ytTitle) ytTitle.value = item.youtube_title || '';
            if (ytDesc) ytDesc.value = item.youtube_description || '';
            
            // ManyChat Mobile Landing URL Binding
            const detailLandingUrl = document.getElementById('detail-landing-url');
            if (detailLandingUrl) {
                detailLandingUrl.value = window.location.origin + '/p/' + item.product_no;
            }
            if (ytTags) ytTags.value = item.youtube_tags || '';
            if (snsCaption) snsCaption.value = item.sns_caption || '';
            if (dmReply) dmReply.value = item.comment_reply || '';
            if (dmText) dmText.value = item.dm_template || '';

            // YouTube Trends keyword binding & auto load
            if (trendsSearchKeyword) {
                if (!trendsSearchKeyword.value || trendsSearchKeyword.dataset.lastItemId != item.id) {
                    trendsSearchKeyword.value = item.title;
                    trendsSearchKeyword.dataset.lastItemId = item.id;
                    loadYoutubeTrends(item.id);
                }
            }

        } catch (err) {
            console.error('Error fetching item details:', err);
        }
    }

    // Polling for processing status
    function startPolling(itemId) {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(() => {
            fetchItemDetails(itemId);
            // Refresh list card status
            loadItems();
        }, 3000);
    }

    // 3. Add Item Submit
    formAddItem.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btnSubmit = document.getElementById('btn-submit-add-item');
        const btnText = btnSubmit.querySelector('.btn-text');
        const spinner = btnSubmit.querySelector('.btn-spinner');

        // Show spinner state
        btnText.style.display = 'none';
        spinner.style.display = 'block';
        btnSubmit.disabled = true;

        const formData = new FormData(formAddItem);

        try {
            const res = await fetch('/api/items', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                hideModal(modalAddItem);
                formAddItem.reset();
                fileNamePreview.style.display = 'none';
                currentItemId = data.item_id;
                await loadItems(data.item_id);
            } else {
                alert('등록 중 에러가 발생했습니다.');
            }
        } catch (err) {
            console.error('Error submitting form:', err);
            alert('네트워크 오류가 발생했습니다.');
        } finally {
            // Restore button state
            btnText.style.display = 'inline-flex';
            spinner.style.display = 'none';
            btnSubmit.disabled = false;
        }
    });

    // 4. Update Custom Short Link & Unified Product Details
    if (btnSaveShortLink) {
        btnSaveShortLink.addEventListener('click', async () => {
            if (!currentItemId) return;

            btnSaveShortLink.disabled = true;
            btnSaveShortLink.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 저장 중...';

            const detailDescInput = document.getElementById('detail-description-input');

            try {
                const res = await fetch(`/api/items/${currentItemId}/short-link`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        short_url: '',
                        coupang_url: detailCoupangUrl ? detailCoupangUrl.value : '',
                        description: detailDescInput ? detailDescInput.value : '',
                        title: detailProductTitle ? detailProductTitle.value : ''
                    })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    closeDetailModal();
                    await loadItems();
                    alert('상품 정보가 저장되었습니다. (오후 6시에 자동 배포됩니다)');
                } else {
                    alert('저장에 실패했습니다.');
                }
            } catch (err) {
                console.error('Error saving short link:', err);
                alert('오류가 발생했습니다.');
            } finally {
                btnSaveShortLink.disabled = false;
                btnSaveShortLink.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> 저장';
            }
        });
    }

    // 5. Trigger Batch Social Publication (R2 + Buffer)
    if (btnPublishNow) {
        btnPublishNow.addEventListener('click', async () => {
            if (!currentItemId) return;

            const platforms = [];
            if (chkYoutube && chkYoutube.checked) platforms.push('youtube');
            if (chkTiktok && chkTiktok.checked) platforms.push('tiktok');
            if (chkInstagram && chkInstagram.checked) platforms.push('instagram');

            if (platforms.length === 0) {
                alert('배포할 플랫폼 채널을 하나 이상 선택해 주세요.');
                return;
            }

            btnPublishNow.disabled = true;
            btnPublishNow.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 배포 요청 전송 중...';

            try {
                const res = await fetch(`/api/items/${currentItemId}/publish`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ platforms })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    if (detailPublishStatus) {
                        detailPublishStatus.className = 'badge badge-processing';
                        detailPublishStatus.innerText = '배포 진행중...';
                    }
                    startPolling(currentItemId);
                    loadItems();
                } else {
                    alert('배포 요청에 실패했습니다.');
                    btnPublishNow.disabled = false;
                    btnPublishNow.innerHTML = '<i class="fa-solid fa-paper-plane"></i> 선택 채널로 일괄 배포 실행';
                }
            } catch (err) {
                console.error('Error triggering publish:', err);
                alert('오류 발생');
                btnPublishNow.disabled = false;
                btnPublishNow.innerHTML = '<i class="fa-solid fa-paper-plane"></i> 선택 채널로 일괄 배포 실행';
            }
        });
    }

    // 6. Regenerate Content (Gemini)
    if (btnRegenerate) {
        btnRegenerate.addEventListener('click', async () => {
            if (!currentItemId) return;

            btnRegenerate.disabled = true;
            btnRegenerate.innerHTML = '<i class="fa-solid fa-rotate fa-spin"></i> AI 집필중...';

            try {
                const res = await fetch(`/api/items/${currentItemId}/regenerate`, {
                    method: 'POST'
                });
                const data = await res.json();
                if (data.status === 'success') {
                    await fetchItemDetails(currentItemId);
                } else {
                    alert('문구 생성에 실패했습니다.');
                }
            } catch (err) {
                console.error('Error regenerating content:', err);
                alert('오류 발생');
            } finally {
                btnRegenerate.disabled = false;
                btnRegenerate.innerHTML = '<i class="fa-solid fa-rotate"></i> AI 홍보글 재작성 (Gemini)';
            }
        });
    }

    // 7. Delete Item
    if (btnDeleteItem) {
        btnDeleteItem.addEventListener('click', async () => {
            if (!currentItemId) return;
            if (!confirm('정말로 이 상품 및 동영상을 영구 삭제하시겠습니까?')) return;

            try {
                const res = await fetch(`/api/items/${currentItemId}`, {
                    method: 'DELETE'
                });
                const data = await res.json();
                if (data.status === 'success') {
                    currentItemId = null;
                    closeDetailModal();
                    if (pollInterval) {
                        clearInterval(pollInterval);
                        pollInterval = null;
                    }
                    await loadItems();
                }
            } catch (err) {
                console.error('Error deleting item:', err);
            }
        });
    }

    // 8. General Settings Management
    async function loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const settings = await res.json();
            
            const chkYt = document.getElementById('setting-publish-youtube');
            const chkTt = document.getElementById('setting-publish-tiktok');
            const chkIg = document.getElementById('setting-publish-instagram');
            
            if (chkYt) chkYt.checked = settings.PUBLISH_YOUTUBE === 'true';
            if (chkTt) chkTt.checked = settings.PUBLISH_TIKTOK === 'true';
            if (chkIg) chkIg.checked = settings.PUBLISH_INSTAGRAM === 'true';
        } catch (err) {
            console.error('Error loading settings:', err);
        }
    }

    if (formSettings) {
        formSettings.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const chkYt = document.getElementById('setting-publish-youtube');
            const chkTt = document.getElementById('setting-publish-tiktok');
            const chkIg = document.getElementById('setting-publish-instagram');
            
            const payload = {
                PUBLISH_YOUTUBE: chkYt ? String(chkYt.checked) : 'false',
                PUBLISH_TIKTOK: chkTt ? String(chkTt.checked) : 'false',
                PUBLISH_INSTAGRAM: chkIg ? String(chkIg.checked) : 'false'
            };

            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    hideModal(modalSettings);
                    alert('기본 배포 채널 설정이 저장되었습니다.');
                }
            } catch (err) {
                console.error('Error saving settings:', err);
                alert('설정 저장 중 오류가 발생했습니다.');
            }
        });
    }

    // 9. Copy to Clipboard Utility
    const copyButtons = document.querySelectorAll('.btn-copy');
    copyButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const targetEl = document.getElementById(targetId);
            
            if (!targetEl || !targetEl.value) return;

            navigator.clipboard.writeText(targetEl.value).then(() => {
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-check"></i> 복사 완료!';
                btn.classList.add('copied');
                
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.classList.remove('copied');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });
        });
    });

    // --- YouTube Comments Real-time Monitor ---
    const btnRefreshComments = document.getElementById('btn-refresh-comments');
    const youtubeCommentsList = document.getElementById('youtube-comments-list');

    async function fetchYoutubeComments() {
        if (!btnRefreshComments || !youtubeCommentsList) return;
        
        btnRefreshComments.disabled = true;
        btnRefreshComments.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 로딩중...';
        youtubeCommentsList.innerHTML = '<div class="empty-state" style="padding: 2rem 1rem;"><p>댓글 피드를 불러오는 중입니다...</p></div>';

        try {
            const res = await fetch('/api/youtube/comments');
            const data = await res.json();

            if (data.status === 'success' && data.comments && data.comments.length > 0) {
                youtubeCommentsList.innerHTML = '';
                data.comments.forEach(comment => {
                    const card = document.createElement('div');
                    card.className = 'comment-card';
                    
                    const publishedDate = new Date(comment.publishedAt).toLocaleString('ko-KR', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });

                    // 특정 대댓글 다이렉트 고정 주소
                    const youtubeUrl = `https://www.youtube.com/watch?v=${comment.videoId}&lc=${comment.id}`;

                    card.innerHTML = `
                        <img class="comment-avatar" src="${comment.avatar || 'https://www.gstatic.com/youtube/media/ytm/images/pml_profile_photo.png'}" alt="profile" onerror="this.src='https://www.gstatic.com/youtube/media/ytm/images/pml_profile_photo.png'">
                        <div class="comment-body">
                            <div class="comment-author-row">
                                <a href="${comment.authorUrl}" target="_blank" class="comment-author">${comment.author}</a>
                                <span class="comment-date">${publishedDate}</span>
                            </div>
                            <p class="comment-text">${comment.text}</p>
                            <div class="comment-actions">
                                <button class="btn-comment-copy">
                                    <i class="fa-regular fa-copy"></i> 네이버 검색 유도 답변 복사 & 이동
                                </button>
                                <a href="${youtubeUrl}" target="_blank" class="btn-comment-link">
                                    <i class="fa-brands fa-youtube"></i> 그냥 바로가기
                                </a>
                            </div>
                        </div>
                    `;

                    // 답변 복사 및 새창 이동 이벤트
                    const btnCopyMove = card.querySelector('.btn-comment-copy');
                    btnCopyMove.addEventListener('click', () => {
                        let replyText = '';
                        const currentReplyEl = document.getElementById('dm-reply');
                        
                        if (currentReplyEl && currentReplyEl.value) {
                            replyText = currentReplyEl.value;
                        } else {
                            replyText = `유튜브 정책상 댓글 링크 클릭이 되지 않아서 네이버 검색을 안내해 드려요! 🔍 네이버 검색창에 '엄마아빠 패션다이어리'를 검색하시면 추천 제품 상세 정보를 바로 보실 수 있습니다!`;
                        }

                        navigator.clipboard.writeText(replyText).then(() => {
                            btnCopyMove.innerHTML = '<i class="fa-solid fa-check"></i> 복사 완료! 이동 중...';
                            btnCopyMove.style.background = 'var(--secondary)';
                            btnCopyMove.style.color = 'white';

                            setTimeout(() => {
                                window.open(youtubeUrl, '_blank');
                                btnCopyMove.innerHTML = '<i class="fa-regular fa-copy"></i> 네이버 검색 유도 답변 복사 & 이동';
                                btnCopyMove.style.background = 'rgba(139, 92, 246, 0.1)';
                                btnCopyMove.style.color = 'var(--primary)';
                            }, 1000);
                        }).catch(err => {
                            console.error('Failed to copy: ', err);
                            window.open(youtubeUrl, '_blank');
                        });
                    });

                    youtubeCommentsList.appendChild(card);
                });
            } else {
                const msg = data.message || '최근 등록된 채널 댓글이 없거나 API Key 설정을 확인해 주세요.';
                youtubeCommentsList.innerHTML = `
                    <div class="empty-state" style="padding: 2rem 1rem;">
                        <i class="fa-regular fa-circle-question empty-icon" style="font-size: 2rem;"></i>
                        <p>${msg}</p>
                    </div>
                `;
            }
        } catch (err) {
            console.error('Error fetching comments:', err);
            youtubeCommentsList.innerHTML = `
                <div class="empty-state" style="padding: 2rem 1rem;">
                    <i class="fa-solid fa-triangle-exclamation empty-icon" style="color: var(--danger); font-size: 2rem;"></i>
                    <p>댓글 데이터를 가져오는 중 오류가 발생했습니다.</p>
                </div>
            `;
        } finally {
            btnRefreshComments.disabled = false;
            btnRefreshComments.innerHTML = '<i class="fa-solid fa-rotate"></i> 새로고침';
        }
    }

    if (btnRefreshComments) {
        btnRefreshComments.addEventListener('click', fetchYoutubeComments);
    }

    // --- YouTube Trends Caching & Benchmarking Logic ---

    async function loadYoutubeTrends(itemId) {
        if (!youtubeTrendsList) return;
        
        youtubeTrendsList.innerHTML = '<div class="trends-empty"><p><i class="fa-solid fa-spinner fa-spin"></i> 분석 데이터를 불러오는 중...</p></div>';
        if (trendsCacheStatus) trendsCacheStatus.style.display = 'none';

        try {
            const res = await fetch(`/api/items/${itemId}/youtube-trends`);
            const data = await res.json();

            if (data.status === 'success' && data.trends) {
                renderYoutubeTrends(itemId, data.trends, data.cached);
            } else {
                youtubeTrendsList.innerHTML = `
                    <div class="trends-empty">
                        <p>${data.message || '인기 영상 트렌드 데이터를 불러오지 못했습니다.'}</p>
                    </div>
                `;
            }
        } catch (err) {
            console.error('Error loading youtube trends:', err);
            youtubeTrendsList.innerHTML = '<div class="trends-empty"><p>데이터 로딩 중 에러가 발생했습니다.</p></div>';
        }
    }

    async function refreshYoutubeTrends(itemId, keyword) {
        if (!youtubeTrendsList) return;

        const btnSearch = document.getElementById('btn-search-trends');
        const originalHtml = btnSearch ? btnSearch.innerHTML : '';
        if (btnSearch) {
            btnSearch.disabled = true;
            btnSearch.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        }

        youtubeTrendsList.innerHTML = '<div class="trends-empty"><p><i class="fa-solid fa-spinner fa-spin"></i> 유튜브 인기 영상을 분석 중입니다 (API 호출)...</p></div>';
        if (trendsCacheStatus) trendsCacheStatus.style.display = 'none';

        try {
            const res = await fetch(`/api/items/${itemId}/youtube-trends/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword })
            });
            const data = await res.json();

            if (data.status === 'success' && data.trends) {
                renderYoutubeTrends(itemId, data.trends, false);
            } else {
                youtubeTrendsList.innerHTML = `
                    <div class="trends-empty">
                        <p>${data.message || '유튜브 실시간 검색 분석에 실패했습니다.'}</p>
                    </div>
                `;
            }
        } catch (err) {
            console.error('Error refreshing youtube trends:', err);
            youtubeTrendsList.innerHTML = '<div class="trends-empty"><p>검색 도중 네트워크 에러가 발생했습니다.</p></div>';
        } finally {
            if (btnSearch) {
                btnSearch.disabled = false;
                btnSearch.innerHTML = originalHtml;
            }
        }
    }

    function renderYoutubeTrends(itemId, trends, isCached) {
        if (!youtubeTrendsList) return;

        if (trendsCacheStatus) {
            trendsCacheStatus.style.display = 'inline-block';
            trendsCacheStatus.innerText = isCached ? 'DB 캐시됨' : '실시간 수집';
            trendsCacheStatus.style.background = isCached ? 'rgba(16, 185, 129, 0.15)' : 'rgba(139, 92, 246, 0.15)';
            trendsCacheStatus.style.color = isCached ? 'var(--secondary)' : 'var(--primary)';
        }

        if (trends.length === 0) {
            youtubeTrendsList.innerHTML = '<div class="trends-empty"><p>관련 인기 동영상을 찾을 수 없습니다.</p></div>';
            return;
        }

        youtubeTrendsList.innerHTML = '';
        trends.forEach(video => {
            const card = document.createElement('div');
            card.className = 'trend-card';

            const youtubeUrl = `https://www.youtube.com/watch?v=${video.videoId}`;
            
            let badgeClass = 'badge-normal';
            if (video.efficiency === 'Great') badgeClass = 'badge-great';
            else if (video.efficiency === 'Good') badgeClass = 'badge-good';

            card.innerHTML = `
                <img class="trend-thumb" src="${video.thumbnailUrl || ''}" alt="thumb">
                <div class="trend-info">
                    <div style="display: flex; align-items: center; gap: 0.35rem; margin-bottom: 3px;">
                        <span class="badge ${badgeClass}" style="padding: 1px 5px; font-size: 0.65rem; white-space: nowrap; flex-shrink: 0; line-height: 1.2; font-weight: 600;">${video.efficiencyLabel}</span>
                        <a href="${youtubeUrl}" target="_blank" class="trend-title" title="${video.title}">${video.title}</a>
                    </div>
                    <div class="trend-meta-row">
                        <span>${video.channelTitle}</span>
                        <span class="trend-views"><i class="fa-regular fa-eye"></i> ${video.viewCount}</span>
                    </div>
                </div>
                <button class="btn-use-title">가져오기</button>
            `;

            // 제목 벤치마킹 연동 가져오기 버튼 액션
            const btnUse = card.querySelector('.btn-use-title');
            btnUse.addEventListener('click', () => {
                if (ytTitle) {
                    ytTitle.value = video.title;
                    ytTitle.focus();
                    
                    // 성공 피드백 알림
                    const originalText = btnUse.innerText;
                    btnUse.innerText = '반영됨!';
                    btnUse.style.background = 'var(--secondary)';
                    btnUse.style.color = 'white';
                    
                    setTimeout(() => {
                        btnUse.innerText = originalText;
                        btnUse.style.background = '';
                        btnUse.style.color = '';
                    }, 1500);
                }
            });

            youtubeTrendsList.appendChild(card);
        });
    }

    // 트렌드 검색/새로고침 이벤트 리스너 바인딩
    if (btnSearchTrends) {
        btnSearchTrends.addEventListener('click', () => {
            if (currentItemId && trendsSearchKeyword) {
                refreshYoutubeTrends(currentItemId, trendsSearchKeyword.value);
            }
        });
    }

    if (btnRefreshTrends) {
        btnRefreshTrends.addEventListener('click', () => {
            if (currentItemId && trendsSearchKeyword) {
                refreshYoutubeTrends(currentItemId, trendsSearchKeyword.value);
            }
        });
    }

    // --- AI Agent Logs & Trigger Logic ---
    const btnTriggerAgent = document.getElementById('btn-trigger-agent');
    const btnRefreshAgentLogs = document.getElementById('btn-refresh-agent-logs');
    const agentLogsList = document.getElementById('agent-logs-list');

    async function fetchAgentLogs() {
        if (!agentLogsList) return;
        agentLogsList.innerHTML = '<div class="empty-state" style="padding: 1.5rem 1rem;"><p><i class="fa-solid fa-spinner fa-spin"></i> 로그 데이터를 불러오는 중...</p></div>';

        try {
            const res = await fetch('/api/agent/logs');
            const logs = await res.json();

            if (logs && logs.length > 0) {
                agentLogsList.innerHTML = '';
                logs.forEach(log => {
                    const row = document.createElement('div');
                    row.className = `agent-log-item status-${log.status}`;
                    
                    let icon = '<i class="fa-solid fa-gear"></i>';
                    let taskName = '시스템';
                    if (log.task_type === 'auto_publish') {
                        icon = '<i class="fa-solid fa-cloud-arrow-up"></i>';
                        taskName = '자동 배포';
                    } else if (log.task_type === 'comment_monitor') {
                        icon = '<i class="fa-solid fa-comments"></i>';
                        taskName = '댓글 감지';
                    } else if (log.task_type === 'manychat_event') {
                        icon = '<i class="fa-solid fa-paper-plane"></i>';
                        taskName = 'ManyChat';
                    }

                    const logTime = new Date(log.created_at).toLocaleString('ko-KR', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    });

                    row.innerHTML = `
                        <div class="log-icon-box">${icon}</div>
                        <div class="log-content-box">
                            <div class="log-meta">
                                <span class="log-task-name">${taskName}</span>
                                <span class="log-time">${logTime}</span>
                            </div>
                            <p class="log-msg">${log.message}</p>
                        </div>
                    `;
                    agentLogsList.appendChild(row);
                });
            } else {
                agentLogsList.innerHTML = '<div class="empty-state" style="padding: 2rem 1rem;"><p>아직 기록된 에이전트 활동 이력이 없습니다.</p></div>';
            }
        } catch (err) {
            console.error('Error fetching agent logs:', err);
            agentLogsList.innerHTML = '<div class="empty-state" style="padding: 2rem 1rem;"><p style="color: var(--danger)">로그 데이터를 가져오는 중 오류가 발생했습니다.</p></div>';
        }
    }

    if (btnTriggerAgent) {
        btnTriggerAgent.addEventListener('click', async () => {
            btnTriggerAgent.disabled = true;
            btnTriggerAgent.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 기동 요청중...';

            try {
                const res = await fetch('/api/agent/trigger', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    alert('에이전트가 백그라운드에서 즉시 기동되었습니다. 잠시 후 로그를 새로고침 하세요.');
                    setTimeout(fetchAgentLogs, 1500);
                } else {
                    alert('기동 실패');
                }
            } catch (err) {
                console.error(err);
                alert('네트워크 오류');
            } finally {
                btnTriggerAgent.disabled = false;
                btnTriggerAgent.innerHTML = '<i class="fa-solid fa-play"></i> 에이전트 즉시 기동';
            }
        });
    }

    if (btnRefreshAgentLogs) {
        btnRefreshAgentLogs.addEventListener('click', fetchAgentLogs);
    }

    // --- YouTube OAuth2 Integration Helpers ---
    const ytConnectionStatus = document.getElementById('youtube-connection-status');
    
    async function checkYoutubeStatus() {
        if (!ytConnectionStatus) return;
        try {
            const res = await fetch('/api/youtube/status');
            const data = await res.json();
            
            if (data.connected) {
                ytConnectionStatus.innerHTML = `
                    <span class="badge badge-completed" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); height: 36px; display: inline-flex; align-items: center; font-size: 0.82rem; padding: 0 12px; border-radius: var(--radius-medium);">
                        <i class="fa-brands fa-youtube" style="font-size: 1rem; color: #ff0000; margin-right: 4px;"></i> 연동 완료 (${data.channel_id.substring(0,8)}...)
                    </span>
                `;
            } else {
                ytConnectionStatus.innerHTML = `
                    <button id="btn-youtube-connect" class="btn btn-secondary btn-small" style="height: 36px; font-weight: 600; color: #FFF; background: linear-gradient(135deg, #FF0000, #C10000); border: none;">
                        <i class="fa-brands fa-youtube"></i> 유튜브 연동하기
                    </button>
                `;
                
                const btnConnect = document.getElementById('btn-youtube-connect');
                if (btnConnect) {
                    btnConnect.addEventListener('click', async () => {
                        try {
                            const authRes = await fetch('/api/youtube/auth');
                            const authData = await authRes.json();
                            if (authData.url) {
                                const popup = window.open(authData.url, 'YouTube Authentication', 'width=600,height=750,scrollbars=yes');
                                const timer = setInterval(async () => {
                                    if (popup.closed) {
                                        clearInterval(timer);
                                        await checkYoutubeStatus();
                                        if (currentItemId) {
                                            await fetchItemDetails(currentItemId);
                                        }
                                    }
                                }, 1000);
                            }
                        } catch (err) {
                            console.error('Failed to trigger YouTube OAuth:', err);
                        }
                    });
                }
            }
        } catch (err) {
            console.error('Error fetching YouTube connection status:', err);
        }
    }

    // Initialize Page
    loadItems();
    checkYoutubeStatus();
    setInterval(checkYoutubeStatus, 15000);
});
