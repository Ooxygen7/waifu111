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
    // 设置中文
    moment.locale('zh-cn');
    
    // 更新时间显示
    function updateTime() {
        const timeElements = document.querySelectorAll('.current-time');
        timeElements.forEach(el => {
            el.textContent = moment().format('YYYY-MM-DD HH:mm:ss');
        });
    }
    
    // 每秒更新时间
    setInterval(updateTime, 1000);
    updateTime();
}

/**
 * 初始化侧边栏切换
 */
function initSidebarToggle() {
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }
    
    // 在小屏幕上点击导航链接后自动收起侧边栏
    const navLinks = document.querySelectorAll('.nav-link');
    if (navLinks.length > 0 && window.innerWidth <= 768) {
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (sidebar) {
                    sidebar.classList.add('collapsed');
                }
            });
        });
    }
}

/**
 * 初始化主题切换
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.querySelector('.theme-icon');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // 检查本地存储中的主题设置
    const currentTheme = localStorage.getItem('theme');
    
    // 如果有存储的主题设置，应用它
    if (currentTheme) {
        document.documentElement.setAttribute('data-theme', currentTheme);
        updateThemeIcon(currentTheme);
    } else if (prefersDarkScheme.matches) {
        // 如果用户系统偏好深色模式，应用深色主题
        document.documentElement.setAttribute('data-theme', 'dark');
        updateThemeIcon('dark');
    }
    
    // 主题切换按钮点击事件
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            let theme = 'light';
            
            // 如果当前是浅色主题或没有设置主题
            if (!document.documentElement.getAttribute('data-theme') || 
                document.documentElement.getAttribute('data-theme') === 'light') {
                theme = 'dark';
            }
            
            // 设置主题
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            updateThemeIcon(theme);
        });
    }
    
    // 更新主题图标
    function updateThemeIcon(theme) {
        if (themeIcon) {
            themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    }
    
    // 监听系统主题变化
    prefersDarkScheme.addEventListener('change', function(e) {
        // 只有在用户没有手动设置主题时才跟随系统
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', newTheme);
            updateThemeIcon(newTheme);
        }
    });
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
 * 添加数字动画效果
 * @param {string|HTMLElement|NodeList} selector - 目标元素选择器或DOM元素
 * @param {number} duration - 动画持续时间（毫秒）
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
        // 添加动画类
        element.classList.add('animate-number');
        
        // 获取最终值
        const finalValueText = element.textContent.trim();
        const finalValue = parseInt(finalValueText.replace(/,/g, ''), 10);
        
        // 如果不是有效数字，跳过
        if (isNaN(finalValue)) return;
        
        let startValue = 0;
        const startTime = performance.now();
        
        // 使用 easeOutExpo 缓动函数使动画更自然
        function easeOutExpo(t) {
            return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
        }
        
        function updateNumber(currentTime) {
            const elapsedTime = currentTime - startTime;
            
            if (elapsedTime < duration) {
                const progress = easeOutExpo(elapsedTime / duration);
                const currentValue = Math.round(progress * finalValue);
                
                // 格式化数字（添加千位分隔符）
                if (formatNumber && currentValue >= 1000) {
                    element.textContent = currentValue.toLocaleString('zh-CN');
                } else {
                    element.textContent = currentValue;
                }
                
                requestAnimationFrame(updateNumber);
            } else {
                // 确保最终值正确显示
                if (formatNumber && finalValue >= 1000) {
                    element.textContent = finalValue.toLocaleString('zh-CN');
                } else {
                    element.textContent = finalValue;
                }
            }
        }
        
        requestAnimationFrame(updateNumber);
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