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
    
    // Detail Panel fields
    const detailProductNo = document.getElementById('detail-product-no');
    const detailTitle = document.getElementById('detail-title');
    const detailPublishStatus = document.getElementById('detail-publish-status');
    const detailVideoPlayer = document.getElementById('detail-video-player');
    const detailR2Url = document.getElementById('detail-r2-url');
    const detailCoupangUrl = document.getElementById('detail-coupang-url');
    const detailShortUrl = document.getElementById('detail-short-url');
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
            }
        });
    });

    // --- Modal Controls ---
    const showModal = (modal) => modal.classList.add('show');
    const hideModal = (modal) => modal.classList.remove('show');

    btnAddItem.addEventListener('click', () => showModal(modalAddItem));
    btnSettings.addEventListener('click', () => {
        loadSettings();
        showModal(modalSettings);
    });

    btnCloseAddModal.addEventListener('click', () => hideModal(modalAddItem));
    btnCancelAddModal.addEventListener('click', () => hideModal(modalAddItem));
    btnCloseSettingsModal.addEventListener('click', () => hideModal(modalSettings));
    btnCloseSettingsFooter.addEventListener('click', () => hideModal(modalSettings));

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
                if (item.publish_status === 'publishing') {
                    statusBadgeClass = 'badge-processing';
                    statusText = '배포중';
                } else if (item.publish_status === 'completed') {
                    statusBadgeClass = 'badge-completed';
                    statusText = '배포완료';
                } else if (item.publish_status === 'partial_failed') {
                    statusBadgeClass = 'badge-pending';
                    statusText = '부분실패';
                } else if (item.publish_status === 'failed') {
                    statusBadgeClass = 'badge-failed';
                    statusText = '배포실패';
                }

                card.innerHTML = `
                    <div class="card-top">
                        <span class="product-badge">No. ${item.product_no}</span>
                        <span class="badge ${statusBadgeClass}">${statusText}</span>
                    </div>
                    <h3 class="card-title">${item.title}</h3>
                    <p class="card-desc">${item.description || ''}</p>
                    <div class="card-meta">
                        <span class="date-text">${new Date(item.created_at).toLocaleDateString()}</span>
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

        // Show details panel, hide placeholder
        detailPlaceholder.style.display = 'none';
        detailSection.style.display = 'flex';
        detailContainer.style.display = 'block';

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

            detailProductNo.innerText = `No. ${item.product_no}`;
            detailTitle.innerText = item.title;
            
            // Video path (Original local preview)
            detailVideoPlayer.src = item.original_video_path.replace(new RegExp('^.*uploads/originals/'), '/uploads/originals/');
            
            // R2 URL
            detailR2Url.value = item.r2_video_url || '';

            // Status setup
            detailPublishStatus.className = 'badge';
            btnPublishNow.disabled = false;
            
            if (item.publish_status === 'pending') {
                detailPublishStatus.classList.add('badge-pending');
                detailPublishStatus.innerText = '배포 대기중';
            } else if (item.publish_status === 'publishing') {
                detailPublishStatus.classList.add('badge-processing');
                detailPublishStatus.innerText = '배포 진행중...';
                btnPublishNow.disabled = true;
                // Poll for updates
                startPolling(item.id);
            } else if (item.publish_status === 'completed') {
                detailPublishStatus.classList.add('badge-completed');
                detailPublishStatus.innerText = '배포 성공';
            } else if (item.publish_status === 'partial_failed') {
                detailPublishStatus.classList.add('badge-pending');
                detailPublishStatus.innerText = '일부 채널 실패';
            } else {
                detailPublishStatus.classList.add('badge-failed');
                detailPublishStatus.innerText = '배포 실패';
            }

            // Publish Results Details Rendering
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

            // Coupang Links
            detailCoupangUrl.value = item.coupang_url;
            detailShortUrl.value = item.short_url || '';
            btnVisitCoupang.href = item.coupang_url;

            // Platform Contents
            ytTitle.value = item.youtube_title || '';
            ytDesc.value = item.youtube_description || '';
            ytTags.value = item.youtube_tags || '';
            snsCaption.value = item.sns_caption || '';
            dmReply.value = item.comment_reply || '';
            dmText.value = item.dm_template || '';

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

    // 4. Update Custom Short Link
    btnSaveShortLink.addEventListener('click', async () => {
        if (!currentItemId) return;

        btnSaveShortLink.disabled = true;
        btnSaveShortLink.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 저장중';

        try {
            const res = await fetch(`/api/items/${currentItemId}/short-link`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    short_url: detailShortUrl.value,
                    coupang_url: detailCoupangUrl.value
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                await fetchItemDetails(currentItemId);
                alert('링크 및 AI 홍보 문구가 업데이트되었습니다.');
            } else {
                alert('업데이트 실패');
            }
        } catch (err) {
            console.error('Error saving short link:', err);
            alert('오류 발생');
        } finally {
            btnSaveShortLink.disabled = false;
            btnSaveShortLink.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> 저장';
        }
    });

    // 5. Trigger Batch Social Publication (R2 + Buffer)
    btnPublishNow.addEventListener('click', async () => {
        if (!currentItemId) return;

        const platforms = [];
        if (chkYoutube.checked) platforms.push('youtube');
        if (chkTiktok.checked) platforms.push('tiktok');
        if (chkInstagram.checked) platforms.push('instagram');

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
                // Instantly update UI status to publishing and start polling
                detailPublishStatus.className = 'badge badge-processing';
                detailPublishStatus.innerText = '배포 진행중...';
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

    // 6. Regenerate Content (Gemini)
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

    // 7. Delete Item
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
                detailContainer.style.display = 'none';
                detailPlaceholder.style.display = 'flex';
                if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                }
                loadItems();
            }
        } catch (err) {
            console.error('Error deleting item:', err);
        }
    });

    // 8. Settings Management
    async function loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const settings = await res.json();
            
            document.getElementById('setting-gemini-key').value = settings.GEMINI_API_KEY || '';
            document.getElementById('setting-buffer-token').value = settings.BUFFER_ACCESS_TOKEN || '';
            document.getElementById('setting-r2-account').value = settings.CLOUDFLARE_ACCOUNT_ID || '';
            document.getElementById('setting-r2-token').value = settings.CLOUDFLARE_API_TOKEN || '';
            document.getElementById('setting-r2-bucket').value = settings.CLOUDFLARE_BUCKET_NAME || 'blog';
            document.getElementById('setting-r2-url').value = settings.CLOUDFLARE_PUBLIC_URL || '';
            document.getElementById('setting-coupang-access').value = settings.COUPANG_ACCESS_KEY || '';
            document.getElementById('setting-coupang-secret').value = settings.COUPANG_SECRET_KEY || '';
            document.getElementById('setting-manychat-token').value = settings.MANYCHAT_API_TOKEN || '';
            document.getElementById('setting-youtube-key').value = settings.YOUTUBE_API_KEY || '';
        } catch (err) {
            console.error('Error loading settings:', err);
        }
    }

    formSettings.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(formSettings);
        const payload = {};
        formData.forEach((value, key) => {
            payload[key] = value;
        });

        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'success') {
                hideModal(modalSettings);
                alert('설정이 안전하게 저장되었습니다.');
                // Refresh active details in case key was updated
                if (currentItemId) {
                    await fetchItemDetails(currentItemId);
                }
            }
        } catch (err) {
            console.error('Error saving settings:', err);
            alert('설정 저장 중 오류가 발생했습니다.');
        }
    });

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

    // Initialize Page
    loadItems();
});
