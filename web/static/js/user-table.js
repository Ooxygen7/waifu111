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
 * 显示数字（移除动画效果）
 * @param {HTMLElement} element - 包含数字的元素
 */
function animateNumber(element) {
    const finalValue = parseInt(element.textContent.replace(/,/g, ''), 10);
    if (isNaN(finalValue)) return;
    
    // 直接显示最终值，不使用动画
    element.textContent = finalValue;
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
                background: linear-gradient(135deg, rgba(0, 0, 0, 0.8) 0%, rgba(0, 20, 40, 0.9) 100%);
                backdrop-filter: blur(10px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                opacity: 0;
                visibility: hidden;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .modal-overlay.show {
                opacity: 1;
                visibility: visible;
            }
            
            .user-modal {
                background: linear-gradient(145deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 20px;
                box-shadow: 
                    0 25px 50px rgba(0, 0, 0, 0.5),
                    0 0 0 1px rgba(255, 255, 255, 0.1),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2);
                width: 90%;
                max-width: 700px;
                max-height: 90vh;
                overflow: hidden;
                transform: translateY(-30px) scale(0.95);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
            }
            
            .user-modal::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: linear-gradient(90deg, #00ffff, #0080ff, #8000ff, #ff0080, #ff8000, #ffff00);
                background-size: 300% 100%;
                animation: techGlow 3s linear infinite;
            }
            
            @keyframes techGlow {
                0% { background-position: 0% 50%; }
                100% { background-position: 300% 50%; }
            }
            
            .modal-overlay.show .user-modal {
                transform: translateY(0) scale(1);
            }
            
            .user-modal-header {
                padding: 24px 28px;
                border-bottom: 1px solid rgba(0, 255, 255, 0.2);
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: linear-gradient(135deg, rgba(0, 255, 255, 0.1) 0%, rgba(0, 128, 255, 0.1) 100%);
                position: relative;
                overflow: hidden;
            }
            
            .user-modal-header::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
                animation: headerScan 2s ease-in-out infinite;
            }
            
            @keyframes headerScan {
                0% { left: -100%; }
                100% { left: 100%; }
            }
            
            .user-modal-title {
                margin: 0;
                font-size: 20px;
                font-weight: 700;
                color: #00ffff;
                text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
                letter-spacing: 1px;
                position: relative;
                z-index: 1;
            }
            
            .user-modal-close {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #00ffff;
                cursor: pointer;
                padding: 10px;
                border-radius: 12px;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                backdrop-filter: blur(10px);
                position: relative;
                z-index: 1;
                min-width: 44px;
                height: 44px;
                flex-shrink: 0;
            }
            
            .user-modal-close:hover {
                background: rgba(0, 255, 255, 0.2);
                border-color: #00ffff;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.4);
                transform: scale(1.1);
            }
            
            .user-modal-body {
                padding: 28px;
                overflow-y: auto;
                max-height: calc(90vh - 160px);
                scrollbar-width: thin;
                scrollbar-color: #00ffff rgba(255, 255, 255, 0.1);
            }
            
            .user-modal-body::-webkit-scrollbar {
                width: 8px;
            }
            
            .user-modal-body::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            
            .user-modal-body::-webkit-scrollbar-thumb {
                background: linear-gradient(180deg, #00ffff, #0080ff);
                border-radius: 4px;
            }
            
            .user-modal-loading {
                text-align: center;
                padding: 60px 20px;
                color: #00ffff;
            }
            
            .user-modal-spinner {
                width: 50px;
                height: 50px;
                border: 3px solid rgba(0, 255, 255, 0.3);
                border-top: 3px solid #00ffff;
                border-radius: 50%;
                animation: techSpin 1s linear infinite;
                margin: 0 auto 20px;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
            }
            
            @keyframes techSpin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .user-modal-content {
                display: none;
            }
            
            .user-modal-profile {
                display: flex;
                align-items: flex-start;
                margin-bottom: 28px;
                padding: 24px;
                background: linear-gradient(135deg, rgba(0, 255, 255, 0.05) 0%, rgba(0, 128, 255, 0.05) 100%);
                border: 1px solid rgba(0, 255, 255, 0.2);
                border-radius: 16px;
                position: relative;
                overflow: hidden;
            }
            
            .user-modal-profile::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(45deg, transparent 30%, rgba(0, 255, 255, 0.1) 50%, transparent 70%);
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .user-modal-profile:hover::before {
                opacity: 1;
            }
            
            .user-modal-avatar {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #00ffff 0%, #0080ff 50%, #8000ff 100%);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 24px;
                color: white;
                flex-shrink: 0;
                box-shadow: 
                    0 0 30px rgba(0, 255, 255, 0.4),
                    inset 0 0 20px rgba(255, 255, 255, 0.2);
                position: relative;
                z-index: 1;
            }
            
            .user-modal-avatar::before {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                background: linear-gradient(45deg, #00ffff, #0080ff, #8000ff, #ff0080);
                border-radius: 50%;
                z-index: -1;
                animation: avatarGlow 2s linear infinite;
            }
            
            @keyframes avatarGlow {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .user-modal-info {
                flex: 1;
                position: relative;
                z-index: 1;
            }
            
            .user-modal-name {
                margin: 0 0 12px 0;
                font-size: 24px;
                font-weight: 700;
                color: #00ffff;
                text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
            }
            
            .user-modal-id {
                color: rgba(255, 255, 255, 0.7);
                font-size: 14px;
                margin-bottom: 16px;
                font-family: 'Courier New', monospace;
                background: rgba(0, 255, 255, 0.1);
                padding: 4px 8px;
                border-radius: 6px;
                display: inline-block;
            }
            
            .user-modal-meta {
                margin-bottom: 8px;
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
                display: flex;
                align-items: center;
            }
            
            .user-modal-meta span {
                color: #00ffff;
                font-weight: 500;
                margin-left: 8px;
            }
            
            .user-modal-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 16px;
                margin-bottom: 28px;
            }
            
            .user-modal-stat {
                text-align: center;
                padding: 20px 16px;
                background: linear-gradient(135deg, rgba(0, 255, 255, 0.1) 0%, rgba(0, 128, 255, 0.1) 100%);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 12px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .user-modal-stat::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.2), transparent);
                transition: left 0.5s ease;
            }
            
            .user-modal-stat:hover {
                transform: translateY(-4px);
                box-shadow: 0 10px 30px rgba(0, 255, 255, 0.2);
                border-color: #00ffff;
            }
            
            .user-modal-stat:hover::before {
                left: 100%;
            }
            
            .user-modal-stat-value {
                font-size: 24px;
                font-weight: 700;
                color: #00ffff;
                margin-bottom: 8px;
                text-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
                position: relative;
                z-index: 1;
            }
            
            .user-modal-stat-label {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.7);
                text-transform: uppercase;
                letter-spacing: 1px;
                position: relative;
                z-index: 1;
            }
            
            .user-modal-footer {
                padding: 24px 28px;
                border-top: 1px solid rgba(0, 255, 255, 0.2);
                display: flex;
                justify-content: flex-end;
                gap: 16px;
                background: linear-gradient(135deg, rgba(0, 255, 255, 0.05) 0%, rgba(0, 128, 255, 0.05) 100%);
            }
            
            .user-modal-btn {
                padding: 12px 24px;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
                text-transform: uppercase;
                letter-spacing: 1px;
                white-space: nowrap;
            }
            
            .user-modal-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                transition: left 0.5s ease;
            }
            
            .user-modal-btn:hover::before {
                left: 100%;
            }
            
            .user-modal-btn-secondary {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
                color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .user-modal-btn-secondary:hover {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, rgba(255, 255, 255, 0.1) 100%);
                border-color: rgba(255, 255, 255, 0.4);
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
            }
            
            .user-modal-btn-primary {
                background: linear-gradient(135deg, #00ffff 0%, #0080ff 100%);
                border: 1px solid #00ffff;
                color: #000;
                font-weight: 700;
            }
            
            .user-modal-btn-primary:hover {
                background: linear-gradient(135deg, #0080ff 0%, #8000ff 100%);
                border-color: #0080ff;
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(0, 255, 255, 0.3);
                color: #fff;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            @media (max-width: 576px) {
                .user-modal {
                    width: 95%;
                    margin: 20px;
                }
                
                .user-modal-stats {
                    grid-template-columns: repeat(2, 1fr);
                }
                
                .user-modal-profile {
                    flex-direction: column;
                    text-align: center;
                }
                
                .user-modal-avatar {
                    margin-right: 0;
                    margin-bottom: 20px;
                }
                
                .user-modal-footer {
                    flex-direction: column;
                }
            }
            
            [data-theme="dark"] .user-modal {
                background: linear-gradient(145deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
            }
            
            [data-theme="dark"] .user-modal-header,
            [data-theme="dark"] .user-modal-footer {
                border-color: rgba(0, 255, 255, 0.3);
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
                            <div class="user-modal-meta">用户名: <span class="user-modal-username">-</span></div>
                            <div class="user-modal-meta">姓名: <span class="user-modal-fullname">-</span></div>
                            <div class="user-modal-meta">注册时间: <span class="user-modal-date">-</span></div>
                            <div class="user-modal-meta">最后更新: <span class="user-modal-update">-</span></div>
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
                            <div class="user-modal-stat-label">输入Token</div>
                        </div>
                        <div class="user-modal-stat">
                            <div class="user-modal-stat-value">-</div>
                            <div class="user-modal-stat-label">输出Token</div>
                        </div>
                        <div class="user-modal-stat">
                            <div class="user-modal-stat-value">-</div>
                            <div class="user-modal-stat-label">总Token数</div>
                        </div>
                        <div class="user-modal-stat">
                            <div class="user-modal-stat-value">-</div>
                            <div class="user-modal-stat-label">账户等级</div>
                        </div>
                        <div class="user-modal-stat">
                            <div class="user-modal-stat-value">-</div>
                            <div class="user-modal-stat-label">剩余次数</div>
                        </div>
                        <div class="user-modal-stat">
                            <div class="user-modal-stat-value">-</div>
                            <div class="user-modal-stat-label">余额</div>
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
        
        // 根据当前页面路径判断使用哪个API端点
        const isViewerMode = window.location.pathname.startsWith('/viewer');
        const apiEndpoint = isViewerMode ? `/viewer/api/user/${userId}` : `/api/user/${userId}`;
        
        // 调用API获取用户详情
        fetch(apiEndpoint)
            .then(response => {
                if (!response.ok) {
                    throw new Error('获取用户信息失败');
                }
                return response.json();
            })
            .then(data => {
                const loadingElement = modalOverlay.querySelector('.user-modal-loading');
                const contentElement = modalOverlay.querySelector('.user-modal-content');
                
                if (loadingElement && contentElement) {
                    loadingElement.style.display = 'none';
                    contentElement.style.display = 'block';
                    
                    const user = data.user;
                    const config = data.config || {};
                    
                    // 计算总token数
                    const totalTokens = (user.input_tokens || 0) + (user.output_tokens || 0);
                    
                    // 格式化日期
                    const formatDate = (dateStr) => {
                        if (!dateStr) return '未知';
                        return new Date(dateStr).toLocaleString('zh-CN');
                    };
                    
                    // 获取用户显示名称
                    const userName = user.first_name || user.last_name ? 
                        `${user.first_name || ''} ${user.last_name || ''}`.trim() : 
                        (user.user_name || '未知用户');
                    
                    const fullName = user.first_name || user.last_name ? 
                        `${user.first_name || ''} ${user.last_name || ''}`.trim() : 
                        '未设置';
                    
                    // 更新用户基本信息
                    modalOverlay.querySelector('.user-modal-name').textContent = userName;
                    modalOverlay.querySelector('.user-modal-username').textContent = user.user_name || '未设置';
                    modalOverlay.querySelector('.user-modal-fullname').textContent = fullName;
                    modalOverlay.querySelector('.user-modal-date').textContent = formatDate(user.create_at);
                    modalOverlay.querySelector('.user-modal-update').textContent = formatDate(user.update_at);
                    
                    // 更新统计数据
                    const statValues = modalOverlay.querySelectorAll('.user-modal-stat-value');
                    if (statValues.length >= 8) {
                        statValues[0].textContent = user.conversations || 0;
                        statValues[1].textContent = user.dialog_turns || 0;
                        statValues[2].textContent = user.input_tokens || 0;
                        statValues[3].textContent = user.output_tokens || 0;
                        statValues[4].textContent = totalTokens;
                        statValues[5].textContent = user.account_tier || '未设置';
                        statValues[6].textContent = user.remain_frequency || 0;
                        statValues[7].textContent = user.balance || 0;
                        
                        // 添加数字动画（仅对数字类型的统计值）
                        for (let i = 0; i < 5; i++) {
                            if (statValues[i] instanceof Element) {
                                animateNumber(statValues[i]);
                            }
                        }
                        for (let i = 6; i < 8; i++) {
                            if (statValues[i] instanceof Element) {
                                animateNumber(statValues[i]);
                            }
                        }
                    }
                }
            })
            .catch(error => {
                console.error('获取用户信息失败:', error);
                const loadingElement = modalOverlay.querySelector('.user-modal-loading');
                if (loadingElement) {
                    loadingElement.innerHTML = '<p class="error">获取用户信息失败，请稍后重试</p>';
                }
            });
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