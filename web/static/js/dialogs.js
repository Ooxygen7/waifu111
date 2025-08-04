document.addEventListener('DOMContentLoaded', function () {
    console.log('dialogs.js loaded and DOM ready.');
    // 从 window 对象安全地获取由 Jinja2 模板传递过来的数据
    const conversation = window.conversationData;
    const dialogs = window.dialogsData;
    const baseUrl = window.dialogsUrl;
    let currentEditingDialogId = null;

    // --- 模态框和通用UI功能 ---

    /**
     * 打开指定的模态框
     * @param {string} modalId - 模态框的ID
     */
    function openModal(modalId) {
        console.log('Attempting to open modal:', modalId);
        const modal = document.getElementById(modalId);
        console.log('Modal element found:', modal);
        if (modal) {
            modal.style.display = 'flex'; // 确保 display 是 flex
            // 延迟一帧以确保 transition 生效
            setTimeout(() => {
                modal.style.opacity = '1';
                modal.style.visibility = 'visible';
                modal.style.pointerEvents = 'auto';
            }, 10);
            modal.setAttribute('aria-hidden', 'false');
        } else {
            console.error('Modal element not found for ID:', modalId);
        }
    }

    /**
     * 关闭指定的模态框
     * @param {string} modalId - 模态框的ID
     */
    function closeModal(modalId) {
        console.log('Attempting to close modal:', modalId);
        const modal = document.getElementById(modalId);
        console.log('Modal element found:', modal);
        if (modal) {
            modal.style.opacity = '0';
            modal.style.pointerEvents = 'none';
            // 在 transition 结束后再隐藏
            setTimeout(() => {
                modal.style.display = 'none';
                modal.style.visibility = 'hidden';
            }, 300); // 匹配 main.css 中的 transition 时间
            modal.setAttribute('aria-hidden', 'true');
        } else {
            console.error('Modal element not found for ID:', modalId);
        }
    }

    // 为所有关闭按钮和遮罩层添加关闭事件
    document.querySelectorAll('.modal-close, .modal-overlay, .modal-close-btn').forEach(el => {
        el.addEventListener('click', function (event) {
            if (event.target === this || this.classList.contains('modal-close-btn') || this.classList.contains('modal-close')) {
                const modal = this.closest('.modal-overlay');
                if (modal) {
                    closeModal(modal.id);
                }
            }
        });
    });
    
    // 键盘支持 - ESC键关闭模态框
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            const openModal = document.querySelector('.modal-overlay[aria-hidden="false"]');
            if (openModal) {
                closeModal(openModal.id);
            }
        }
    });


    // --- 浮动提示 (Toast) ---
    /**
     * 显示一个浮动提示
     * @param {string} message - 要显示的消息
     * @param {string} type - 'success' 或 'error'
     */
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type}`;
        
        const iconClass = type === 'success' ? 'fa-check-circle' : 'fa-times-circle';
        toast.innerHTML = `
            <i class="fas ${iconClass} toast-icon"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(toast);

        // 触发显示动画
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        // 3秒后自动隐藏
        setTimeout(() => {
            toast.classList.remove('show');
            // 在动画结束后从DOM中移除
            toast.addEventListener('transitionend', () => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, { once: true });
        }, 3000);
    }

    // --- 卡片折叠与高度调整 ---
    const toggleBtn = document.getElementById('toggleDetailsBtn');
    const detailsCard = document.getElementById('conversationDetailsCard');

    if (toggleBtn && detailsCard) {
        function adjustChatHistoryHeight() {
            const chatHistoryCard = document.querySelector('.chat-history-card');
            if (!chatHistoryCard) return;

            const detailsHeight = detailsCard.offsetHeight;
            const windowHeight = window.innerHeight;
            // 适当调整，留出边距
            const newMaxHeight = windowHeight - detailsHeight - 200; 
            chatHistoryCard.querySelector('.message-list').style.maxHeight = `${newMaxHeight}px`;
        }

        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            detailsCard.classList.toggle('collapsed');
            // 在动画结束后调整高度
            setTimeout(adjustChatHistoryHeight, 500); 
        });

        // 初始加载和窗口大小改变时也调整高度
        adjustChatHistoryHeight();
        window.addEventListener('resize', adjustChatHistoryHeight);
    }

    // --- 搜索结果跳转和高亮 ---
    const searchParams = new URLSearchParams(window.location.search);
    const isSearchResult = searchParams.has('search') && searchParams.get('search').length > 0;

    function highlightAndScrollToMessage() {
        const hash = window.location.hash;
        if (hash) {
            const targetId = hash.substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                targetElement.classList.add('highlight');
                setTimeout(() => {
                    targetElement.classList.remove('highlight');
                }, 2500); // 高亮持续2.5秒
            }
        }
    }

    // --- 消息点击逻辑 (详情/跳转/编辑) ---
    const messageList = document.getElementById('messageList');
    if (messageList) {
        messageList.addEventListener('click', function (event) {
            console.log('Click detected on message list.');
            const target = event.target;
            const bubbleContainer = target.closest('.message-bubble-container');
            console.log('Clicked target:', target);
            console.log('Bubble container found:', bubbleContainer);

            if (!bubbleContainer) return;

            // 点击编辑按钮
            if (target.closest('.edit-btn')) {
                event.stopPropagation();
                const dialogId = bubbleContainer.dataset.dialogId;
                console.log('Edit button clicked for dialogId:', dialogId);
                const content = bubbleContainer.dataset.processedContent;
                editMessage(dialogId, content);
                return;
            }

            // 点击消息气泡本身
            if (target.closest('.message-bubble')) {
                // 如果是搜索结果页面，则跳转
                if (isSearchResult) {
                    const msgId = bubbleContainer.id;
                    // 使用字符串拼接来构建 URL
                    const finalUrl = baseUrl + '#' + msgId;
                    window.location.href = finalUrl;
                    return;
                }

                // 否则，打开详情模态框
                console.log('Message bubble clicked, preparing to open detail modal.');
                console.log('Data from container:', JSON.parse(JSON.stringify(bubbleContainer.dataset)));

                // 1. 重置/清空模态框内容
                resetMessageDetailModal();

                // 2. 填充新数据
                const roleText = bubbleContainer.dataset.role === 'user' ? '用户' : 'AI';
                const roleClass = bubbleContainer.dataset.role === 'user' ? 'tag secondary' : 'tag info';

                document.getElementById('modal-role').innerHTML = `<span class="tag ${roleClass}">${roleText}</span>`;
                document.getElementById('modal-turn').textContent = bubbleContainer.dataset.turn;
                document.getElementById('modal-time').textContent = bubbleContainer.dataset.time;
                document.getElementById('modal-msg-id').textContent = bubbleContainer.dataset.msgId || 'N/A';
                document.getElementById('modal-raw-content').textContent = bubbleContainer.dataset.rawContent;

                const editBtn = document.getElementById('editMessageDetailBtn');
                editBtn.onclick = () => {
                    closeModal('messageDetailModal');
                    editMessage(bubbleContainer.dataset.dialogId, bubbleContainer.dataset.processedContent);
                };

                openModal('messageDetailModal');
            }
        });
    }

    /**
     * 重置消息详情模态框的状态，清除所有旧数据。
     */
    function resetMessageDetailModal() {
        console.log('Resetting message detail modal content.');
        document.getElementById('modal-role').innerHTML = '';
        document.getElementById('modal-turn').textContent = '';
        document.getElementById('modal-time').textContent = '';
        document.getElementById('modal-msg-id').textContent = '';
        document.getElementById('modal-raw-content').textContent = '';
        
        // 移除旧的点击事件监听器，防止内存泄漏
        const editBtn = document.getElementById('editMessageDetailBtn');
        const newEditBtn = editBtn.cloneNode(true);
        editBtn.parentNode.replaceChild(newEditBtn, editBtn);
    }

    // --- 消息编辑逻辑 ---

    /**
     * 准备并打开编辑模态框
     * @param {number} dialogId - 数据库中的对话记录ID
     * @param {string} currentContent - 当前处理后的内容
     */
    function editMessage(dialogId, currentContent) {
        console.log(`Preparing edit modal for dialogId: ${dialogId}`);
        currentEditingDialogId = dialogId;
        const textarea = document.getElementById('edit-content');
        textarea.value = currentContent;
        openModal('editMessageModal');
        textarea.focus();
    }

    /**
     * 保存编辑后的消息
     */
    async function saveMessageEdit() {
        if (!currentEditingDialogId) return;

        const newContent = document.getElementById('edit-content').value;
        const convId = conversation.conv_id;

        try {
            const response = await fetch('/api/edit_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    dialog_id: currentEditingDialogId,
                    content: newContent,
                    conv_id: convId
                })
            });

            const result = await response.json();

            if (result.success) {
                // 更新页面上的消息气泡
                const messageContainer = document.querySelector(`[data-dialog-id="${currentEditingDialogId}"]`);
                if (messageContainer) {
                    const contentDiv = messageContainer.querySelector('.message-content');
                    contentDiv.innerHTML = newContent.replace(/\n/g, '<br>');
                    // 更新数据集以便下次编辑
                    messageContainer.dataset.processedContent = newContent;
                }
                closeModal('editMessageModal');
                showToast('保存成功！', 'success');
            } else {
                showToast('保存失败: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('保存消息时出错:', error);
            showToast('保存过程中发生网络错误。', 'error');
        }
    }

    // --- 对话导出功能 ---

    /**
     * 导出当前对话为 JSON 文件
     */
    function exportConversation() {
        const dataStr = JSON.stringify({
            conversation_details: conversation,
            dialogs: dialogs
        }, null, 4);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation_${conversation.conv_id}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // --- 事件绑定 ---
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportConversation);
    }

    const saveEditBtn = document.getElementById('saveEditBtn');
    if (saveEditBtn) {
        saveEditBtn.addEventListener('click', saveMessageEdit);
    }

    // 页面加载时检查并执行高亮
    highlightAndScrollToMessage();

    // 消息详情模态框中的元数据折叠
    const metaContainer = document.querySelector('#messageDetailModal .message-meta-container');
    if (metaContainer) {
        const metaHeader = metaContainer.querySelector('.meta-header');
        metaHeader.addEventListener('click', () => {
            metaContainer.classList.toggle('collapsed');
        });
    }
});
    // --- 对话详情页摘要折叠功能 ---
    const summaryToggleButtons = document.querySelectorAll('.toggle-summary-btn');
    summaryToggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const summaryContainer = this.closest('.collapsible-summary');
            if (summaryContainer) {
                summaryContainer.classList.toggle('collapsed');
            }
        });
    });