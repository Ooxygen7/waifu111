/**
 * Accessibility enhancements for CyberWaifu Bot 浏览系统
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化键盘导航支持
    initKeyboardNavigation();
    
    // 初始化焦点指示器
    initFocusIndicator();
    
    // 初始化ARIA属性动态更新
    initAriaUpdates();
});

/**
 * 初始化键盘导航支持
 */
function initKeyboardNavigation() {
    // 添加键盘快捷键
    document.addEventListener('keydown', function(e) {
        // Alt + 数字键快捷导航
        if (e.altKey && !e.ctrlKey && !e.shiftKey) {
            const navLinks = document.querySelectorAll('.nav-menu .nav-link');
            
            // Alt + 1-9 导航到对应的菜单项
            if (e.key >= '1' && e.key <= '9' && navLinks.length >= parseInt(e.key)) {
                e.preventDefault();
                navLinks[parseInt(e.key) - 1].click();
            }
            
            // Alt + H 返回首页
            if (e.key === 'h' || e.key === 'H') {
                e.preventDefault();
                const homeLink = document.querySelector('.nav-menu .nav-link:first-child');
                if (homeLink) homeLink.click();
            }
            
            // Alt + S 跳转到搜索框
            if (e.key === 's' || e.key === 'S') {
                e.preventDefault();
                const searchInput = document.querySelector('.search-input');
                if (searchInput) searchInput.focus();
            }
            
            // Alt + T 切换主题
            if (e.key === 't' || e.key === 'T') {
                e.preventDefault();
                const themeToggle = document.getElementById('theme-toggle');
                if (themeToggle) themeToggle.click();
            }
        }
        
        // Escape 键关闭模态框或清除搜索
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal.show');
            if (modal) {
                const closeButton = modal.querySelector('.close-modal');
                if (closeButton) closeButton.click();
            } else {
                const searchInput = document.querySelector('.search-input:focus');
                if (searchInput) {
                    searchInput.value = '';
                    searchInput.dispatchEvent(new Event('input'));
                }
            }
        }
        
        // Tab 键导航顺序优化
        if (e.key === 'Tab') {
            // 在这里可以添加特定的Tab键导航逻辑
        }
    });
    
    // 为所有可交互元素添加适当的tabindex
    ensureTabindexes();
}

/**
 * 确保所有可交互元素有适当的tabindex
 */
function ensureTabindexes() {
    // 确保主内容区域可以获得焦点
    const mainContent = document.getElementById('main-content');
    if (mainContent && !mainContent.hasAttribute('tabindex')) {
        mainContent.setAttribute('tabindex', '-1');
    }
    
    // 确保所有按钮和链接可以获得焦点
    const interactiveElements = document.querySelectorAll('button, a, input, select, textarea');
    interactiveElements.forEach(el => {
        if (el.disabled || el.hasAttribute('aria-hidden') && el.getAttribute('aria-hidden') === 'true') {
            el.setAttribute('tabindex', '-1');
        }
    });
}

/**
 * 初始化焦点指示器
 */
function initFocusIndicator() {
    // 检测用户是否使用鼠标或键盘
    let usingMouse = false;
    
    // 鼠标事件发生时标记为使用鼠标
    document.addEventListener('mousedown', function() {
        usingMouse = true;
        document.body.classList.add('user-is-using-mouse');
    });
    
    // 键盘事件发生时标记为使用键盘
    document.addEventListener('keydown', function(e) {
        // 只有当按下Tab键时才切换到键盘模式
        if (e.key === 'Tab') {
            usingMouse = false;
            document.body.classList.remove('user-is-using-mouse');
        }
    });
    
    // 为所有可聚焦元素添加focus-visible类
    const focusableElements = document.querySelectorAll('button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])');
    focusableElements.forEach(el => {
        el.addEventListener('focus', function() {
            if (!usingMouse) {
                this.classList.add('focus-visible');
            }
        });
        
        el.addEventListener('blur', function() {
            this.classList.remove('focus-visible');
        });
    });
}

/**
 * 初始化ARIA属性动态更新
 */
function initAriaUpdates() {
    // 侧边栏切换按钮ARIA属性更新
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            const isExpanded = sidebar.classList.contains('collapsed');
            this.setAttribute('aria-expanded', !isExpanded);
        });
    }
    
    // 主题切换按钮ARIA属性更新
    const themeToggle = document.getElementById('theme-toggle');
    
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const isDarkTheme = document.documentElement.getAttribute('data-theme') === 'dark';
            this.setAttribute('aria-pressed', isDarkTheme);
        });
        
        // 初始化主题按钮状态
        const currentTheme = document.documentElement.getAttribute('data-theme');
        themeToggle.setAttribute('aria-pressed', currentTheme === 'dark');
    }
    
    // 表格排序按钮ARIA属性更新
    const sortableHeaders = document.querySelectorAll('th.sortable');
    
    sortableHeaders.forEach(header => {
        header.setAttribute('role', 'button');
        header.setAttribute('tabindex', '0');
        
        header.addEventListener('click', function() {
            const isSortAsc = this.classList.contains('sort-asc');
            const isSortDesc = this.classList.contains('sort-desc');
            
            // 更新排序状态
            if (!isSortAsc && !isSortDesc) {
                this.setAttribute('aria-sort', 'ascending');
            } else if (isSortAsc) {
                this.setAttribute('aria-sort', 'descending');
            } else {
                this.setAttribute('aria-sort', 'none');
            }
            
            // 通知屏幕阅读器排序变化
            const sortStatus = document.getElementById('sort-status');
            if (!sortStatus) {
                const status = document.createElement('div');
                status.id = 'sort-status';
                status.className = 'sr-only';
                status.setAttribute('aria-live', 'polite');
                document.body.appendChild(status);
            }
            
            const columnName = this.textContent.trim();
            const sortDirection = this.getAttribute('aria-sort');
            document.getElementById('sort-status').textContent = `表格已按${columnName}${sortDirection === 'ascending' ? '升序' : '降序'}排序`;
        });
        
        // 支持键盘操作
        header.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });
}

/**
 * 添加键盘快捷键帮助
 */
function showKeyboardShortcuts() {
    // 创建快捷键帮助模态框
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'keyboard-shortcuts-modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-labelledby', 'keyboard-shortcuts-title');
    modal.setAttribute('aria-modal', 'true');
    
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="keyboard-shortcuts-title">键盘快捷键</h2>
                <button class="close-modal" aria-label="关闭">×</button>
            </div>
            <div class="modal-body">
                <table class="table">
                    <thead>
                        <tr>
                            <th>快捷键</th>
                            <th>功能</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Alt + 1-9</td>
                            <td>导航到对应的菜单项</td>
                        </tr>
                        <tr>
                            <td>Alt + H</td>
                            <td>返回首页</td>
                        </tr>
                        <tr>
                            <td>Alt + S</td>
                            <td>跳转到搜索框</td>
                        </tr>
                        <tr>
                            <td>Alt + T</td>
                            <td>切换主题</td>
                        </tr>
                        <tr>
                            <td>Escape</td>
                            <td>关闭模态框或清除搜索</td>
                        </tr>
                        <tr>
                            <td>Tab</td>
                            <td>在页面元素间导航</td>
                        </tr>
                        <tr>
                            <td>Shift + Tab</td>
                            <td>反向在页面元素间导航</td>
                        </tr>
                        <tr>
                            <td>Enter / Space</td>
                            <td>激活当前聚焦的按钮或链接</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 显示模态框
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
    
    // 关闭按钮事件
    const closeButton = modal.querySelector('.close-modal');
    closeButton.addEventListener('click', function() {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.remove();
        }, 300);
    });
    
    // 点击模态框外部关闭
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeButton.click();
        }
    });
    
    // Escape键关闭
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && document.getElementById('keyboard-shortcuts-modal')) {
            closeButton.click();
        }
    });
    
    // 聚焦到关闭按钮
    closeButton.focus();
}