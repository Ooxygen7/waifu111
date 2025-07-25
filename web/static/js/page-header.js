/**
 * Page Header
 * 页面头部功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面头部
    initPageHeader();
});

/**
 * 初始化页面头部
 */
function initPageHeader() {
    // 更新当前时间
    updateCurrentTime();
    
    // 初始化主题切换
    initThemeToggle();
}

/**
 * 更新当前时间
 */
function updateCurrentTime() {
    const currentTimeElement = document.querySelector('.current-time');
    if (!currentTimeElement) return;
    
    // 每秒更新一次时间
    setInterval(() => {
        const now = moment();
        currentTimeElement.textContent = now.format('YYYY-MM-DD HH:mm:ss');
    }, 1000);
}

/**
 * 初始化主题切换
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle ? themeToggle.querySelector('.theme-icon') : null;
    if (!themeToggle || !themeIcon) return;
    
    // 检查当前主题
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    updateThemeIcon(themeIcon, currentTheme);
    
    // 设置按钮状态
    themeToggle.setAttribute('aria-pressed', currentTheme === 'dark' ? 'true' : 'false');
    
    // 添加点击事件
    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = (!currentTheme || currentTheme === 'dark') ? 'tech' : 'dark';
        
        // 更新主题
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // 更新图标
        updateThemeIcon(themeIcon, newTheme);
        
        // 更新按钮状态
        themeToggle.setAttribute('aria-pressed', newTheme === 'tech' ? 'true' : 'false');
    });
}

/**
 * 更新主题图标
 * @param {HTMLElement} iconElement - 图标元素
 * @param {string} theme - 当前主题
 */
function updateThemeIcon(iconElement, theme) {
    if (theme === 'tech') {
        iconElement.textContent = '🔮';
    } else {
        iconElement.textContent = '🌙';
    }
}