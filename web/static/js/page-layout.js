/**
 * Page Layout
 * 页面布局功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面布局
    initPageLayout();
});

/**
 * 初始化页面布局
 */
function initPageLayout() {
    // 更新页面标题
    updatePageTitle();
    
    // 初始化响应式布局
    initResponsiveLayout();
}

/**
 * 更新页面标题
 */
function updatePageTitle() {
    const pageTitle = document.querySelector('.page-title');
    if (!pageTitle) return;
    
    // 添加标题动画效果
    pageTitle.style.opacity = '0';
    pageTitle.style.transform = 'translateY(-10px)';
    pageTitle.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    
    setTimeout(() => {
        pageTitle.style.opacity = '1';
        pageTitle.style.transform = 'translateY(0)';
    }, 100);
}

/**
 * 初始化响应式布局
 */
function initResponsiveLayout() {
    // 监听窗口大小变化
    window.addEventListener('resize', handleResize);
    
    // 初始调用一次
    handleResize();
}

/**
 * 处理窗口大小变化
 */
function handleResize() {
    const width = window.innerWidth;
    const mainContent = document.querySelector('.main-content');
    if (!mainContent) return;
    
    // 根据窗口大小调整内容区域的内边距
    if (width < 576) {
        mainContent.style.padding = 'var(--spacing-sm)';
    } else if (width < 768) {
        mainContent.style.padding = 'var(--spacing-md)';
    } else if (width < 992) {
        mainContent.style.padding = 'var(--spacing-lg)';
    } else {
        mainContent.style.padding = 'var(--spacing-xl)';
    }
}

/**
 * 设置页面标题
 * @param {string} title - 页面标题
 */
function setPageTitle(title) {
    const pageTitle = document.querySelector('.page-title');
    if (!pageTitle) return;
    
    // 添加淡出效果
    pageTitle.style.opacity = '0';
    pageTitle.style.transform = 'translateY(-10px)';
    
    setTimeout(() => {
        pageTitle.textContent = title;
        
        // 添加淡入效果
        pageTitle.style.opacity = '1';
        pageTitle.style.transform = 'translateY(0)';
    }, 300);
}