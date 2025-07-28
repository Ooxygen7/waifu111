document.addEventListener('DOMContentLoaded', function () {
    // 从 window 对象安全地获取由 Jinja2 模板传递过来的数据
    const conversation = window.conversationData;
    const dialogs = window.dialogsData;
    let currentEditingDialogId = null;

    // --- 模态框和通用UI功能 ---

    /**
     * 打开指定的模态框
     * @param {string} modalId - 模态框的ID
     */
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
            modal.style.visibility = 'visible';
            modal.setAttribute('aria-hidden', 'false');
        }
    }

    /**
     * 关闭指定的模态框
     * @param {string} modalId - 模态框的ID
     */
    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            modal.style.visibility = 'hidden';
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    // 为所有关闭按钮和遮罩层添加关闭事件
    document.querySelectorAll('.modal-close, .modal-overlay, .modal-close-btn').forEach(el => {
        el.addEventListener('click', function (event) {
            // 防止点击模态框内容区域导致关闭
            if (event.target === this || this.classList.contains('modal-close-btn') || this.classList.contains('modal-close')) {
                const modal = this.closest('.modal-overlay');
                if (modal) {
                    closeModal(modal.id);
                }
            }
        });
    });

    // --- 卡片折叠功能 ---
    const toggleBtn = document.getElementById('toggleDetailsBtn');
    const detailsCard = document.getElementById('conversationDetailsCard');

    if (toggleBtn && detailsCard) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // 防止触发其他点击事件
            detailsCard.classList.toggle('collapsed');
        });
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

    // --- 消息点击逻辑 (详情/跳转) ---
    const messageList = document.getElementById('messageList');
    if (messageList) {
        messageList.addEventListener('click', function (event) {
            const bubbleContainer = event.target.closest('.message-bubble-container');
            if (!bubbleContainer) return;

            // 如果点击的是编辑按钮，则不执行后续操作
            if (event.target.closest('.edit-btn')) {
                return;
            }

            // 如果是搜索结果页面，点击则跳转到完整对话并高亮
            if (isSearchResult) {
                const convId = conversation.conv_id;
                const msgId = bubbleContainer.id;
                // 构建 URL 并跳转
                const url = new URL(window.location.origin + `/admin/dialogs/${convId}`);
                url.hash = msgId;
                window.location.href = url.toString();
                return; // 阻止打开详情模态框
            }

            // 正常打开消息详情模态框
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
        });
    }

    // --- 消息编辑逻辑 ---

    /**
     * 准备并打开编辑模态框
     * @param {number} dialogId - 数据库中的对话记录ID
     * @param {string} currentContent - 当前处理后的内容
     */
    function editMessage(dialogId, currentContent) {
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
                const messageContainer = document.getElementById(`msg-${currentEditingDialogId}`);
                if (messageContainer) {
                    const contentDiv = messageContainer.querySelector('.message-content');
                    contentDiv.innerHTML = newContent.replace(/\n/g, '<br>');
                    // 更新数据集以便下次编辑
                    messageContainer.dataset.processedContent = newContent;
                }
                closeModal('editMessageModal');
                // 可以添加一个成功提示，例如使用SweetAlert或自定义通知
            } else {
                alert('保存失败: ' + result.error);
            }
        } catch (error) {
            console.error('保存消息时出错:', error);
            alert('保存过程中发生网络错误。');
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

    // 为所有编辑按钮添加事件监听
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', function (event) {
            event.stopPropagation(); // 阻止事件冒泡到消息气泡容器
            const container = this.closest('.message-bubble-container');
            if (container) {
                const dialogId = container.dataset.dialogId;
                const content = container.dataset.processedContent;
                editMessage(dialogId, content);
            }
        });
    });

    // 页面加载时检查并执行高亮
    highlightAndScrollToMessage();
});