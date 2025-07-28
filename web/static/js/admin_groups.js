/**
 * CyberWaifu Bot Admin - Groups Page Script
 * Handles modal interactions, data fetching, and form submissions for groups.html.
 * This version is refactored to support dynamic data loading for single modal instances.
 */

document.addEventListener('DOMContentLoaded', function () {
    // Bind events to buttons that open modals
    bindModalTriggers();

    // Bind events for actions within the modals (e.g., close, save)
    setupModalEvents();

    // Initialize all custom select components
    initializeCustomSelects();
});

/**
 * Opens a modal and fetches the relevant group data.
 * @param {string} modalId - The ID of the modal to open.
 * @param {string} groupId - The ID of the group to fetch data for.
 */
function openModal(modalId, groupId) {
    const modal = document.getElementById(modalId);
    if (!modal) {
        console.error(`Modal with ID ${modalId} not found.`);
        return;
    }

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    if (modalId === 'groupDetailModal') {
        loadGroupDetailData(groupId);
    } else if (modalId === 'groupEditModal') {
        loadGroupEditData(groupId);
    }
}

/**
 * Closes the currently active modal.
 */
function closeModal() {
    const activeModal = document.querySelector('.modal-overlay.active');
    if (activeModal) {
        activeModal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

/**
 * Binds click events to all buttons that should open a modal using event delegation.
 */
function bindModalTriggers() {
    document.body.addEventListener('click', function (e) {
        const viewBtn = e.target.closest('.view-group-btn');
        const editBtn = e.target.closest('.edit-group-btn');

        if (viewBtn) {
            e.preventDefault();
            const groupId = viewBtn.dataset.groupId;
            if (groupId) {
                openModal('groupDetailModal', groupId);
            }
            return;
        }

        if (editBtn) {
            e.preventDefault();
            const groupId = editBtn.dataset.groupId;
            if (groupId) {
                openModal('groupEditModal', groupId);
            }
        }
    });
}

/**
 * Sets up event listeners for elements within the modals.
 */
function setupModalEvents() {
    document.addEventListener('click', function (e) {
        if (e.target.matches('.modal-close') || e.target.closest('.modal-close')) {
            closeModal();
        }
    });

    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', function (e) {
            if (e.target === this) {
                closeModal();
            }
        });
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });

    const saveButton = document.getElementById('saveGroupChangesBtn');
    if (saveButton) {
        saveButton.addEventListener('click', function (e) {
            e.preventDefault();
            const groupId = document.getElementById('editGroupId').value;
            if (groupId) {
                saveGroupChanges(groupId);
            } else {
                console.error("No group ID found in edit form.");
            }
        });
    }
}

/**
 * Fetches and displays data for the Group Detail modal.
 * @param {string} groupId - The group's ID.
 */
function loadGroupDetailData(groupId) {
    const modal = document.getElementById('groupDetailModal');
    const contentDiv = modal.querySelector('#groupDetailContent');
    const loadingDiv = contentDiv.querySelector('.loading-state');
    const dialogsBtn = document.getElementById('viewGroupDialogsBtn');

    loadingDiv.style.display = 'flex';
    // Clear previous content but keep the loading state element
    contentDiv.innerHTML = '';
    contentDiv.appendChild(loadingDiv);
    dialogsBtn.href = '#'; // Reset button link

    fetch(`/api/groups/${groupId}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch group details.');
            return response.json();
        })
        .then(data => {
            loadingDiv.style.display = 'none';
            contentDiv.innerHTML = createGroupDetailHtml(data);
            dialogsBtn.href = `/admin/group_dialogs/${groupId}`;
        })
        .catch(error => {
            console.error('Error loading group details:', error);
            contentDiv.innerHTML = `<div class="error-state"><h3>无法加载群组数据</h3><p>${error.message}</p></div>`;
        });
}

/**
 * Creates the HTML for the group detail view.
 * @param {object} group - The group data object from the API.
 * @returns {string} - The HTML string for the group detail content.
 */
function createGroupDetailHtml(group) {
    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    };

    const createBadges = (items, type = 'secondary') => {
        if (!items) return `<span class="text-muted">无</span>`;
        return items.split(',')
            .map(item => `<span class="badge ${type}">${item.trim()}</span>`)
            .join(' ');
    };

    return `
        <div class="user-detail-grid">
            <div class="detail-card profile-card">
                <h4 class="card-title">基本信息</h4>
                <div class="profile-body">
                    <div class="info-item">
                        <span class="info-label">群组 ID:</span>
                        <span class="info-value user-id-mono">#${group.group_id}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">群组名称:</span>
                        <span class="info-value">${group.group_name || '未命名'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">状态:</span>
                        <span class="info-value">${group.active ? '<span class="badge success">活跃</span>' : '<span class="badge danger">非活跃</span>'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">更新于:</span>
                        <span class="info-value">${formatDate(group.update_time)}</span>
                    </div>
                </div>
            </div>
            <div class="detail-card stats-card">
                <h4 class="card-title">核心统计</h4>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-value">${group.call_count || 0}</span>
                        <span class="stat-label">调用次数</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${((group.rate || 0) * 100).toFixed(1)}%</span>
                        <span class="stat-label">触发几率</span>
                    </div>
                </div>
            </div>
            <div class="detail-card config-card">
                <h4 class="card-title">配置与规则</h4>
                <div class="config-grid">
                    <div class="config-item"><span class="config-label">角色:</span><span class="config-value">${group.char || 'N/A'}</span></div>
                    <div class="config-item"><span class="config-label">API:</span><span class="config-value">${group.api || 'N/A'}</span></div>
                    <div class="config-item"><span class="config-label">预设:</span><span class="config-value">${group.preset || 'N/A'}</span></div>
                </div>
                <div class="mt-3">
                    <h5 class="config-label">关键词:</h5>
                    <div class="config-value-box">${createBadges(group.keywords)}</div>
                </div>
                <div class="mt-3">
                    <h5 class="config-label">禁用话题:</h5>
                    <div class="config-value-box">${createBadges(group.disabled_topics, 'danger')}</div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Fetches and populates data for the Group Edit modal form.
 * @param {string} groupId - The group's ID.
 */
function loadGroupEditData(groupId) {
    document.getElementById('editGroupId').value = groupId;

    fetch(`/api/groups/${groupId}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch group data for editing.');
            return response.json();
        })
        .then(group => {
            document.getElementById('editGroupName').value = group.group_name || '';
            const activeSelect = document.getElementById('editActive');
            activeSelect.value = group.active ? '1' : '0';
            updateCustomSelectDisplay(activeSelect);
            document.getElementById('editRate').value = group.rate || 0;
            document.getElementById('editChar').value = group.char || '';
            document.getElementById('editApi').value = group.api || '';
            document.getElementById('editPreset').value = group.preset || '';
            document.getElementById('editKeywords').value = group.keywords || '';
            document.getElementById('editDisabledTopics').value = group.disabled_topics || '';
        })
        .catch(error => {
            console.error('Error loading group data for edit:', error);
            alert('无法加载群组数据，请重试。');
            closeModal();
        });
}

/**
 * Collects data from the edit form and sends it to the server.
 * @param {string} groupId - The ID of the group being saved.
 */
function saveGroupChanges(groupId) {
    const form = document.getElementById('groupEditForm');
    const saveButton = document.getElementById('saveGroupChangesBtn');
    const originalButtonHtml = saveButton.innerHTML;

    saveButton.disabled = true;
    saveButton.innerHTML = `<div class="loading-spinner" style="width: 20px; height: 20px; border-width: 2px;"></div>`;

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    data.active = parseInt(data.active, 10);
    data.rate = parseFloat(data.rate);

    fetch(`/api/groups/${groupId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
        .then(response => {
            if (!response.ok) return response.json().then(err => Promise.reject(err));
            return response.json();
        })
        .then(data => {
            if (data.success) {
                closeModal();
                location.reload();
            } else {
                throw new Error(data.message || '保存失败');
            }
        })
        .catch(error => {
            console.error('Save failed:', error);
            alert(`保存失败: ${error.message || '未知错误'}`);
        })
        .finally(() => {
            saveButton.disabled = false;
            saveButton.innerHTML = originalButtonHtml;
        });
}

/**
 * Initializes all custom select components on the page.
 */
function initializeCustomSelects() {
    document.querySelectorAll('.custom-select-wrapper').forEach(wrapper => {
        // If custom select already exists, skip
        if (wrapper.querySelector('.custom-select')) return;

        const originalSelect = wrapper.querySelector('.original-select');
        if (!originalSelect) return;

        const customSelect = document.createElement('div');
        customSelect.className = 'custom-select';

        const trigger = document.createElement('div');
        trigger.className = 'custom-select-trigger';
        trigger.innerHTML = `<span></span><div class="arrow-container"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg></div>`;

        const options = document.createElement('div');
        options.className = 'custom-options';

        Array.from(originalSelect.options).forEach(option => {
            const customOption = document.createElement('div');
            customOption.className = 'custom-option';
            customOption.dataset.value = option.value;
            customOption.innerHTML = `<span>${option.textContent}</span>`;
            options.appendChild(customOption);
        });

        customSelect.appendChild(trigger);
        customSelect.appendChild(options);
        wrapper.appendChild(customSelect);

        updateCustomSelectDisplay(originalSelect); // Set initial value

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.custom-select.open').forEach(openSelect => {
                if (openSelect !== customSelect) openSelect.classList.remove('open');
            });
            customSelect.classList.toggle('open');
        });

        options.querySelectorAll('.custom-option').forEach(option => {
            option.addEventListener('click', function () {
                originalSelect.value = this.dataset.value;
                updateCustomSelectDisplay(originalSelect);
                customSelect.classList.remove('open');
            });
        });
    });

    window.addEventListener('click', () => {
        document.querySelectorAll('.custom-select.open').forEach(select => {
            select.classList.remove('open');
        });
    });
}

/**
 * Updates the display of a custom select component.
 * @param {HTMLElement} originalSelect - The original <select> element.
 */
function updateCustomSelectDisplay(originalSelect) {
    const wrapper = originalSelect.closest('.custom-select-wrapper');
    if (!wrapper) return;

    const triggerSpan = wrapper.querySelector('.custom-select-trigger span');
    const customOptions = wrapper.querySelectorAll('.custom-option');
    const selectedValue = originalSelect.value;

    let selectedText = 'Select an option';
    if (originalSelect.selectedOptions.length > 0) {
        selectedText = originalSelect.selectedOptions[0].textContent;
    }

    if (triggerSpan) triggerSpan.textContent = selectedText;

    customOptions.forEach(option => {
        option.classList.toggle('selected', option.dataset.value === selectedValue);
    });
}