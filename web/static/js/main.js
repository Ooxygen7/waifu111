/**
 * Main JavaScript file for CyberWaifu Bot 浏览系统
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化时间显示
    initTimeDisplay();
    
    // 初始化侧边栏切换
    initSidebarToggle();
    
    // 初始化主题切换
    initThemeToggle();
    
    // 初始化统计卡片
    initStatCards();
});

/**
 * 初始化时间显示
 */
function initTimeDisplay() {
    const clockElement = document.getElementById('digital-clock');
    if (!clockElement) return;

    function updateClock() {
        const now = moment();
        const timeString = now.format('HH:mm:ss');
        const dateString = now.format('YYYY-MM-DD');
        
        clockElement.innerHTML = `
            <span class="time">${timeString}</span>
            <span class="date">${dateString}</span>
        `;
    }

    // Initial call
    updateClock();

    // Update every second
    setInterval(updateClock, 1000);
}

/**
 * 初始化侧边栏切换
 */
function initSidebarToggle() {
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const body = document.body;

    function handleResize() {
        if (window.innerWidth <= 992) {
            sidebar.classList.add('collapsed');
            body.classList.add('sidebar-collapsed');
        } else {
            sidebar.classList.remove('collapsed');
            body.classList.remove('sidebar-collapsed');
        }
    }

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            body.classList.toggle('sidebar-collapsed');
        });
    }

    // Initial check on page load
    handleResize();

    // Check on window resize
    window.addEventListener('resize', handleResize);
}

/**
 * 初始化主题切换
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const doc = document.documentElement;

    if (!themeToggle) return;

    const themeIcon = themeToggle.querySelector('.theme-icon');

    const applyTheme = (theme) => {
        doc.setAttribute('data-theme', theme);
        if (themeIcon) {
            themeIcon.setAttribute('data-feather', theme === 'dark' ? 'sun' : 'moon');
        }
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    };

    themeToggle.addEventListener('click', () => {
        let currentTheme = doc.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    });

    // Apply saved theme on initial load
    const savedTheme = localStorage.getItem('theme') || 'dark'; // Default to dark
    applyTheme(savedTheme);
}

/**
 * 添加骨架屏加载效果
 * @param {string} selector - 目标元素选择器
 */
function addSkeletonLoading(selector) {
    const elements = document.querySelectorAll(selector);
    
    elements.forEach(element => {
        element.classList.add('skeleton-loading');
        
        // 模拟数据加载
        setTimeout(() => {
            element.classList.remove('skeleton-loading');
        }, 1500);
    });
}

/**
 * 显示数字（移除动画效果）
 * @param {string|HTMLElement|NodeList} selector - 目标元素选择器或DOM元素
 * @param {number} duration - 保留参数以兼容现有调用（已忽略）
 * @param {boolean} formatNumber - 是否格式化数字（添加千位分隔符）
 */
function animateNumbers(selector, duration = 1500, formatNumber = true) {
    let elements;
    
    // 处理不同类型的输入
    if (typeof selector === 'string') {
        // 如果是选择器字符串，使用querySelectorAll
        elements = document.querySelectorAll(selector);
    } else if (selector instanceof Element) {
        // 如果是单个DOM元素，创建一个包含它的数组
        elements = [selector];
    } else if (selector instanceof NodeList || Array.isArray(selector)) {
        // 如果是NodeList或数组，直接使用
        elements = selector;
    } else {
        // 无效的选择器
        console.error('无效的选择器类型:', selector);
        return;
    }
    
    Array.from(elements).forEach(element => {
        // 获取最终值
        const finalValueText = element.textContent.trim();
        const finalValue = parseInt(finalValueText.replace(/,/g, ''), 10);
        
        // 如果不是有效数字，跳过
        if (isNaN(finalValue)) return;
        
        // 直接显示最终值，不使用动画
        if (formatNumber && finalValue >= 1000) {
            element.textContent = finalValue.toLocaleString('zh-CN');
        } else {
            element.textContent = finalValue;
        }
    });
}

/**
 * 添加表格排序功能
 * @param {string} tableSelector - 表格选择器
 */
function initTableSort(tableSelector) {
    const table = document.querySelector(tableSelector);
    
    if (!table) return;
    
    const headers = table.querySelectorAll('th');
    
    headers.forEach(header => {
        if (header.classList.contains('sortable')) {
            header.addEventListener('click', function() {
                const index = Array.from(header.parentNode.children).indexOf(header);
                const isAsc = header.classList.contains('sort-asc');
                
                // 清除所有排序状态
                headers.forEach(h => {
                    h.classList.remove('sort-asc', 'sort-desc');
                });
                
                // 设置新的排序状态
                header.classList.add(isAsc ? 'sort-desc' : 'sort-asc');
                
                // 排序表格
                sortTable(table, index, !isAsc);
            });
        }
    });
    
    function sortTable(table, columnIndex, asc) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // 排序行
        const sortedRows = rows.sort((a, b) => {
            const cellA = a.querySelectorAll('td')[columnIndex].textContent.trim();
            const cellB = b.querySelectorAll('td')[columnIndex].textContent.trim();
            
            // 尝试数字排序
            const numA = parseFloat(cellA);
            const numB = parseFloat(cellB);
            
            if (!isNaN(numA) && !isNaN(numB)) {
                return asc ? numA - numB : numB - numA;
            }
            
            // 字符串排序
            return asc 
                ? cellA.localeCompare(cellB, 'zh-CN') 
                : cellB.localeCompare(cellA, 'zh-CN');
        });
        
        // 清空表格并添加排序后的行
        while (tbody.firstChild) {
            tbody.removeChild(tbody.firstChild);
        }
        
        sortedRows.forEach(row => {
            tbody.appendChild(row);
        });
    }
}

/**
 * 初始化搜索功能
 * @param {string} inputSelector - 搜索输入框选择器
 * @param {string} targetSelector - 搜索目标元素选择器
 */
function initSearch(inputSelector, targetSelector) {
    const searchInput = document.querySelector(inputSelector);
    const targets = document.querySelectorAll(targetSelector);
    
    if (!searchInput || targets.length === 0) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        
        targets.forEach(target => {
            const text = target.textContent.toLowerCase();
            const match = text.includes(searchTerm);
            
            target.style.display = match ? '' : 'none';
        });
    });
    
    // 添加清除按钮功能
    const clearButton = document.querySelector(`${inputSelector} + .search-clear`);
    if (clearButton) {
        clearButton.addEventListener('click', function() {
            searchInput.value = '';
            searchInput.dispatchEvent(new Event('input'));
        });
    }
}

/**
 * 初始化统计卡片
 * 添加动画效果和交互功能
 */
function initStatCards() {
    const statCards = document.querySelectorAll('.stat-card');
    
    if (!statCards.length) return;
    
    // 添加入场动画
    statCards.forEach((card, index) => {
        // 延迟入场，形成级联效果
        setTimeout(() => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            // 强制重绘
            void card.offsetWidth;
            
            // 添加过渡
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
            
            // 添加数字动画
            const statValue = card.querySelector('.stat-value');
            if (statValue) {
                setTimeout(() => {
                    animateNumbers(statValue, 1800, true);
                }, 300);
            }
        }, index * 150); // 每张卡片错开150ms
    });
    
    // 添加悬停效果增强
    statCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            // 背景图标动画
            const bgIcon = this.querySelector('.stat-bg-icon');
            if (bgIcon) {
                bgIcon.style.transition = 'transform 0.5s ease';
                bgIcon.style.transform = 'scale(1.2) rotate(15deg)';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            // 恢复背景图标
            const bgIcon = this.querySelector('.stat-bg-icon');
            if (bgIcon) {
                bgIcon.style.transition = 'transform 0.5s ease';
                bgIcon.style.transform = 'rotate(10deg)';
            }
        });
    });
    
    // 初始化表格排序
    initTableSort('.table');
    
    // 添加刷新数据功能
    const refreshButton = document.querySelector('.refresh-data');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            // 显示加载状态
            this.classList.add('loading');
            this.disabled = true;
            
            // 添加旋转动画
            const icon = this.querySelector('.btn-icon');
            if (icon) {
                icon.style.display = 'inline-block';
                icon.style.animation = 'spin 1s linear infinite';
            }
            
            // 模拟数据刷新
            setTimeout(() => {
                // 重新添加骨架屏效果
                addSkeletonLoading('.stat-card');
                
                // 恢复按钮状态
                setTimeout(() => {
                    this.classList.remove('loading');
                    this.disabled = false;
                    
                    if (icon) {
                        icon.style.animation = '';
                    }
                    
                    // 重新触发数字动画
                    setTimeout(() => {
                        animateNumbers('.stat-value', 1500, true);
                    }, 500);
                }, 1500);
            }, 500);
        });
    }
    
    // 添加卡片点击效果
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // 如果点击的是按钮，不触发卡片点击效果
            if (e.target.tagName === 'BUTTON' || e.target.tagName === 'A' || 
                e.target.closest('button') || e.target.closest('a')) {
                return;
            }
            
            // 触发卡片内的主要按钮点击
            const mainButton = this.querySelector('.btn-primary');
            if (mainButton) {
                mainButton.click();
            }
        });
    });
}

/**
 * 添加旋转动画的关键帧
 */
if (!document.getElementById('animation-keyframes')) {
    const style = document.createElement('style');
    style.id = 'animation-keyframes';
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}


// ==========================================================================
// 合并自 accessibility.js
// ==========================================================================

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

// ==========================================================================
// 合并自 table-interactions.js
// ==========================================================================

/**
 * 初始化表格交互功能
 */
function initTableInteractions() {
    // 表格行悬停效果增强
    enhanceTableRowHover();
    
    // 初始化表格排序
    initTableSortable();
    
    // 注意：表格行点击功能已移至专门的页面JS文件中处理
}

/**
 * 增强表格行悬停效果
 */
function enhanceTableRowHover() {
    const interactiveRows = document.querySelectorAll('.table-row-interactive');
    
    interactiveRows.forEach(row => {
        // 添加鼠标进入效果
        row.addEventListener('mouseenter', function() {
            // 添加高亮效果
            this.style.zIndex = '1';
            
            // 高亮用户头像
            const avatar = this.querySelector('.user-avatar');
            if (avatar) {
                avatar.style.transform = 'scale(1.1)';
            }
            
            // 高亮消息数量标签
            const messageCount = this.querySelector('.message-count');
            if (messageCount) {
                messageCount.style.transform = 'scale(1.1)';
            }
        });
        
        // 添加鼠标离开效果
        row.addEventListener('mouseleave', function() {
            // 恢复默认状态
            this.style.zIndex = '';
            
            // 恢复用户头像
            const avatar = this.querySelector('.user-avatar');
            if (avatar) {
                avatar.style.transform = '';
            }
            
            // 恢复消息数量标签
            const messageCount = this.querySelector('.message-count');
            if (messageCount) {
                messageCount.style.transform = '';
            }
        });
    });
}

/**
 * 初始化表格排序功能
 */
function initTableSortable() {
    const sortableHeaders = document.querySelectorAll('th.sortable');
    
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const table = this.closest('table');
            if (!table) return; // 如果找不到table，则不执行
            const tbody = table.querySelector('tbody');
            if (!tbody) return; // 如果找不到tbody，则不执行

            const rows = Array.from(tbody.querySelectorAll('tr'));
            const index = Array.from(this.parentNode.children).indexOf(this);
            const sortType = this.dataset.sort || 'text';
            
            // 切换排序方向
            const isAsc = !this.classList.contains('sort-asc');
            
            // 更新排序状态
            sortableHeaders.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            this.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
            
            // 排序行
            rows.sort((a, b) => {
                const cellA = a.querySelectorAll('td')[index];
                const cellB = b.querySelectorAll('td')[index];
                
                if (!cellA || !cellB) return 0;
                
                let valueA, valueB;
                
                // 根据排序类型获取值
                if (sortType === 'number') {
                    // 提取数字
                    valueA = parseInt(cellA.textContent.replace(/[^\d]/g, ''), 10) || 0;
                    valueB = parseInt(cellB.textContent.replace(/[^\d]/g, ''), 10) || 0;
                } else if (sortType === 'user') {
                    // 用户名排序
                    const userNameA = cellA.querySelector('.user-name');
                    const userNameB = cellB.querySelector('.user-name');
                    valueA = userNameA ? userNameA.textContent.trim() : '';
                    valueB = userNameB ? userNameB.textContent.trim() : '';
                } else {
                    // 默认文本排序
                    valueA = cellA.textContent.trim();
                    valueB = cellB.textContent.trim();
                }
                
                // 排序比较
                if (sortType === 'number') {
                    return isAsc ? valueA - valueB : valueB - valueA;
                } else {
                    return isAsc
                        ? valueA.localeCompare(valueB, 'zh-CN')
                        : valueB.localeCompare(valueA, 'zh-CN');
                }
            });
            
            // 应用排序动画
            rows.forEach((row, i) => {
                // 设置行的新位置
                row.style.transition = 'none';
                row.style.opacity = '0';
                row.style.transform = 'translateY(20px)';
                
                // 重新添加到表格
                tbody.appendChild(row);
                
                // 触发重绘
                void row.offsetHeight;
                
                // 添加动画
                setTimeout(() => {
                    row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    row.style.opacity = '1';
                    row.style.transform = 'translateY(0)';
                }, 50 * i); // 错开动画时间
            });
        });
    });
}

// 在 DOMContentLoaded 事件中调用新的初始化函数
document.addEventListener('DOMContentLoaded', function() {
    // 检查页面是否不需要这些交互
    if (window.page_has_custom_scripts) {
        return;
    }
    initKeyboardNavigation();
    initFocusIndicator();
    initAriaUpdates();
    initTableInteractions();
});