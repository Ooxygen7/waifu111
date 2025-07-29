document.addEventListener('DOMContentLoaded', function () {
    // --- 浮动提示 (Toast) ---
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type}`;
        const iconClass = type === 'success' ? 'fa-check-circle' : 'fa-times-circle';
        toast.innerHTML = `<i class="fas ${iconClass} toast-icon"></i><span>${message}</span>`;
        document.body.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 100);
        setTimeout(() => {
            toast.classList.remove('show');
            toast.addEventListener('transitionend', () => toast.remove(), { once: true });
        }, 3000);
    }

    // --- 复制转发命令 ---
    function copyForwardCommand(groupId, messageId) {
        const command = `/fw ${groupId} ${messageId}`;
        navigator.clipboard.writeText(command).then(() => {
            showToast('转发命令已复制', 'success');
        }).catch(err => {
            console.error('复制失败:', err);
            showToast('复制失败，请手动操作', 'error');
        });
    }

    // --- 模态框控制 ---
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex'; // Keep this for the flex layout
            modal.classList.add('active');
            modal.setAttribute('aria-hidden', 'false');
        }
    }

    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    document.querySelectorAll('.modal-close, .modal-overlay, .modal-close-btn').forEach(el => {
        el.addEventListener('click', function (event) {
            // The `this.closest('.modal-overlay')` will find the correct modal to close.
            // The check `event.target === this` ensures that clicks on the modal content
            // do not bubble up and close the modal.
            if (event.target === this) {
                const modal = this.closest('.modal-overlay');
                if (modal) {
                    closeModal(modal.id);
                }
            } else if (this.classList.contains('modal-close-btn') || this.classList.contains('modal-close')) {
                 const modal = this.closest('.modal-overlay');
                if (modal) {
                    closeModal(modal.id);
                }
            }
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const openModalEl = document.querySelector('.modal-overlay[aria-hidden="false"]');
            if (openModalEl) closeModal(openModalEl.id);
        }
    });

    // --- 信息卡片折叠 ---
    const detailsCard = document.getElementById('groupDetailsCard');
    if (detailsCard) {
        const toggleBtn = detailsCard.querySelector('#toggleDetailsBtn');
        const collapsibleContent = detailsCard.querySelector('.collapsible-content');

        const toggleCard = (collapse) => {
            if (collapse) {
                detailsCard.classList.add('collapsed');
                localStorage.setItem('groupInfoCardState', 'collapsed');
            } else {
                detailsCard.classList.remove('collapsed');
                localStorage.setItem('groupInfoCardState', 'expanded');
            }
        };

        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleCard(detailsCard.classList.contains('collapsed') ? false : true);
        });
        
        detailsCard.querySelector('.collapsible-header').addEventListener('click', () => {
             toggleCard(detailsCard.classList.contains('collapsed') ? false : true);
        });

        // Default to collapsed state if not set in localStorage
        if (localStorage.getItem('groupInfoCardState') === 'expanded') {
            detailsCard.classList.remove('collapsed');
        } else {
            detailsCard.classList.add('collapsed');
        }
    }

    // --- 消息列表交互 ---
    const messageList = document.getElementById('messageList');
    const isSearchMode = new URLSearchParams(window.location.search).has('search');
    const groupId = document.body.dataset.groupId;

    if (messageList) {
        messageList.addEventListener('click', (event) => {
            const container = event.target.closest('.message-bubble-container');
            if (!container) return;

            const msgId = container.dataset.dialogId;

            // 处理转发按钮点击
            if (event.target.closest('.forward-btn')) {
                event.stopPropagation();
                copyForwardCommand(groupId, msgId);
                return;
            }

            // 处理消息气泡点击
            if (isSearchMode) {
                const originalPage = container.dataset.originalPage || 1;
                const url = new URL(window.location.href);
                url.searchParams.delete('search');
                url.searchParams.set('page', originalPage);
                url.hash = `msg-${msgId}`;
                window.location.href = url.toString();
            } else {
                // 填充并打开详情模态框
                document.getElementById('modal-sender').textContent = container.dataset.userName;
                const role = container.dataset.role;
                document.getElementById('modal-role').textContent = role === 'user' ? '用户' : 'AI';
                document.getElementById('modal-turn').textContent = container.dataset.turn;
                document.getElementById('modal-time').textContent = container.dataset.time;
                document.getElementById('modal-msg-id').textContent = container.dataset.msgId || 'N/A';
                document.getElementById('modal-raw-content').textContent = container.dataset.rawContent;
                document.getElementById('modal-processed-content').textContent = container.dataset.processedContent;
                openModal('messageDetailModal');
            }
            
            // --- Modal Meta Card Collapse ---
            const modalMetaCard = document.getElementById('modalMetaCard');
            if (modalMetaCard) {
                const header = modalMetaCard.querySelector('.collapsible-header');
                header.addEventListener('click', () => {
                    modalMetaCard.classList.toggle('collapsed');
                });
            }
        });
    }

    // --- 滚动到指定消息 ---
    function scrollToMessage(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            element.classList.add('highlight-pulse');
            setTimeout(() => element.classList.remove('highlight-pulse'), 2500);
        }
    }

    // 页面加载时滚动
    const targetMsgId = window.location.hash.substring(1);
    if (targetMsgId) {
        scrollToMessage(targetMsgId);
    } else if (isSearchMode) {
        const firstHighlight = document.querySelector('.search-highlight');
        if (firstHighlight) {
            const container = firstHighlight.closest('.message-bubble-container');
            if (container) scrollToMessage(container.id);
        }
    }
});