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
    // 强制设置 'dark' 主题
    document.documentElement.setAttribute('data-theme', 'dark');
    localStorage.setItem('theme', 'dark');

    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        // 隐藏切换按钮
        themeToggle.style.display = 'none';
    }
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