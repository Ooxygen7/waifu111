/**
 * Breadcrumb Navigation
 * 面包屑导航功能
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化面包屑导航
    initBreadcrumb();
});

/**
 * 初始化面包屑导航
 */
function initBreadcrumb() {
    // 获取当前页面路径
    const currentPath = window.location.pathname;
    
    // 获取面包屑容器
    const breadcrumb = document.querySelector('.breadcrumb');
    if (!breadcrumb) return;
    
    // 为面包屑项添加动态效果
    const breadcrumbItems = breadcrumb.querySelectorAll('.breadcrumb-item');
    breadcrumbItems.forEach((item, index) => {
        // 添加延迟动画效果
        item.style.opacity = '0';
        item.style.transform = 'translateX(-10px)';
        item.style.transition = `opacity 0.3s ease ${index * 0.1}s, transform 0.3s ease ${index * 0.1}s`;
        
        setTimeout(() => {
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, 100);
    });
    
    // 为活动项添加ARIA属性
    const activeItem = breadcrumb.querySelector('.breadcrumb-item.active');
    if (activeItem) {
        activeItem.setAttribute('aria-current', 'page');
    }
}

/**
 * 动态添加面包屑项
 * @param {string} label - 面包屑项文本
 * @param {string} url - 面包屑项链接
 * @param {boolean} isActive - 是否为当前活动项
 */
function addBreadcrumbItem(label, url, isActive = false) {
    const breadcrumb = document.querySelector('.breadcrumb');
    if (!breadcrumb) return;
    
    const item = document.createElement('li');
    item.className = `breadcrumb-item${isActive ? ' active' : ''}`;
    
    if (isActive) {
        item.textContent = label;
        item.setAttribute('aria-current', 'page');
    } else {
        const link = document.createElement('a');
        link.href = url;
        link.textContent = label;
        item.appendChild(link);
    }
    
    breadcrumb.appendChild(item);
    
    // 添加动画效果
    item.style.opacity = '0';
    item.style.transform = 'translateX(-10px)';
    item.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    
    setTimeout(() => {
        item.style.opacity = '1';
        item.style.transform = 'translateX(0)';
    }, 100);
}