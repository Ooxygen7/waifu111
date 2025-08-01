/**
 * CyberWaifu Bot Admin - Users Page Script
 * Handles modal interactions, data fetching, and form submissions for users.html.
 * This version is refactored to use existing HTML elements instead of dynamic generation.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Bind events to buttons that open modals
    bindModalTriggers();

    // Bind events for actions within the modals (e.g., close, save)
    setupModalEvents();

    // Initialize all custom select components
    initializeCustomSelects();
});

/**
 * Opens a modal and fetches the relevant user data.
 * @param {string} modalId - The ID of the modal to open (e.g., 'userDetailModal').
 * @param {string} userId - The ID of the user to fetch data for.
 */
function openModal(modalId, userId) {
    const modal = document.getElementById(modalId);
    if (!modal) {
        console.error(`Modal with ID ${modalId} not found.`);
        return;
    }

    // Use the .active class from main.css to show the modal
    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Prevent background scrolling

    if (modalId === 'userDetailModal') {
        // We need to implement the data loading for the detail modal
        console.log(`Opening detail modal for user ${userId}`);
        // Placeholder for data loading function
        loadUserDetailData(userId); 
    } else if (modalId === 'userEditModal') {
        loadUserEditData(userId);
    }
}

/**
 * Closes the currently active modal.
 */
function closeModal() {
    const activeModal = document.querySelector('.modal-overlay.active');
    if (activeModal) {
        activeModal.classList.remove('active');
        document.body.style.overflow = ''; // Restore background scrolling
    }
}

/**
 * Binds click events to all buttons that should open a modal.
 */
function bindModalTriggers() {
    // Use event delegation on the body for all modal triggers
    document.body.addEventListener('click', function(e) {
        const viewBtn = e.target.closest('.view-user-btn');
        const editBtn = e.target.closest('.edit-user-btn');

        if (viewBtn) {
            e.preventDefault();
            const userId = viewBtn.dataset.uid;
            if (userId) {
                openModal('userDetailModal', userId);
            }
            return; // Stop further processing
        }

        if (editBtn) {
            e.preventDefault();
            const userId = editBtn.dataset.uid;
            if (userId) {
                openModal('userEditModal', userId);
            }
        }
    });
}

/**
 * Sets up event listeners for elements within the modals, like close buttons and forms.
 */
function setupModalEvents() {
    // Use event delegation for close buttons for robustness
    document.addEventListener('click', function(e) {
        // If the clicked element or its parent has the class 'modal-close'
        if (e.target.matches('.modal-close') || e.target.closest('.modal-close')) {
            closeModal();
        }
        // If a secondary button (often 'Cancel') is clicked
        if (e.target.matches('.modal-footer .btn-secondary')) {
            closeModal();
        }
    });

    // Close modal when clicking on the overlay background
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });
    });

    // Close modal on Escape key press
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });

    // Handle the edit form submission
    const userEditForm = document.getElementById('userEditForm');
    if (userEditForm) {
        // The primary button in the footer now triggers the save function
        const saveButton = document.querySelector('#userEditModal .btn-primary');
        if (saveButton) {
            saveButton.addEventListener('click', function(e) {
                e.preventDefault();
                const userId = document.getElementById('editUserId').value;
                if (userId) {
                    saveUserChanges(userId);
                } else {
                    console.error("No user ID found in edit form.");
                }
            });
        }
    }
}

/**
 * Fetches and displays data for the User Detail modal.
 * @param {string} userId - The user's ID.
 */
function loadUserDetailData(userId) {
    const modal = document.getElementById('userDetailModal');
    const contentDiv = modal.querySelector('#userDetailContent');
    const loadingDiv = contentDiv.querySelector('.loading-state');

    loadingDiv.style.display = 'flex'; // Use flex for centering
    contentDiv.innerHTML = ''; // Clear previous content
    contentDiv.appendChild(loadingDiv);

    fetch(`/api/user/${userId}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch user details.');
            return response.json();
        })
        .then(data => {
            loadingDiv.style.display = 'none';
            contentDiv.innerHTML = createUserDetailHtml(data);
        })
        .catch(error => {
            console.error('Error loading user details:', error);
            contentDiv.innerHTML = `<div class="error-state">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                <h3>无法加载用户数据</h3>
                <p>${error.message}</p>
            </div>`;
        });
}

/**
 * Creates the HTML for the user detail view based on user data.
 * @param {object} data - The user data object from the API.
 * @returns {string} - The HTML string for the user detail content.
 */
function createUserDetailHtml(data) {
    const user = data.user;
    const config = data.config || {};
    const profiles = data.profiles || [];
    const fullName = ((user.first_name || '') + ' ' + (user.last_name || '')).trim();

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    };
    
    const getTierBadge = (tier) => {
        if (tier === 1) return `<span class="badge warning">VIP</span>`;
        if (tier === 2) return `<span class="badge danger">SVIP</span>`;
        return `<span class="badge secondary">普通</span>`;
    };

    const formatLargeNumber = (num) => {
        if (num === null || num === undefined) return '0';
        if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
        return num.toString();
    };

    return `
        <div class="user-detail-grid">
            <div class="detail-card profile-card">
                <div class="profile-header">
                    <div class="profile-avatar">
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                    </div>
                    <div class="profile-info">
                        <h4 class="profile-name">${fullName || user.user_name}</h4>
                        <p class="profile-username">@${user.user_name || 'N/A'}</p>
                    </div>
                    <div class="profile-tier">
                        ${getTierBadge(user.account_tier)}
                    </div>
                </div>
                <div class="profile-body">
                    <div class="info-item">
                        <span class="info-label">用户 ID:</span>
                        <span class="info-value user-id-mono">${user.uid}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">昵称:</span>
                        <span class="info-value">${config.nick || '未设置'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">注册于:</span>
                        <span class="info-value">${formatDate(user.create_at)}</span>
                    </div>
                </div>
            </div>

            <div class="detail-card stats-card">
                <h5 class="card-title">账户统计</h5>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-value">¥${(user.balance || 0).toFixed(2)}</span>
                        <span class="stat-label">余额</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${formatLargeNumber(user.remain_frequency)}</span>
                        <span class="stat-label">剩余额度</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${formatLargeNumber(user.conversations)}</span>
                        <span class="stat-label">总对话</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${formatLargeNumber(user.dialog_turns)}</span>
                        <span class="stat-label">总轮数</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${formatLargeNumber(user.input_tokens)}</span>
                        <span class="stat-label">输入 Tokens</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${formatLargeNumber(user.output_tokens)}</span>
                        <span class="stat-label">输出 Tokens</span>
                    </div>
                </div>
            </div>

            <div class="detail-card config-card">
                <h5 class="card-title">高级配置</h5>
                <div class="config-grid">
                    <div class="config-item">
                        <span class="config-label">角色 (char):</span>
                        <span class="config-value">${config.char || '默认'}</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">预设 (preset):</span>
                        <span class="config-value">${config.preset || '默认'}</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">API:</span>
                        <span class="config-value">${config.api || '默认'}</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">流式传输 (stream):</span>
                        <span class="config-value">${config.stream !== null ? config.stream : '默认'}</span>
                    </div>
                </div>
            </div>

            ${profiles.length > 0 ? `
            <div class="detail-card-full-width user-profiles-card">
                <h5 class="card-title">
                   <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                   用户画像
                </h5>
                <div class="profiles-content">
                    ${profiles.map(profile => `
                        <div class="profile-item">
                            <div class="profile-item-header">
                                <span class="badge secondary">群组: ${profile.group_id}</span>
                            </div>
                            <div class="profile-item-body">
                                <p>${profile.user_profile}</p>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}

        </div>
    `;
}


/**
 * Fetches and populates data for the User Edit modal form.
 * @param {string} userId - The user's ID.
 */
function loadUserEditData(userId) {
    // Set the hidden user ID field first
    document.getElementById('editUserId').value = userId;

    fetch(`/api/user/${userId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch user data for editing.');
            }
            return response.json();
        })
        .then(data => {
            const user = data.user;
            const config = data.config || {};

            // Populate the form fields
            document.getElementById('editUserName').value = user.user_name || '';
            document.getElementById('editFirstName').value = user.first_name || '';
            document.getElementById('editLastName').value = user.last_name || '';
            document.getElementById('editNick').value = config.nick || '';
            document.getElementById('editAccountTier').value = user.account_tier !== null ? user.account_tier : '0';
            // Manually trigger the update for the custom select to reflect the new value
            updateCustomSelectDisplay(document.getElementById('editAccountTier'));
            document.getElementById('editRemainFrequency').value = user.remain_frequency !== null ? user.remain_frequency : '0';
            document.getElementById('editBalance').value = user.balance !== null ? user.balance.toFixed(2) : '0.00';
            document.getElementById('editChar').value = config.char || '';
            document.getElementById('editPreset').value = config.preset || '';
            document.getElementById('editApi').value = config.api || '';
            document.getElementById('editStream').value = config.stream || '';
        })
        .catch(error => {
            console.error('Error loading user data for edit:', error);
            // Optionally, show an error message in the modal
            alert('Could not load user data. Please try again.');
            closeModal();
        });
}

/**
 * Collects data from the edit form and sends it to the server.
 * @param {string} userId - The ID of the user being saved.
 */
function saveUserChanges(userId) {
    const form = document.getElementById('userEditForm');
    const saveButton = document.querySelector('#userEditModal .btn-primary');
    
    const originalButtonText = saveButton.innerHTML;
    saveButton.disabled = true;
    saveButton.innerHTML = `
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        Saving...
    `;

    const formData = {
        user_id: userId,
        user_name: form.querySelector('#editUserName').value,
        first_name: form.querySelector('#editFirstName').value,
        last_name: form.querySelector('#editLastName').value,
        nick: form.querySelector('#editNick').value,
        account_tier: parseInt(form.querySelector('#editAccountTier').value, 10),
        remain_frequency: parseInt(form.querySelector('#editRemainFrequency').value, 10),
        balance: parseFloat(form.querySelector('#editBalance').value),
        config: {
            char: form.querySelector('#editChar').value,
            preset: form.querySelector('#editPreset').value,
            api: form.querySelector('#editApi').value,
            stream: form.querySelector('#editStream').value,
        }
    };

    fetch(`/api/user/${userId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.json();
    })
    .then(data => {
        console.log('Save successful:', data);
        closeModal();
        // Optionally, show a success notification
        alert('User updated successfully!');
        window.location.reload(); // Reload to see changes
    })
    .catch(error => {
        console.error('Save failed:', error);
        // Optionally, display errors in the form
        alert(`Error saving user: ${error.message || 'Unknown error'}`);
    })
    .finally(() => {
        saveButton.disabled = false;
        saveButton.innerHTML = originalButtonText;
    });
}

/**
 * Initializes all custom select components on the page.
 */
function initializeCustomSelects() {
    document.querySelectorAll('.custom-select-wrapper').forEach(wrapper => {
        const trigger = wrapper.querySelector('.custom-select-trigger');
        const customSelect = wrapper.querySelector('.custom-select');
        const originalSelect = wrapper.querySelector('.original-select');
        const customOptions = wrapper.querySelectorAll('.custom-option');

        // Toggle dropdown on trigger click
        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            // Close all other open selects
            document.querySelectorAll('.custom-select.open').forEach(openSelect => {
                if (openSelect !== customSelect) {
                    openSelect.classList.remove('open');
                }
            });
            customSelect.classList.toggle('open');
        });

        // Handle option selection
        customOptions.forEach(option => {
            option.addEventListener('click', function() {
                const selectedValue = this.getAttribute('data-value');
                const selectedText = this.textContent;

                // Update the hidden native select
                originalSelect.value = selectedValue;

                // Update the trigger text
                trigger.querySelector('span').textContent = selectedText;

                // Update selected class
                customOptions.forEach(opt => opt.classList.remove('selected'));
                this.classList.add('selected');

                // Close the dropdown
                customSelect.classList.remove('open');
            });
        });
    });

    // Close dropdown when clicking outside
    window.addEventListener('click', () => {
        document.querySelectorAll('.custom-select.open').forEach(select => {
            select.classList.remove('open');
        });
    });
}

/**
 * Updates the display of a custom select component based on the value of its
 * underlying original select element.
 * @param {HTMLElement} originalSelect - The original <select> element.
 */
function updateCustomSelectDisplay(originalSelect) {
    const wrapper = originalSelect.closest('.custom-select-wrapper');
    if (!wrapper) return;

    const trigger = wrapper.querySelector('.custom-select-trigger span');
    const customOptions = wrapper.querySelectorAll('.custom-option');
    const selectedValue = originalSelect.value;
    
    let selectedText = '';

    customOptions.forEach(option => {
        option.classList.remove('selected');
        if (option.getAttribute('data-value') === selectedValue) {
            option.classList.add('selected');
            selectedText = option.textContent;
        }
    });

    if (trigger) {
        trigger.textContent = selectedText || 'Select an option';
    }
}