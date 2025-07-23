/**
 * User Table Interactions
 * 用户表格交互功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化用户表格交互
    initUserTableInteractions();
    
    // 初始化统计卡片动画
    initStatsCardAnimations();
    
    // 初始化用户详情模态框
    initUserDetailModal();
});

/**
 * 初始化用户表格交互
 */
function initUserTableInteractions() {
    const userRows = document.querySelectorAll('.table-row-interactive');
    
    userRows.forEach(row => {
        // 添加行悬停效果
        row.addEventListener('mouseenter', function() {
            // 高亮用户头像
            const avatar = this.querySelector('.user-avatar');
            if (avatar) {
                avatar.style.transform = 'scale(1.15) rotate(5deg)';
                avatar.style.boxShadow = '0 6px 12px rgba(0, 0, 0, 0.1)';
            }
            
            // 高亮用户名
            const userName = this.querySelector('.user-name');
            if (userName) {
                userName.style.color = 'var(--primary-color)';
                userName.style.transform = 'translateY(-1px)';
            }
            
            // 高亮统计徽章
            const statValues = this.querySelectorAll('.stat-value');
            statValues.forEach(stat => {
                stat.style.transform = 'translateY(-2px) scale(1.05)';
                stat.style.color = 'var(--primary-dark)';
            });
            
            // 高亮操作按钮
            const actionButtons = this.querySelectorAll('.btn-icon');
            actionButtons.forEach(btn => {
                btn.style.opacity = '1';
                btn.style.transform = 'scale(1.05)';
            });
            
            // 添加行左侧边框效果
            this.style.borderLeft = '3px solid var(--primary-color)';
            this.style.paddingLeft = 'calc(var(--spacing-md) - 3px)';
        });
        
        // 鼠标离开效果
        row.addEventListener('mouseleave', function() {
            // 恢复用户头像
            const avatar = this.querySelector('.user-avatar');
            if (avatar) {
                avatar.style.transform = '';
                avatar.style.boxShadow = '';
            }
            
            // 恢复用户名
            const userName = this.querySelector('.user-name');
            if (userName) {
                userName.style.color = '';
                userName.style.transform = '';
            }
            
            // 恢复统计徽章
            const statValues = this.querySelectorAll('.stat-value');
            statValues.forEach(stat => {
                stat.style.transform = '';
                stat.style.color = '';
            });
            
            // 恢复操作按钮
            const actionButtons = this.querySelectorAll('.btn-icon');
            actionButtons.forEach(btn => {
                btn.style.opacity = '';
                btn.style.transform = '';
            });
            
            // 移除行左侧边框效果
            this.style.borderLeft = '';
            this.style.paddingLeft = '';
        });
        
        // 行点击事件
        row.addEventListener('click', function(e) {
            // 如果点击的是链接或按钮，不触发行点击
            if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || 
                e.target.closest('a') || e.target.closest('button')) {
                return;
            }
            
            // 添加点击波纹效果
            const ripple = document.createElement('div');
            ripple.className = 'table-row-ripple';
            ripple.style.position = 'absolute';
            ripple.style.width = '20px';
            ripple.style.height = '20px';
            ripple.style.borderRadius = '50%';
            ripple.style.backgroundColor = 'rgba(79, 172, 254, 0.3)';
            ripple.style.transform = 'scale(0)';
            ripple.style.animation = 'ripple 0.6s linear';
            ripple.style.left = e.clientX - this.getBoundingClientRect().left + 'px';
            ripple.style.top = e.clientY - this.getBoundingClientRect().top + 'px';
            
            this.style.overflow = 'hidden';
            this.style.position = 'relative';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
            
            // 获取用户ID
            const userIdElement = this.querySelector('.user-id');
            if (userIdElement) {
                const userId = userIdElement.textContent.trim();
                showUserDetailModal(userId);
            }
        });
        
        // 添加键盘导航支持
        row.setAttribute('tabindex', '0');
        row.setAttribute('role', 'button');
        row.setAttribute('aria-label', '查看用户详情');
        
        row.addEventListener('keydown', function(e) {
            // 回车或空格键触发点击
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const userIdElement = this.querySelector('.user-id');
                if (userIdElement) {
                    const userId = userIdElement.textContent.trim();
                    showUserDetailModal(userId);
                }
            }
        });
    });
    
    // 添加详情按钮点击事件
    const detailButtons = document.querySelectorAll('button.btn-icon[title="查看详情"]');
    console.log('找到详情按钮数量:', detailButtons.length); // 调试信息
    
    detailButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault(); // 阻止默认行为
            e.stopPropagation(); // 阻止事件冒泡
            
            console.log('详情按钮被点击'); // 调试信息
            
            // 添加按钮点击效果
            this.classList.add('btn-clicked');
            setTimeout(() => {
                this.classList.remove('btn-clicked');
            }, 300);
            
            const row = this.closest('tr');
            const userIdElement = row.querySelector('.user-id');
            if (userIdElement) {
                const userId = userIdElement.textContent.trim();
                console.log('用户ID:', userId); // 调试信息
                showUserDetailModal(userId);
            }
        });
        
        // 添加工具提示
        button.setAttribute('aria-label', '查看用户详情');
    });
    
    // 添加表格头部排序指示器效果
    const sortLinks = document.querySelectorAll('.sort-link');
    sortLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            const indicator = this.querySelector('.sort-indicator');
            if (indicator) {
                indicator.style.transform = 'scale(1.1)';
                indicator.style.opacity = '1';
            }
        });
        
        link.addEventListener('mouseleave', function() {
            const indicator = this.querySelector('.sort-indicator');
            if (indicator) {
                indicator.style.transform = '';
                indicator.style.opacity = '';
            }
        });
    });
    
    // 添加CSS动画样式
    if (!document.getElementById('table-animations-style')) {
        const style = document.createElement('style');
        style.id = 'table-animations-style';
        style.textContent = `
            @keyframes ripple {
                0% {
                    transform: scale(0);
                    opacity: 1;
                }
                100% {
                    transform: scale(40);
                    opacity: 0;
                }
            }
            
            .btn-clicked {
                animation: button-pulse 0.3s ease;
            }
            
            @keyframes button-pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.2); }
                100% { transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * 初始化统计卡片动画
 */
function initStatsCardAnimations() {
    const statCards = document.querySelectorAll('.stat-card');
    const statValues = document.querySelectorAll('.stat-value');
    
    // 添加入场动画
    statCards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            // 强制重绘
            void card.offsetWidth;
            
            // 添加过渡
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
        
        // 添加悬停效果
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.02)';
            this.style.boxShadow = '0 8px 16px rgba(0, 0, 0, 0.1)';
            
            // 获取图标并添加动画
            const icon = this.querySelector('.stat-icon');
            if (icon) {
                icon.style.transform = 'scale(1.1)';
            }
            
            // 获取数值并添加动画
            const value = this.querySelector('.stat-value');
            if (value) {
                value.style.transform = 'scale(1.05)';
                value.style.backgroundSize = '200% 200%';
                value.style.animation = 'gradient-shift 2s ease infinite';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
            
            // 恢复图标
            const icon = this.querySelector('.stat-icon');
            if (icon) {
                icon.style.transform = '';
            }
            
            // 恢复数值
            const value = this.querySelector('.stat-value');
            if (value) {
                value.style.transform = '';
                value.style.backgroundSize = '';
                value.style.animation = '';
            }
        });
    });
    
    // 添加数字动画
    statValues.forEach((value, index) => {
        setTimeout(() => {
            animateNumber(value);
        }, 500 + index * 100);
    });
    
    // 刷新按钮点击事件
    const refreshButton = document.querySelector('.refresh-stats');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            // 添加加载动画
            this.classList.add('loading');
            
            // 添加旋转动画
            this.querySelector('svg').style.animation = 'spin 1s linear infinite';
            
            // 重置统计值
            statValues.forEach(value => {
                value.dataset.finalValue = value.textContent;
                value.textContent = '0';
            });
            
            // 模拟加载延迟
            setTimeout(() => {
                // 重新触发数字动画
                statValues.forEach((value, index) => {
                    setTimeout(() => {
                        value.textContent = value.dataset.finalValue;
                        animateNumber(value);
                        
                        // 添加闪烁效果
                        value.style.animation = 'flash 0.5s ease';
                        setTimeout(() => {
                            value.style.animation = '';
                        }, 500);
                    }, index * 100);
                });
                
                // 移除加载动画
                setTimeout(() => {
                    refreshButton.classList.remove('loading');
                    refreshButton.querySelector('svg').style.animation = '';
                }, 500);
            }, 800);
        });
    }
    
    // 添加CSS动画样式
    if (!document.getElementById('stats-animations-style')) {
        const style = document.createElement('style');
        style.id = 'stats-animations-style';
        style.textContent = `
            @keyframes gradient-shift {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            
            @keyframes flash {
                0% { opacity: 0.5; }
                50% { opacity: 1; transform: scale(1.1); }
                100% { opacity: 1; transform: scale(1); }
            }
            
            @keyframes float {
                0% { transform: translateY(0px); }
                50% { transform: translateY(-5px); }
                100% { transform: translateY(0px); }
            }
            
            .stats-card:hover .stat-card {
                animation: float 3s ease-in-out infinite;
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * 数字动画效果
 * @param {HTMLElement} element - 包含数字的元素
 */
function animateNumber(element) {
    const finalValue = parseInt(element.textContent.replace(/,/g, ''), 10);
    if (isNaN(finalValue)) return;
    
    let startValue = 0;
    const duration = 1500;
    const startTime = performance.now();
    
    function easeOutExpo(t) {
        return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
    }
    
    function updateNumber(currentTime) {
        const elapsedTime = currentTime - startTime;
        
        if (elapsedTime < duration) {
            const progress = easeOutExpo(elapsedTime / duration);
            const currentValue = Math.round(progress * finalValue);
            
            element.textContent = currentValue;
            requestAnimationFrame(updateNumber);
        } else {
            element.textContent = finalValue;
        }
    }
    
    requestAnimationFrame(updateNumber);
}

/**
 * 初始化用户详情模态框
 */
function initUserDetailModal() {
    // 检查是否已存在模态框样式
    if (!document.getElementById('user-modal-styles')) {
        const style = document.createElement('style');
        style.id = 'user-modal-styles';
        style.textContent = `
            .modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.3s ease, visibility 0.3s ease;
            }
            
            .modal-overlay.show {
                opacity: 1;
                visibility: visible;
            }
            
            .user-modal {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
                width: 90%;
                max-width: 600px;
                max-height: 90vh;
                overflow-y: auto;
                transform: translateY(-20px);
                transition: transform 0.3s ease;
            }
            
            .modal-overlay.show .user-modal {
                transform: translateY(0);
            }
            
            .user-modal-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px 24px;
                border-bottom: 1px solid #eee;
            }
            
            .user-modal-title {
                margin: 0;
                font-size: 1.25rem;
                font-weight: 500;
            }
            
            .user-modal-close {
                background: transparent;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                padding: 0;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background-color 0.2s;
            }
            
            .user-modal-close:hover {
                background-color: #f0f0f0;
            }
            
            .user-modal-body {
                padding: 24px;
            }
            
            .user-modal-loading {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px 0;
            }
            
            .user-modal-spinner {
                width: 40px;
                height: 40px;
                border: 3px solid rgba(0, 0, 0, 0.1);
                border-radius: 50%;
                border-top-color: #4facfe;
                animation: spin 1s linear infinite;
                margin-bottom: 16px;
            }
            
            .user-modal-content {
                display: none;
            }
            
            .user-modal-profile {
                display: flex;
                align-items: center;
                margin-bottom: 24px;
            }
            
            .user-modal-avatar {
                width: 80px;
                height: 80px;
                border-radius: 50%;
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 2rem;
                margin-right: 24px;
                flex-shrink: 0;
            }
            
            .user-modal-info {
                flex: 1;
            }
            
            .user-modal-name {
                font-size: 1.5rem;
                font-weight: 500;
                margin: 0 0 4px;
            }
            
            .user-modal-id {
                color: #666;
                font-size: 0.875rem;
                margin: 0 0 8px;
            }
            
            .user-modal-stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-top: 24px;
            }
            
            .user-modal-stat {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 16px;
                text-align: center;
            }
            
            .user-modal-stat-value {
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 4px;
                color: #4facfe;
            }
            
            .user-modal-stat-label {
                font-size: 0.875rem;
                color: #666;
            }
            
            .user-modal-footer {
                display: flex;
                justify-content: flex-end;
                padding: 16px 24px;
                border-top: 1px solid #eee;
                gap: 8px;
            }
            
            .user-modal-btn {
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.875rem;
                transition: all 0.2s;
            }
            
            .user-modal-btn-secondary {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                color: #333;
            }
            
            .user-modal-btn-secondary:hover {
                background-color: #e0e0e0;
            }
            
            .user-modal-btn-primary {
                background-color: #4facfe;
                border: 1px solid #4facfe;
                color: white;
            }
            
            .user-modal-btn-primary:hover {
                background-color: #3a9efd;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            @media (max-width: 576px) {
                .user-modal-stats {
                    grid-template-columns: 1fr;
                }
                
                .user-modal-profile {
                    flex-direction: column;
                    text-align: center;
                }
                
                .user-modal-avatar {
                    margin-right: 0;
                    margin-bottom: 16px;
                }
            }
            
            [data-theme="dark"] .user-modal {
                background-color: #1f1f1f;
                color: white;
            }
            
            [data-theme="dark"] .user-modal-header,
            [data-theme="dark"] .user-modal-footer {
                border-color: #333;
            }
            
            [data-theme="dark"] .user-modal-close:hover {
                background-color: #333;
            }
            
            [data-theme="dark"] .user-modal-stat {
                background-color: #2a2a2a;
            }
            
            [data-theme="dark"] .user-modal-btn-secondary {
                background-color: #333;
                border-color: #444;
                color: #eee;
            }
            
            [data-theme="dark"] .user-modal-btn-secondary:hover {
                background-color: #444;
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * 显示用户详情模态框
 * @param {string} userId - 用户ID
 */
function showUserDetailModal(userId) {
    // 检查是否已存在模态框，如果存在则先移除
    const existingModal = document.querySelector('.modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 创建模态框
    const modalOverlay = document.createElement('div');
    modalOverlay.className = 'modal-overlay';
    modalOverlay.setAttribute('role', 'dialog');
    modalOverlay.setAttribute('aria-modal', 'true');
    modalOverlay.setAttribute('aria-labelledby', 'user-modal-title');
    
    modalOverlay.innerHTML = `
        <div class="user-modal">
            <div class="user-modal-header">
                <h2 class="user-modal-title" id="user-modal-title">用户详情</h2>
                <button class="user-modal-close" aria-label="关闭">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            <div class="user-modal-body">
                <div class="user-modal-loading">
                    <div class="user-modal-spinner"></div>
                    <p>加载用户数据...</p>
                </div>
                <div class="user-modal-content">
                    <div class="user-modal-profile">
                        <div class="user-modal-avatar">
                            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                                <circle cx="12" cy="7" r="4"></circle>
                            </svg>
                        </div>
                        <div class="user-modal-info">
                            <h3 class="user-modal-name">加载中...</h3>
                            <div class="user-modal-id">ID: ${userId}</div>
                            <div class="user-modal-meta">注册时间: <span class="user-modal-date">-</span></div>
                        </div>
                    </div>
                    <div class="user-modal-stats">
                        <div class="user-modal-stat">
                            <div class="user-modal-stat-value">-</div>
                            <div class="user-modal-stat-label">总对话数</div>
                        </div>
                        <div class="user-modal-stat">
                            <div class="user-modal-stat-value">-</div>
                            <div class="user-modal-stat-label">总消息数</div>
                        </div>
                        <div class="user-modal-stat">
                            <div class="user-modal-stat-value">-</div>
                            <div class="user-modal-stat-label">总Token数</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="user-modal-footer">
                <button class="user-modal-btn user-modal-btn-secondary user-modal-close">关闭</button>
                <a href="/viewer/conversations?search=${userId}" class="user-modal-btn user-modal-btn-primary">查看对话记录</a>
            </div>
        </div>
    `;
    
    document.body.appendChild(modalOverlay);
    
    // 显示模态框
    setTimeout(() => {
        modalOverlay.classList.add('show');
        
        // 模拟加载数据
        setTimeout(() => {
            const loadingElement = modalOverlay.querySelector('.user-modal-loading');
            const contentElement = modalOverlay.querySelector('.user-modal-content');
            
            if (loadingElement && contentElement) {
                loadingElement.style.display = 'none';
                contentElement.style.display = 'block';
                
                // 获取用户数据
                // 使用更兼容的方式查找用户数据
                let userName = `用户 ${userId}`;
                let userDate = '-';
                let userConversations = '0';
                let userMessages = '0';
                
                // 查找包含该用户ID的行
                const rows = document.querySelectorAll('tr.table-row-interactive');
                for (const row of rows) {
                    const userIdElement = row.querySelector('.user-id');
                    if (userIdElement && userIdElement.textContent.trim() === userId) {
                        // 找到匹配的行，获取数据
                        const userNameElement = row.querySelector('.user-name');
                        if (userNameElement) {
                            userName = userNameElement.textContent;
                        }
                        
                        const dateElement = row.querySelector('.date-value');
                        if (dateElement) {
                            userDate = dateElement.textContent;
                        }
                        
                        const conversationsElement = row.querySelector('td:nth-child(4) .stat-value');
                        if (conversationsElement) {
                            userConversations = conversationsElement.textContent;
                        }
                        
                        const messagesElement = row.querySelector('td:nth-child(5) .stat-value');
                        if (messagesElement) {
                            userMessages = messagesElement.textContent;
                        }
                        
                        break;
                    }
                }
                
                // 更新用户信息
                modalOverlay.querySelector('.user-modal-name').textContent = userName;
                modalOverlay.querySelector('.user-modal-date').textContent = userDate;
                
                // 更新统计数据
                const statValues = modalOverlay.querySelectorAll('.user-modal-stat-value');
                if (statValues.length > 0) {
                    statValues[0].textContent = userConversations;
                    statValues[1].textContent = userMessages;
                    statValues[2].textContent = Math.floor(Math.random() * 10000) + 1000; // 模拟Token数
                    
                    // 添加数字动画
                    statValues.forEach(value => {
                        // 确保值是一个DOM元素而不是选择器字符串
                        if (value instanceof Element) {
                            animateNumber(value);
                        }
                    });
                }
            }
        }, 800);
    }, 10);
    
    // 关闭按钮事件
    const closeButtons = modalOverlay.querySelectorAll('.user-modal-close');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            modalOverlay.classList.remove('show');
            setTimeout(() => {
                modalOverlay.remove();
            }, 300);
        });
    });
    
    // 点击背景关闭
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            closeButtons[0].click();
        }
    });
    
    // ESC键关闭
    const escHandler = function(e) {
        if (e.key === 'Escape') {
            closeButtons[0].click();
            document.removeEventListener('keydown', escHandler);
        }
    };
    
    document.addEventListener('keydown', escHandler);
}