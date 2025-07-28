document.addEventListener('DOMContentLoaded', function () {
    // --- Modal Handling ---
    const editGroupModal = document.getElementById('editGroupModal');
    const viewGroupModal = document.getElementById('viewGroupModal');
    const editForm = document.getElementById('editGroupForm');

    function openModal(modal) {
        if (modal) {
            modal.style.display = 'flex';
            setTimeout(() => modal.classList.add('show'), 10);
        }
    }

    function closeModal(modal) {
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300); // Match CSS transition duration
        }
    }

    // Close modal event listeners
    document.querySelectorAll('.modal-close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            closeModal(editGroupModal);
            closeModal(viewGroupModal);
        });
    });

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeModal(editGroupModal);
                closeModal(viewGroupModal);
            }
        });
    });
    
    // --- Data Fetching and API Calls ---
    
    // Fetch group data to populate the form for editing
    async function fetchGroupData(groupId) {
        try {
            const response = await fetch(`/api/groups/${groupId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (data.success) {
                return data.group;
            } else {
                throw new Error(data.message || 'Failed to fetch group data.');
            }
        } catch (error) {
            console.error('Error fetching group data:', error);
            // You might want to show a notification to the user here
            return null;
        }
    }

    // --- Edit Group Functionality ---

    // Populate the edit form with fetched data
    function populateEditForm(group) {
        if (!group) return;
        editForm.querySelector('#editGroupId').value = group.group_id;
        editForm.querySelector('#editGroupName').value = group.group_name || '';
        editForm.querySelector('#editActive').value = group.active ? '1' : '0';
        editForm.querySelector('#editRate').value = group.rate || 0;
        editForm.querySelector('#editChar').value = group.char || '';
        editForm.querySelector('#editApi').value = group.api || '';
        editForm.querySelector('#editPreset').value = group.preset || '';
        editForm.querySelector('#editKeywords').value = group.keywords || '';
        editForm.querySelector('#editDisabledTopics').value = group.disabled_topics || '';
    }

    // Handle edit button clicks
    document.querySelectorAll('.edit-group-btn').forEach(button => {
        button.addEventListener('click', async (e) => {
            const groupId = e.currentTarget.closest('tr').dataset.groupId;
            const groupData = await fetchGroupData(groupId);
            if (groupData) {
                populateEditForm(groupData);
                openModal(editGroupModal);
            }
        });
    });

    // Handle form submission
    editForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const saveButton = editForm.querySelector('button[type="submit"]');
        const spinner = saveButton.querySelector('.spinner');
        const btnText = saveButton.querySelector('.btn-text');

        saveButton.disabled = true;
        spinner.style.display = 'inline-block';
        btnText.style.display = 'none';

        const formData = new FormData(editForm);
        const data = Object.fromEntries(formData.entries());
        
        // Ensure numeric types are correct
        data.active = parseInt(data.active, 10);
        data.rate = parseFloat(data.rate);

        try {
            const response = await fetch(`/api/groups/${data.group_id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            if (result.success) {
                closeModal(editGroupModal);
                // Optionally, show a success notification
                location.reload(); // Reload to see changes
            } else {
                throw new Error(result.message || 'Failed to save changes.');
            }
        } catch (error) {
            console.error('Error saving group changes:', error);
            // Optionally, show an error notification
        } finally {
            saveButton.disabled = false;
            spinner.style.display = 'none';
            btnText.style.display = 'inline-block';
        }
    });

    // --- View Group Detail Functionality ---

    function renderGroupDetails(group) {
        const contentContainer = viewGroupModal.querySelector('#viewGroupContent');
        if (!group) {
            contentContainer.innerHTML = `<div class="error-state"><p>无法加载群组信息。</p></div>`;
            return;
        }

        const keywords = group.keywords ? group.keywords.split(',').map(k => `<span class="badge secondary">${k.trim()}</span>`).join('') : '<span class="text-muted">无</span>';
        const disabledTopics = group.disabled_topics ? group.disabled_topics.split(',').map(t => `<span class="badge danger">${t.trim()}</span>`).join('') : '<span class="text-muted">无</span>';

        const html = `
            <div class="user-detail-grid">
                <div class="detail-card profile-card">
                    <h4 class="card-title">基本信息</h4>
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
                        <span class="info-value">${new Date(group.update_time).toLocaleString()}</span>
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
                        <div class="config-item">
                            <span class="config-label">角色:</span>
                            <span class="config-value">${group.char || 'N/A'}</span>
                        </div>
                        <div class="config-item">
                            <span class="config-label">API:</span>
                            <span class="config-value">${group.api || 'N/A'}</span>
                        </div>
                        <div class="config-item">
                            <span class="config-label">预设:</span>
                            <span class="config-value">${group.preset || 'N/A'}</span>
                        </div>
                    </div>
                     <div class="mt-3">
                        <h5 class="config-label">关键词:</h5>
                        <div class="config-value-box">${keywords}</div>
                    </div>
                    <div class="mt-3">
                        <h5 class="config-label">禁用话题:</h5>
                        <div class="config-value-box">${disabledTopics}</div>
                    </div>
                </div>
            </div>
        `;
        contentContainer.innerHTML = html;
        
        // Update dialogs link
        const dialogsLink = viewGroupModal.querySelector('#viewGroupDialogsLink');
        if(dialogsLink) {
            dialogsLink.href = `/admin/group_dialogs?group_id=${group.group_id}`;
        }
    }

    // Handle view button clicks
    document.querySelectorAll('.view-group-btn').forEach(button => {
        button.addEventListener('click', async (e) => {
            const groupId = e.currentTarget.closest('tr').dataset.groupId;
            const contentContainer = viewGroupModal.querySelector('#viewGroupContent');
            
            // Show loading state
            contentContainer.innerHTML = `
                <div class="loading-state active">
                    <div class="spinner"></div>
                    <p>正在加载群组数据...</p>
                </div>`;
            openModal(viewGroupModal);

            const groupData = await fetchGroupData(groupId);
            renderGroupDetails(groupData);
        });
    });
});