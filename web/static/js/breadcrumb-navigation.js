/**
 * Breadcrumb Navigation
 * 面包屑导航功能增强
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化面包屑导航
    initBreadcrumbNavigation();
});

/**
 * 初始化面包屑导航
 */
function initBreadcrumbNavigation() {
    const breadcrumbContainer = document.querySelector('.breadcrumb-container');
    if (!breadcrumbContainer) return;
    
    // 添加动画效果
    breadcrumbContainer.style.opacity = '0';
    breadcrumbContainer.style.transform = 'translateY(-10px)';
    breadcrumbContainer.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    
    setTimeout(() => {
        breadcrumbContainer.style.opacity = '1';
        breadcrumbContainer.style.transform = 'translateY(0)';
    }, 200);
    
    // 为面包屑项添加ARIA属性
    const activeItem = breadcrumbContainer.querySelector('.breadcrumb-item.active');
    if (activeItem) {
        activeItem.setAttribute('aria-current', 'page');
    }
    
    // 为面包屑项添加点击事件
    const breadcrumbItems = breadcrumbContainer.querySelectorAll('.breadcrumb-item a');
    breadcrumbItems.forEach(item => {
        item.addEventListener('click', function(e) {
            // 添加点击动画效果
            const ripple = document.createElement('span');
            ripple.classList.add('breadcrumb-ripple');
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 500);
        });
    });
}